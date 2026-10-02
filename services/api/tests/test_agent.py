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
    monkeypatch.setattr(service, "query", lambda question, access_token=None: (seen.append(access_token) or ("ok", "run")))
    response = agent_client.post("/agent/query", json={"question": "ticket 1"}, headers=auth_headers)
    assert response.status_code == 200
    assert seen and seen[0] == auth_headers["Authorization"].removeprefix("Bearer ")


def test_old_endpoint_keeps_working(agent_client, monkeypatch):
    from routes import knowledge
    monkeypatch.setattr(knowledge, "query", lambda q: "Respuesta anterior")
    assert agent_client.post("/knowledge/query", json={"question": "Oro?"}).json() == {"answer": "Respuesta anterior"}
