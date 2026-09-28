import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from support_agent.graph import build_graph, rag
from support_agent.service import AgentError, open_service
from support_agent.traces import load_trace


@pytest.fixture
def providers(monkeypatch):
    chunks = [{"text": "Oro (50+ puntos): 15%", "source_document": "loyalty-program"}]
    calls = []
    monkeypatch.setattr(rag, "retrieve", lambda q: calls.append(("retrieve", q)) or chunks)
    monkeypatch.setattr(rag, "generate_answer", lambda q, c: calls.append(("generate", c)) or "Oro: 50 puntos.")
    monkeypatch.setattr(rag, "query", lambda *a: pytest.fail("No se debe llamar al RAG monolítico"))
    return chunks, calls


def test_retrieves_once_and_passes_context_to_generation(tmp_path, providers):
    chunks, calls = providers
    with open_service(tmp_path, mode="mock") as service:
        answer, run = service.query("  puntos\nOro?  ")
    assert answer == "Oro: 50 puntos."
    assert calls == [("retrieve", "puntos Oro?"), ("generate", chunks)]
    trace = load_trace(tmp_path / "traces" / f"{run}.json")
    assert [e.node for e in trace.events] == ["receive_question", "retrieve_context", "generate_answer"]
    assert trace.events[1].output["context"] == chunks
    assert trace.status == "completed"


def test_empty_context_uses_distinct_node(tmp_path, providers, monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda q: [])
    with open_service(tmp_path, mode="mock") as service:
        _, run = service.query("No está en el corpus")
    trace = load_trace(tmp_path / "traces" / f"{run}.json")
    assert trace.events[-1].node == "insufficient_context"
    assert providers[1] == [("generate", [])]


def test_empty_question_never_calls_providers(tmp_path, providers):
    with open_service(tmp_path, mode="mock") as service:
        with pytest.raises(AgentError) as failure:
            service.query(" \n ")
    assert failure.value.code == "invalid_question"
    assert providers[1] == []
    trace = load_trace(tmp_path / "traces" / f"{failure.value.run_id}.json")
    assert trace.status == "invalid_question"
    assert [e.node for e in trace.events] == ["receive_question", "invalid_question"]


@pytest.mark.parametrize("failing_node", ["retrieve", "generate_answer"])
def test_failure_is_persisted_without_raw_exception(tmp_path, providers, monkeypatch, failing_node):
    def fail(*a):
        raise RuntimeError("private-provider-message")
    monkeypatch.setattr(rag, failing_node, fail)
    with open_service(tmp_path, mode="mock") as service:
        with pytest.raises(AgentError) as failure:
            service.query("Oro?")
    path = tmp_path / "traces" / f"{failure.value.run_id}.json"
    trace = load_trace(path)
    assert trace.status == "failed" and trace.answer is None
    assert trace.events[-1].node == ("retrieve_context" if failing_node == "retrieve" else "generate_answer")
    assert "private-provider-message" not in path.read_text()


def test_checkpoints_survive_reopen(tmp_path, providers):
    with open_service(tmp_path, mode="mock") as service:
        _, run = service.query("Oro?")
    with open_service(tmp_path, mode="mock") as reopened:
        history = list(reopened.graph.get_state_history({"configurable": {"thread_id": run}}))
    assert history[0].values["answer"] == "Oro: 50 puntos."
    assert any(s.next == ("generate_answer",) and s.values["context"] for s in history)


def test_concurrent_runs_do_not_share_state(tmp_path, providers, monkeypatch):
    monkeypatch.setattr(rag, "generate_answer", lambda q, c: q)
    with open_service(tmp_path, mode="mock") as service:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(service.query, [f"Pregunta {i}" for i in range(8)]))
        assert len({run for _, run in results}) == 8
        for i, (answer, run) in enumerate(results):
            assert answer == f"Pregunta {i}"
            assert service.graph.get_state({"configurable": {"thread_id": run}}).values["question"] == answer


def test_invalid_edge_fails_at_compile():
    graph = build_graph()
    graph.add_edge("retrieve_context", "missing_node")
    with pytest.raises(ValueError, match="unknown"):
        graph.compile()


def test_invalid_input_and_empty_model_answer(tmp_path, providers, monkeypatch):
    with open_service(tmp_path, mode="mock") as service:
        with pytest.raises(ValueError):
            service.query(123)
        monkeypatch.setattr(rag, "generate_answer", lambda *a: "   ")
        with pytest.raises(AgentError):
            service.query("Oro?")


def test_trace_write_failure_is_not_a_success(tmp_path, providers, monkeypatch):
    import support_agent.service as module
    with open_service(tmp_path, mode="mock") as service:
        monkeypatch.setattr(module, "save_trace", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
        with pytest.raises(AgentError, match="agent_unavailable"):
            service.query("Oro?")
    assert providers[1] == []


def test_trace_loader_rejects_incomplete_and_bad_schema(tmp_path):
    path = tmp_path / "trace.json"
    path.write_text(json.dumps({"schema_version": 99}))
    with pytest.raises(ValueError):
        load_trace(path)


def test_runtime_starts_without_git_binary(tmp_path, monkeypatch):
    import support_agent.service as module
    def no_git(*a, **kw):
        raise FileNotFoundError("git")
    monkeypatch.setattr(module.subprocess, "run", no_git)
    with open_service(tmp_path, mode="mock") as service:
        assert service.provenance["commit"] == "unknown"
        assert service.graph is not None


def test_retrieval_contract_failure_is_traced(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda q: [{"text": 42}])
    with open_service(tmp_path, mode="mock") as service:
        with pytest.raises(AgentError) as failure:
            service.query("Oro?")
    trace = load_trace(tmp_path / "traces" / f"{failure.value.run_id}.json")
    assert trace.events[-1].node == "retrieve_context"
    assert trace.status == "failed"
