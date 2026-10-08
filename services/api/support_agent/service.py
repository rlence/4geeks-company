"""Una instancia por proceso; estado por consulta persistido por thread_id."""
import hashlib
import logging
import os
import re
import sqlite3
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from .graph import ROOT, NodeFailure, StateContract, build_graph, rag, next_node
from .memory.repository import MemoryConflict, MemoryRepository
from .traces import Event, Trace, save_trace

logger = logging.getLogger(__name__)
DEFAULT_RUNTIME = Path(__file__).resolve().parents[1] / ".agent-runtime"


class AgentError(RuntimeError):
    def __init__(self, code, run_id):
        self.code, self.run_id = code, run_id
        super().__init__(code)


def provenance(mode="live"):
    def git(*args):
        try:
            result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    corpus = ROOT / "docs" / "company-knowledge-base"
    paths = [*sorted(corpus.glob("*.md")), *sorted(Path(__file__).parent.rglob("*.py")),
             ROOT / "data/pipelines/rag.py", ROOT / "data/process/rag_index.py",
             ROOT / "services/api/uv.lock"]
    return {
        "mode": mode, "commit": git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(git("status", "--porcelain")),
        "files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "generation_model": os.environ.get("GENERATION_MODEL", "unconfigured"),
        "embedding_model": os.environ.get("EMBEDDING_MODEL", "unconfigured"),
        "k": rag.DEFAULT_K, "min_score": rag.MIN_SCORE,
    }


class AgentService:
    def __init__(self, checkpointer, trace_dir, memory_repository=None, *, mode="live"):
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.provenance = provenance(mode)
        self.graph = build_graph().compile(checkpointer=checkpointer)
        self.memory = memory_repository
        self.conversation_lock = RLock()

    def query(self, question, *, access_token=None):
        from .tools.mcp_incidents import current_access_token
        token = current_access_token.set(access_token)
        try:
            return self._query(question)
        finally:
            current_access_token.reset(token)

    def _query(self, question):
        answer, run_id, _ = self._run(question)
        return answer, run_id

    def _run(self, question, *, thread_id=None, memories=None, private_trace=False, stateless=False):
        state = StateContract(question=question, memory_context=memories or []).model_dump()
        run_id = str(uuid4())
        trace = Trace(run_id=run_id, question="[redacted]" if private_trace else question,
                      provenance=self.provenance)
        config = {"configurable": {"thread_id": thread_id or run_id}}
        try:
            save_trace(self.trace_dir, trace)
            graph = build_graph().compile() if stateless else self.graph
            stream_options = {} if stateless else {"durability": "sync"}
            for update in graph.stream(state, config, stream_mode="updates", **stream_options):
                for node, output in update.items():
                    state.update(output)
                    trace.events.append(Event(node=node, status="completed",
                                              output={} if private_trace else output,
                                              next_node=next_node(node, state)))
                    save_trace(self.trace_dir, trace)
            StateContract.model_validate(state)
            trace.answer = None if private_trace else state["answer"]
            trace.error_code = state["error_code"]
            trace.status = "invalid_question" if state["error_code"] else state["outcome"]
            trace.finished_at = datetime.now(timezone.utc)
            save_trace(self.trace_dir, trace)
        except Exception as exc:
            trace.status, trace.answer, trace.error_code = "failed", None, "agent_unavailable"
            trace.finished_at = datetime.now(timezone.utc)
            trace.events.append(Event(node=exc.node if isinstance(exc, NodeFailure) else "runtime",
                                      status="failed", error_code="agent_unavailable"))
            try:
                save_trace(self.trace_dir, trace)
            except Exception:
                logger.error("agent trace persistence failed run_id=%s", run_id)
            # No raw provider exception: it can contain request data or credentials.
            logger.error("agent run failed run_id=%s node=%s", run_id, trace.events[-1].node)
            raise AgentError("agent_unavailable", run_id) from exc
        logger.info("agent run_id=%s status=%s", run_id, trace.status)
        if trace.error_code:
            raise AgentError(trace.error_code, run_id)
        return state["answer"], run_id, state

    def _decision_trace(self, status):
        run_id = str(uuid4())
        trace = Trace(run_id=run_id, question="[redacted]", provenance=self.provenance,
                      status="completed", finished_at=datetime.now(timezone.utc),
                      events=[Event(node="memory_decision", status="completed", output={"decision": status})])
        save_trace(self.trace_dir, trace)
        return run_id

    def query_with_memory(self, question, *, owner_id, conversation_id=None, access_token=None):
        """Un turno autenticado: resuelve pendiente, ejecuta grafo y evalúa novedad."""
        from .memory import logic
        from .memory.policy import FORBIDDEN
        from .tools.mcp_incidents import current_access_token

        if self.memory is None:
            raise RuntimeError("Almacén de memoria no disponible")
        token = current_access_token.set(access_token)
        try:
            with self.conversation_lock:
                if conversation_id is None:
                    conversation_id = self.memory.create_conversation(owner_id)
                else:
                    self.memory.assert_owner(conversation_id, owner_id)
                pending = self.memory.pending(conversation_id, owner_id)
                acknowledgement = ""
                if pending:
                    original_message = question
                    english = pending["language"] == "en"
                    try:
                        decision = logic.classify_decision(question, pending)
                    except Exception:
                        decision = None
                    if (decision and decision.confidence >= 0.8 and decision.intent == "approve"
                            and decision.explicit_approval):
                        self.memory.resolve_proposal(owner_id, conversation_id, "approve", question)
                        acknowledgement = ("I saved the memory you approved." if english else
                                           "He guardado el recuerdo que aprobaste.")
                    elif decision and decision.confidence >= 0.8 and decision.intent == "reject":
                        self.memory.resolve_proposal(owner_id, conversation_id, "reject", question)
                        acknowledgement = ("I will not save that memory." if english else
                                           "No guardaré ese recuerdo.")
                    elif decision and decision.confidence >= 0.8 and decision.intent == "edit":
                        try:
                            if decision.explicit_approval and decision.edited_fact:
                                self.memory.resolve_proposal(owner_id, conversation_id, "approve", question,
                                                             edited_fact=decision.edited_fact)
                                acknowledgement = ("I saved the edited version you approved." if english else
                                                   "He guardado la versión editada que aprobaste.")
                            elif decision.edited_fact:
                                revised = self.memory.revise_pending(owner_id, conversation_id,
                                                                     decision.edited_fact, question)
                                run_id = self._decision_trace("edited_pending")
                                prompt = (f"I propose remembering: ‘{revised}’. Do you confirm?" if english else
                                          f"Propongo recordar: «{revised}». ¿Confirmas que lo guarde?")
                                return (prompt,
                                        run_id, conversation_id)
                            else:
                                self.memory.resolve_proposal(owner_id, conversation_id, "discard", question)
                                acknowledgement = ("I discarded the unclear proposal." if english else
                                                   "No guardé la propuesta ambigua.")
                        except ValueError:
                            self.memory.resolve_proposal(owner_id, conversation_id, "discard", question)
                            acknowledgement = ("I could not save that edit." if english else
                                               "No guardé esa edición porque no pasó la validación.")
                    else:
                        self.memory.resolve_proposal(owner_id, conversation_id, "discard", question)
                        acknowledgement = ("I discarded the previous proposal because it was not clearly approved."
                                           if english else
                                           "Descarté la propuesta anterior porque no hubo confirmación clara.")

                    if (decision and decision.intent in {"approve", "reject", "edit"}
                            and decision.confidence >= 0.8
                            and (decision.intent != "approve" or decision.explicit_approval)):
                        remaining = (decision.remaining_question or "").strip()
                        if remaining and remaining.casefold() not in original_message.casefold():
                            remaining = ""
                        if not remaining:
                            return acknowledgement, self._decision_trace(decision.intent), conversation_id
                        question = remaining
                    elif (decision is None or decision.intent == "ambiguous" or decision.confidence < 0.8
                          or (decision.intent == "approve" and not decision.explicit_approval)):
                        return acknowledgement, self._decision_trace("discarded"), conversation_id

                location = re.search(r"\b(?:local|location|sede)\s*#?\s*(\d{1,2})\b", question, re.I)
                location_id = int(location.group(1)) if location and 1 <= int(location.group(1)) <= 14 else None
                memories = self.memory.read_relevant(owner_id, location_id, question)
                sensitive = bool(FORBIDDEN.search(question))
                answer, run_id, state = self._run(question, thread_id=conversation_id,
                                                  memories=[] if sensitive else memories,
                                                  private_trace=True, stateless=sensitive)
                if acknowledgement:
                    answer = acknowledgement + "\n\n" + answer
                if state["outcome"] == "completed" and not state["error_code"] and not sensitive:
                    try:
                        candidate = logic.evaluate(question, answer, context=state["context"])
                        if candidate:
                            self.memory.create_proposal(owner_id, conversation_id, candidate, question, run_id)
                            suffix = (f"Would you like me to remember this for next time: ‘{candidate.fact}’?"
                                      if candidate.language == "en" else
                                      f"¿Quieres que recuerde esto para la próxima vez: «{candidate.fact}»?")
                            answer += "\n\n" + suffix
                    except (ValueError, MemoryConflict):
                        pass
                    except Exception:
                        logger.warning("memory evaluation unavailable run_id=%s", run_id)
                return answer, run_id, conversation_id
        finally:
            current_access_token.reset(token)


@contextmanager
def open_service(runtime_dir=None, trace_dir=None, *, mode="live"):
    runtime = Path(runtime_dir or os.environ.get("AGENT_RUNTIME_DIR", DEFAULT_RUNTIME))
    runtime.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(runtime / "checkpoints.sqlite"), check_same_thread=False)
    memory = None
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        saver = SqliteSaver(connection, serde=JsonPlusSerializer(allowed_msgpack_modules=[]))
        saver.setup()
        memory = MemoryRepository(runtime / "memory.sqlite")
        yield AgentService(saver, trace_dir or runtime / "traces", memory, mode=mode)
    finally:
        if memory is not None:
            memory.close()
        connection.close()
