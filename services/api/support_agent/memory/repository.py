"""SQLite transaccional para conversaciones, propuestas, auditoría y recuerdos."""
import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4

from .policy import LIFETIME, MemoryProposal, validate_edited_fact

PENDING_TTL = timedelta(hours=24)
MAX_ACTIVE = 100


def now():
    return datetime.now(timezone.utc)


def stamp(value):
    return value.isoformat()


class MemoryConflict(RuntimeError):
    pass


class MemoryRepository:
    def __init__(self, path):
        self.connection = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.lock = RLock()
        with self.lock:
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.connection.execute("PRAGMA busy_timeout=5000")
            self._migrate()

    def _migrate(self):
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version(version)
                SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version);
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
                owner_id INTEGER NOT NULL, category TEXT NOT NULL, location_id INTEGER,
                subject_key TEXT NOT NULL, fact TEXT NOT NULL, source_quote TEXT NOT NULL,
                reason TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'es',
                source_hash TEXT NOT NULL, run_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','discarded','expired')),
                created_at TEXT NOT NULL, expires_at TEXT NOT NULL, decided_at TEXT,
                final_fact TEXT, decision_hash TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_pending_per_conversation
                ON proposals(conversation_id) WHERE status='pending';
            CREATE INDEX IF NOT EXISTS proposal_owner ON proposals(owner_id, conversation_id, status);
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, location_id INTEGER,
                scope_key INTEGER NOT NULL, category TEXT NOT NULL, subject_key TEXT NOT NULL,
                fact TEXT NOT NULL, source_proposal_id TEXT NOT NULL REFERENCES proposals(id),
                approved_by INTEGER NOT NULL, approved_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL,
                UNIQUE(owner_id, scope_key, category, subject_key)
            );
            CREATE INDEX IF NOT EXISTS memory_lookup
                ON memories(owner_id, status, scope_key, category, expires_at);
            CREATE TABLE IF NOT EXISTS memory_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, proposal_id TEXT NOT NULL REFERENCES proposals(id),
                owner_id INTEGER NOT NULL, action TEXT NOT NULL, occurred_at TEXT NOT NULL,
                fact TEXT, previous_fact TEXT, message_hash TEXT
            );
        """)
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(proposals)")}
        if "language" not in columns:
            self.connection.execute("ALTER TABLE proposals ADD COLUMN language TEXT NOT NULL DEFAULT 'es'")
        self.connection.execute("UPDATE schema_version SET version=2")

    def close(self):
        with self.lock:
            self.connection.close()

    @contextmanager
    def _transaction(self):
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self.connection.rollback()
                raise
            else:
                self.connection.commit()

    def _one(self, sql, args=()):
        row = self.connection.execute(sql, args).fetchone()
        return dict(row) if row else None

    def create_conversation(self, owner_id):
        identifier = str(uuid4())
        with self.lock:
            self.connection.execute(
                "INSERT INTO conversations VALUES (?,?,?)", (identifier, owner_id, stamp(now()))
            )
        return identifier

    def assert_owner(self, conversation_id, owner_id):
        with self.lock:
            row = self._one("SELECT owner_id FROM conversations WHERE id=?", (conversation_id,))
        if row is None or row["owner_id"] != owner_id:
            raise MemoryConflict("Conversación inexistente o ajena")

    def expire_pending(self, conversation_id=None):
        with self._transaction():
            rows = self.connection.execute(
                "SELECT id, owner_id FROM proposals WHERE status='pending' AND expires_at<=?" +
                (" AND conversation_id=?" if conversation_id else ""),
                (stamp(now()), conversation_id) if conversation_id else (stamp(now()),),
            ).fetchall()
            for row in rows:
                self.connection.execute(
                    "UPDATE proposals SET status='expired', decided_at=? WHERE id=?",
                    (stamp(now()), row["id"]),
                )
                self._audit(row["id"], row["owner_id"], "expired")
            self.connection.execute(
                "UPDATE memories SET status='expired' WHERE status='active' AND expires_at<=?",
                (stamp(now()),),
            )
        return len(rows)

    def pending(self, conversation_id, owner_id):
        self.assert_owner(conversation_id, owner_id)
        self.expire_pending(conversation_id)
        with self.lock:
            return self._one(
                "SELECT * FROM proposals WHERE conversation_id=? AND owner_id=? AND status='pending'",
                (conversation_id, owner_id),
            )

    def read_relevant(self, owner_id, location_id=None, question="", limit=5):
        self.expire_pending()
        # Filtro conservador: preferencias personales + hechos del local explícito.
        scope = (0, location_id) if location_id is not None else (0,)
        placeholders = ",".join("?" for _ in scope)
        with self.lock:
            rows = self.connection.execute(
                f"SELECT id, location_id, category, subject_key, fact, approved_at, expires_at "
                f"FROM memories WHERE owner_id=? AND status='active' AND scope_key IN ({placeholders}) "
                "ORDER BY updated_at DESC LIMIT 100", (owner_id, *scope),
            ).fetchall()
        stopwords = {"local", "location", "sede", "cuándo", "cuando", "where", "which", "sobre", "about"}
        words = {w for w in re.findall(r"\w+", question.casefold()) if len(w) > 4 and w not in stopwords}
        selected = [dict(row) for row in rows if row["category"] == "communication_preference"
                    or words.intersection(re.findall(r"\w+", (row["fact"] + " " + row["subject_key"]).casefold()))]
        return selected[:limit]

    def create_proposal(self, owner_id, conversation_id, candidate: MemoryProposal, question, run_id):
        self.assert_owner(conversation_id, owner_id)
        self.expire_pending(conversation_id)
        identifier = str(uuid4())
        created = now()
        with self._transaction():
            try:
                self.connection.execute(
                    """INSERT INTO proposals
                       (id,conversation_id,owner_id,category,location_id,subject_key,fact,source_quote,
                        reason,language,source_hash,run_id,status,created_at,expires_at,decided_at,
                        final_fact,decision_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (identifier, conversation_id, owner_id, candidate.category, candidate.location_id,
                     candidate.subject_key, candidate.fact, candidate.source_quote, candidate.reason,
                     candidate.language,
                     hashlib.sha256(question.encode()).hexdigest(), run_id, "pending",
                     stamp(created), stamp(created + PENDING_TTL), None, None, None),
                )
            except sqlite3.IntegrityError as exc:
                raise MemoryConflict("Ya existe una propuesta pendiente") from exc
            self._audit(identifier, owner_id, "proposed", fact=candidate.fact)
        return identifier

    def _audit(self, proposal_id, owner_id, action, *, fact=None, previous_fact=None, message_hash=None):
        self.connection.execute(
            "INSERT INTO memory_audit(proposal_id,owner_id,action,occurred_at,fact,previous_fact,message_hash) "
            "VALUES (?,?,?,?,?,?,?)",
            (proposal_id, owner_id, action, stamp(now()), fact, previous_fact, message_hash),
        )

    @staticmethod
    def _validated_edit(proposal, edited_fact):
        fact = validate_edited_fact(edited_fact)
        location_id = proposal["location_id"]
        if location_id is not None and not re.search(
            rf"\b(?:local|location|sede)\s*#?\s*{location_id}\b", fact, re.IGNORECASE
        ):
            raise ValueError("La edición debe conservar el local confirmado")
        return fact

    def resolve_proposal(self, owner_id, conversation_id, action, message, edited_fact=None):
        if action not in {"approve", "reject", "discard"}:
            raise ValueError("Decisión inválida")
        self.assert_owner(conversation_id, owner_id)
        self.expire_pending(conversation_id)
        with self._transaction():
            proposal = self._one(
                "SELECT * FROM proposals WHERE owner_id=? AND conversation_id=? AND status='pending'",
                (owner_id, conversation_id),
            )
            if not proposal:
                raise MemoryConflict("No hay propuesta pendiente")
            final_fact = self._validated_edit(proposal, edited_fact) if edited_fact else proposal["fact"]
            status = {"approve": "approved", "reject": "rejected", "discard": "discarded"}[action]
            if action == "approve":
                active_count = self.connection.execute(
                    "SELECT count(*) FROM memories WHERE owner_id=? AND status='active'", (owner_id,)
                ).fetchone()[0]
                previous = self._one(
                    "SELECT fact FROM memories WHERE owner_id=? AND scope_key=? AND category=? AND subject_key=?",
                    (owner_id, proposal["location_id"] or 0, proposal["category"], proposal["subject_key"]),
                )
                if active_count >= MAX_ACTIVE and previous is None:
                    raise MemoryConflict("Límite de recuerdos activos alcanzado")
                approved_at = now()
                self.connection.execute(
                    """INSERT INTO memories(id,owner_id,location_id,scope_key,category,subject_key,fact,
                       source_proposal_id,approved_by,approved_at,updated_at,expires_at,status)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(owner_id,scope_key,category,subject_key) DO UPDATE SET
                       fact=excluded.fact,source_proposal_id=excluded.source_proposal_id,
                       approved_by=excluded.approved_by,approved_at=excluded.approved_at,
                       updated_at=excluded.updated_at,expires_at=excluded.expires_at,status='active'""",
                    (str(uuid4()), owner_id, proposal["location_id"], proposal["location_id"] or 0,
                     proposal["category"], proposal["subject_key"], final_fact, proposal["id"],
                     owner_id, stamp(approved_at), stamp(approved_at),
                     stamp(approved_at + LIFETIME[proposal["category"]]), "active"),
                )
                self._audit(proposal["id"], owner_id, "approved", fact=final_fact,
                            previous_fact=previous["fact"] if previous else None,
                            message_hash=hashlib.sha256(message.encode()).hexdigest())
            else:
                self._audit(proposal["id"], owner_id, status,
                            message_hash=hashlib.sha256(message.encode()).hexdigest())
            self.connection.execute(
                "UPDATE proposals SET status=?, decided_at=?, final_fact=?, decision_hash=? WHERE id=?",
                (status, stamp(now()), final_fact if action == "approve" else None,
                 hashlib.sha256(message.encode()).hexdigest(), proposal["id"]),
            )
        return status

    def revise_pending(self, owner_id, conversation_id, edited_fact, message):
        self.assert_owner(conversation_id, owner_id)
        with self._transaction():
            proposal = self._one(
                "SELECT * FROM proposals WHERE owner_id=? AND conversation_id=? AND status='pending'",
                (owner_id, conversation_id),
            )
            if not proposal:
                raise MemoryConflict("No hay propuesta pendiente")
            fact = self._validated_edit(proposal, edited_fact)
            self.connection.execute("UPDATE proposals SET fact=? WHERE id=?", (fact, proposal["id"]))
            self._audit(proposal["id"], owner_id, "edited_pending", fact=fact,
                        previous_fact=proposal["fact"],
                        message_hash=hashlib.sha256(message.encode()).hexdigest())
        return fact

    def consolidate(self):
        self.expire_pending()
        with self.lock:
            return self.connection.execute("SELECT count(*) FROM memories WHERE status='active'").fetchone()[0]
