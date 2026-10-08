import pytest
from fastapi.testclient import TestClient

from main import app
from support_agent.graph import rag


@pytest.fixture
def agent_client(tmp_path, monkeypatch):
    from support_agent import routing
    from support_agent.contracts import Decision
    monkeypatch.setattr(routing, "classify", lambda q: Decision(source="rag", rag_question=q))
    monkeypatch.setenv("AGENT_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(rag, "retrieve", lambda q: [{"text": "Oro: 50 puntos"}])
    monkeypatch.setattr(rag, "generate_answer", lambda q, c: "Oro: 50 puntos.")
    with TestClient(app) as client:
        yield client
    assert app.state.support_agent is None


def test_endpoint_contract_and_empty_question(agent_client):
    response = agent_client.post("/agent/query", json={"question": "Oro?"})
    assert response.status_code == 200
    assert response.json() == {"answer": "Oro: 50 puntos."}
    assert response.headers["x-agent-run-id"]
    empty = agent_client.post("/agent/query", json={"question": "  "})
    assert empty.status_code == 422
    assert empty.headers["x-agent-run-id"]


@pytest.mark.parametrize("payload", [{}, {"question": 12}, {"question": "x" * 1001}])
def test_endpoint_validates_input(agent_client, payload):
    assert agent_client.post("/agent/query", json=payload).status_code == 422


def test_endpoint_masks_failure(agent_client, monkeypatch):
    def fail(q):
        raise RuntimeError("private provider details")
    monkeypatch.setattr(rag, "retrieve", fail)
    response = agent_client.post("/agent/query", json={"question": "Oro?"})
    assert response.status_code == 503
    assert "private" not in response.text
    assert response.headers["x-agent-run-id"]


def test_endpoint_forwards_validated_bearer_to_mcp(agent_client, monkeypatch, existing_user, auth_headers):
    from routes import agent
    seen = []
    service = app.state.support_agent
    monkeypatch.setattr(service, "query_with_memory", lambda question, *, owner_id, conversation_id=None,
                        access_token=None: (seen.append((owner_id, access_token)) or
                                            ("ok", "run", "d8add198-62dd-47ef-b8c3-51dafdb3c654")))
    response = agent_client.post("/agent/query", json={"question": "ticket 1"}, headers=auth_headers)
    assert response.status_code == 200
    assert seen and seen[0][1] == auth_headers["Authorization"].removeprefix("Bearer ")
    assert seen[0][0] == 1


def test_old_endpoint_keeps_working(agent_client, monkeypatch):
    from routes import knowledge
    monkeypatch.setattr(knowledge, "query", lambda q: "Respuesta anterior")
    assert agent_client.post("/knowledge/query", json={"question": "Oro?"}).json() == {"answer": "Respuesta anterior"}


def test_authenticated_memory_api_cycle(agent_client, monkeypatch, existing_user, auth_headers):
    from support_agent.memory import logic
    from support_agent.memory.logic import PendingDecision
    from support_agent.memory.policy import MemoryProposal

    question = "En realidad el proveedor del local 7 entrega los miércoles, no los martes."
    candidate = MemoryProposal(
        category="supplier_delivery", location_id=7, subject_key="proveedor_carne",
        fact="El proveedor del local 7 entrega los miércoles, no los martes",
        source_quote="el proveedor del local 7 entrega los miércoles",
        reason="Corrección estable de entregas",
    )
    monkeypatch.setattr(logic, "evaluate", lambda q, a, context=None: candidate if q == question else None)
    monkeypatch.setattr(logic, "classify_decision",
                        lambda q, p: PendingDecision(intent="approve", confidence=0.99,
                                                     explicit_approval=True))
    first = agent_client.post("/agent/query", json={"question": question}, headers=auth_headers)
    assert first.status_code == 200
    assert "¿Quieres que recuerde" in first.json()["answer"]
    conversation = first.json()["conversation_id"]
    second = agent_client.post("/agent/query", json={"question": "Sí, recuérdalo",
                                                        "conversation_id": conversation}, headers=auth_headers)
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation
    assert "guardado" in second.json()["answer"]
    assert agent_client.post("/agent/query", json={"question": "Hola",
                                                   "conversation_id": conversation}).status_code == 401
