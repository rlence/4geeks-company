"""Ciclos del agente con proveedor de generación simulado."""
from datetime import timedelta

import pytest

from support_agent.contracts import Decision
from support_agent.memory.logic import PendingDecision
from support_agent.memory.policy import MemoryProposal, validate_proposal
from support_agent.memory.repository import MemoryConflict, MemoryRepository, now, stamp
from support_agent.service import open_service
from support_agent.graph import rag

QUESTION = "En realidad el proveedor del local 7 entrega los miércoles, no los martes."


def proposal(fact="El proveedor del local 7 entrega los miércoles, no los martes"):
    return MemoryProposal(
        category="supplier_delivery", location_id=7, subject_key="proveedor_carne",
        fact=fact, source_quote="el proveedor del local 7 entrega los miércoles",
        reason="Corrección estable de entregas",
    )


@pytest.fixture
def simulated(monkeypatch):
    from support_agent import routing
    from support_agent.memory import logic
    monkeypatch.setattr(routing, "classify", lambda q: Decision(source="rag", rag_question=q))
    monkeypatch.setattr(rag, "retrieve", lambda q: [])
    monkeypatch.setattr(rag, "generate_answer", lambda q, c: "Entendido; verificaré el horario oficial.")
    monkeypatch.setattr(logic, "evaluate", lambda q, a, context=None: proposal() if q == QUESTION else None)
    monkeypatch.setattr(logic, "answer_with_memory", lambda q, c, m: f"Recuerdo aprobado: {m[0]['fact']}")
    return logic


def test_approval_persists_and_survives_restart(tmp_path, simulated, monkeypatch):
    monkeypatch.setattr(simulated, "classify_decision",
                        lambda q, p: PendingDecision(intent="approve", confidence=0.99,
                                                     explicit_approval=True))
    with open_service(tmp_path, mode="mock") as service:
        answer, run, conversation = service.query_with_memory(QUESTION, owner_id=1)
        assert "¿Quieres que recuerde" in answer
        assert service.memory.pending(conversation, 1)["status"] == "pending"
        approved, _, same = service.query_with_memory("Sí, recuérdalo", owner_id=1,
                                                        conversation_id=conversation)
        assert same == conversation and "guardado" in approved
        assert service.memory.connection.execute("SELECT count(*) FROM memory_audit").fetchone()[0] == 2
    with open_service(tmp_path, mode="mock") as service:
        answer, _, same = service.query_with_memory("¿Cuándo entrega el proveedor del local 7?",
                                                     owner_id=1, conversation_id=conversation)
        assert same == conversation and "miércoles" in answer
        assert service.memory.connection.execute("SELECT count(*) FROM memories WHERE status='active'").fetchone()[0] == 1
        with pytest.raises(MemoryConflict):
            service.query_with_memory("¿Qué recuerdas?", owner_id=2, conversation_id=conversation)
    trace = (tmp_path / "traces" / f"{run}.json").read_text()
    assert QUESTION not in trace and "proveedor" not in trace


def test_rejection_does_not_write_memory(tmp_path, simulated, monkeypatch):
    monkeypatch.setattr(simulated, "classify_decision",
                        lambda q, p: PendingDecision(intent="reject", confidence=0.99))
    with open_service(tmp_path, mode="mock") as service:
        _, _, conversation = service.query_with_memory(QUESTION, owner_id=1)
        answer, _, _ = service.query_with_memory("No, no lo recuerdes", owner_id=1,
                                                conversation_id=conversation)
        assert "No guardaré" in answer
        assert service.memory.connection.execute("SELECT count(*) FROM memories").fetchone()[0] == 0
        assert [x[0] for x in service.memory.connection.execute("SELECT action FROM memory_audit")] == ["proposed", "rejected"]


def test_edit_requires_new_confirmation(tmp_path, simulated, monkeypatch):
    decisions = iter([
        PendingDecision(intent="edit", confidence=0.95, edited_fact="El proveedor del local 7 entrega los jueves"),
        PendingDecision(intent="approve", confidence=0.95, explicit_approval=True),
    ])
    monkeypatch.setattr(simulated, "classify_decision", lambda q, p: next(decisions))
    with open_service(tmp_path, mode="mock") as service:
        _, _, conversation = service.query_with_memory(QUESTION, owner_id=1)
        answer, _, _ = service.query_with_memory("Quise decir jueves", owner_id=1, conversation_id=conversation)
        assert "¿Confirmas" in answer
        assert service.memory.connection.execute("SELECT count(*) FROM memories").fetchone()[0] == 0
        service.query_with_memory("Sí, confirmo", owner_id=1, conversation_id=conversation)
        assert service.memory.connection.execute("SELECT fact FROM memories").fetchone()[0].endswith("jueves")


def test_unrelated_discards_and_answers_new_question(tmp_path, simulated, monkeypatch):
    monkeypatch.setattr(simulated, "classify_decision",
                        lambda q, p: PendingDecision(intent="unrelated", confidence=0.99))
    with open_service(tmp_path, mode="mock") as service:
        _, _, conversation = service.query_with_memory(QUESTION, owner_id=1)
        answer, _, _ = service.query_with_memory("¿Qué dice la política?", owner_id=1,
                                                conversation_id=conversation)
        assert "Descarté" in answer and "verificaré" in answer
        assert service.memory.connection.execute("SELECT count(*) FROM memories").fetchone()[0] == 0


def test_expiry_and_deduplication(tmp_path):
    repo = MemoryRepository(tmp_path / "memory.sqlite")
    try:
        conv = repo.create_conversation(1)
        first = repo.create_proposal(1, conv, proposal(), QUESTION, "run-1")
        repo.resolve_proposal(1, conv, "approve", "Sí")
        second = repo.create_proposal(1, conv, proposal("El proveedor del local 7 entrega los viernes"),
                                      QUESTION, "run-2")
        repo.resolve_proposal(1, conv, "approve", "Sí")
        assert first != second
        assert repo.connection.execute("SELECT count(*) FROM memories").fetchone()[0] == 1
        assert repo.connection.execute("SELECT count(*) FROM memory_audit").fetchone()[0] == 4
        third = repo.create_proposal(1, conv, proposal(), QUESTION, "run-3")
        repo.connection.execute("UPDATE proposals SET expires_at=? WHERE id=?",
                                (stamp(now() - timedelta(seconds=1)), third))
        assert repo.pending(conv, 1) is None
        assert repo.connection.execute("SELECT status FROM proposals WHERE id=?", (third,)).fetchone()[0] == "expired"
    finally:
        repo.close()


def test_policy_rejects_sensitive_and_unconfirmed_location():
    with pytest.raises(ValueError):
        validate_proposal(proposal(), "El cliente de Brasa Points reclamó en el local 7")
    with pytest.raises(ValueError):
        validate_proposal(proposal(), "En Medellín el proveedor entrega los miércoles")


def test_model_numeric_string_location_is_validated_against_user_text():
    raw = proposal().model_dump()
    raw["location_id"] = "7"
    assert validate_proposal(MemoryProposal.model_validate(raw), QUESTION).location_id == 7
    raw["location_id"] = "9"
    with pytest.raises(ValueError):
        validate_proposal(MemoryProposal.model_validate(raw), QUESTION)

def test_approval_then_second_question_in_same_turn(tmp_path, simulated, monkeypatch):
    monkeypatch.setattr(simulated, "classify_decision", lambda q, p: PendingDecision(
        intent="approve", confidence=0.99, explicit_approval=True,
        remaining_question="¿Qué dice la política?"
    ))
    with open_service(tmp_path, mode="mock") as service:
        _, _, conversation = service.query_with_memory(QUESTION, owner_id=1)
        answer, _, _ = service.query_with_memory("Sí, y además ¿qué dice la política?",
                                                owner_id=1, conversation_id=conversation)
        assert "He guardado" in answer and "verificaré" in answer
        assert service.memory.connection.execute("SELECT count(*) FROM memories").fetchone()[0] == 1


def test_failed_audit_rolls_back_approval(tmp_path, monkeypatch):
    repo = MemoryRepository(tmp_path / "memory.sqlite")
    try:
        conv = repo.create_conversation(1)
        repo.create_proposal(1, conv, proposal(), QUESTION, "run-1")
        original = repo._audit

        def fail(*args, **kwargs):
            if args[2] == "approved":
                raise OSError("audit unavailable")
            return original(*args, **kwargs)

        monkeypatch.setattr(repo, "_audit", fail)
        with pytest.raises(OSError):
            repo.resolve_proposal(1, conv, "approve", "Sí")
        assert repo.connection.execute("SELECT count(*) FROM memories").fetchone()[0] == 0
        assert repo.pending(conv, 1)["status"] == "pending"
    finally:
        repo.close()


def test_edit_cannot_change_location_scope(tmp_path):
    repo = MemoryRepository(tmp_path / "memory.sqlite")
    try:
        conv = repo.create_conversation(1)
        repo.create_proposal(1, conv, proposal(), QUESTION, "run-1")
        with pytest.raises(ValueError):
            repo.revise_pending(1, conv, "El proveedor del local 9 entrega los jueves", "Quise decir local 9")
        assert repo.pending(conv, 1)["fact"] == proposal().fact
    finally:
        repo.close()


def test_sensitive_question_is_not_checkpointed_or_proposed(tmp_path, simulated):
    with open_service(tmp_path, mode="mock") as service:
        answer, _, conversation = service.query_with_memory(
            "El cliente de Brasa Points llamó por su cuenta", owner_id=1
        )
        assert "¿Quieres que recuerde" not in answer
        assert service.memory.pending(conversation, 1) is None
        assert service.graph.get_state({"configurable": {"thread_id": conversation}}).values == {}

def test_english_proposal_and_confirmation(tmp_path, simulated, monkeypatch):
    from support_agent.memory import logic
    question = "Actually, the supplier for location 7 always delivers on Wednesdays, not Tuesdays."
    english = MemoryProposal(
        category="supplier_delivery", location_id=7, subject_key="meat_supplier",
        fact="The supplier for location 7 always delivers on Wednesdays, not Tuesdays",
        source_quote="the supplier for location 7 always delivers on Wednesdays",
        reason="Recurring local delivery correction", language="en",
    )
    monkeypatch.setattr(logic, "evaluate", lambda q, a, context=None: english if q == question else None)
    monkeypatch.setattr(logic, "classify_decision",
                        lambda q, p: PendingDecision(intent="approve", confidence=0.99,
                                                     explicit_approval=True))
    with open_service(tmp_path, mode="mock") as service:
        answer, _, conversation = service.query_with_memory(question, owner_id=1)
        assert "Would you like me to remember" in answer
        confirmed, _, _ = service.query_with_memory("Yes, remember it", owner_id=1,
                                                     conversation_id=conversation)
        assert "I saved" in confirmed

def test_memory_answers_when_router_would_clarify(tmp_path, simulated, monkeypatch):
    from support_agent import routing
    monkeypatch.setattr(simulated, "classify_decision",
                        lambda q, p: PendingDecision(intent="approve", confidence=0.99,
                                                     explicit_approval=True))
    with open_service(tmp_path, mode="mock") as service:
        _, _, conversation = service.query_with_memory(QUESTION, owner_id=1)
        service.query_with_memory("Sí, recuérdalo", owner_id=1, conversation_id=conversation)
        monkeypatch.setattr(routing, "classify", lambda q: Decision(source="clarify"))
        answer, _, _ = service.query_with_memory("¿Cuándo entrega el proveedor del local 7?",
                                                 owner_id=1, conversation_id=conversation)
        assert "miércoles" in answer

def test_approve_and_continue_incident_query(tmp_path, simulated, monkeypatch):
    from support_agent import routing
    from support_agent.tools import mcp_incidents
    monkeypatch.setattr(simulated, "classify_decision", lambda q, p: PendingDecision(
        intent="approve", confidence=0.99, explicit_approval=True,
        remaining_question="¿Qué pasó con el ticket 482?"
    ))
    with open_service(tmp_path, mode="mock") as service:
        _, _, conversation = service.query_with_memory(QUESTION, owner_id=1)
        monkeypatch.setattr(routing, "classify", lambda q: Decision(source="incidents", ticket_id=482))
        monkeypatch.setattr(mcp_incidents, "lookup", lambda d: {
            "status": "ok", "items": [{"id": 482, "status": "resolved",
            "category": "operations", "updated_at": "2026-10-08"}], "total": 1,
        })
        answer, _, _ = service.query_with_memory("Sí, y además ¿qué pasó con el ticket 482?",
                                                owner_id=1, conversation_id=conversation)
        assert "He guardado" in answer and "Ticket 482" in answer

def test_approve_label_without_explicit_signal_discards(tmp_path, simulated, monkeypatch):
    monkeypatch.setattr(simulated, "classify_decision",
                        lambda q, p: PendingDecision(intent="approve", confidence=0.99,
                                                     explicit_approval=False))
    with open_service(tmp_path, mode="mock") as service:
        _, _, conversation = service.query_with_memory(QUESTION, owner_id=1)
        answer, _, _ = service.query_with_memory("Tal vez", owner_id=1, conversation_id=conversation)
        assert "Descarté" in answer
        assert service.memory.connection.execute("SELECT count(*) FROM memories").fetchone()[0] == 0
