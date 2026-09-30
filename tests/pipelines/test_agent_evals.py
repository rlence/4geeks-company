"""Evals sobre artefactos guardados. No ejecutan grafo, Qdrant ni LLM.

Sin argumentos evalúan trazas de proveedores simulados versionadas para CI.
--agent-traces-dir exige trazas live y sirve para la aceptación real.
"""
import hashlib
import json
import re
from pathlib import Path

import pytest

from support_agent.traces import load_trace

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def traces(request):
    supplied = request.config.getoption("--agent-traces-dir")
    directory = Path(supplied) if supplied else Path(__file__).parent / "fixtures/agent-traces"
    manifest = json.loads((directory / "manifest.json").read_text())
    expected_mode = "live" if supplied else "mock"
    assert manifest["mode"] == expected_mode, "No presentar fixtures simuladas como evidencia real"
    assert set(manifest["cases"]) == {"gold", "allergens", "unknown", "empty"}
    loaded = {}
    for case, filename in manifest["cases"].items():
        assert Path(filename).name == filename and filename.endswith(".json")
        trace = load_trace(directory / filename)
        assert str(trace.run_id) == Path(filename).stem
        assert trace.provenance["mode"] == expected_mode
        assert trace.status in {"completed", "invalid_question"}, f"{case}: {trace.status}"
        assert all(event.status == "completed" for event in trace.events)
        assert trace.finished_at >= trace.started_at
        assert trace.provenance["files_sha256"], "Falta procedencia del corpus"
        for source in (ROOT / "docs/company-knowledge-base").glob("*.md"):
            assert trace.provenance["files_sha256"][str(source.relative_to(ROOT))] == hashlib.sha256(source.read_bytes()).hexdigest()
        loaded[case] = trace
    assert len({t.run_id for t in loaded.values()}) == len(loaded)
    return loaded


def assert_route(trace, nodes):
    if trace.schema_version == 2 and nodes[1] == "retrieve_context":
        nodes = [nodes[0], "classify_request", *nodes[1:]]
    assert [event.node for event in trace.events] == nodes
    assert [event.next_node for event in trace.events] == nodes[1:] + ["END"]


def test_gold_is_grounded_in_loyalty_policy(traces):
    trace = traces["gold"]
    assert "oro" in trace.question.lower()
    assert_route(trace, ["receive_question", "retrieve_context", "generate_answer"])
    chunks = next(e for e in trace.events if e.node == "retrieve_context").output["context"]
    policy = (ROOT / "docs/company-knowledge-base/brasaland-loyalty-program.es.md").read_text()
    assert "Oro (50+ puntos)" in policy
    assert any(c["source_document"] == "loyalty-program" and "Oro (50+ puntos)" in c["text"] for c in chunks)
    answer = trace.answer.lower()
    assert re.search(r"\b50\s*(?:o más\s*)?puntos", answer)
    assert trace.events[-1].output["answer"] == trace.answer
    # Cifras solo si aparecen en el contexto realmente recuperado.
    context_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", " ".join(c["text"] for c in chunks)))
    assert set(re.findall(r"\d+(?:[.,]\d+)?", answer)) <= context_numbers
    if "descuento" in answer:
        assert "15" in answer


def test_unknown_routes_to_honest_response(traces):
    trace = traces["unknown"]
    assert "horario" in trace.question.lower()
    assert_route(trace, ["receive_question", "retrieve_context", "insufficient_context"])
    assert next(e for e in trace.events if e.node == "retrieve_context").output["context"] == []
    assert re.search(r"no (?:tengo|dispongo|hay|contamos)|no (?:incluye|contiene)|sin información", trace.answer.lower())
    assert not re.search(r"\d", trace.answer), "No inventar un horario"


def test_empty_skips_retrieval_and_generation(traces):
    trace = traces["empty"]
    assert not trace.question.strip()
    assert_route(trace, ["receive_question", "invalid_question"])
    assert trace.status == "invalid_question" and trace.error_code == "invalid_question"
    assert trace.answer is None


def test_allergens_follow_source_without_safety_guarantee(traces):
    trace = traces["allergens"]
    assert "maní" in trace.question.lower()
    assert_route(trace, ["receive_question", "retrieve_context", "generate_answer"])
    chunks = next(e for e in trace.events if e.node == "retrieve_context").output["context"]
    assert any(c["source_document"] == "menu-allergens" and "maní" in c["text"] for c in chunks)
    answer = trace.answer.lower()
    assert "maní" in answer and "trazas" in answer
    assert "contaminación cruzada" in answer
    assert re.search(r"(?:nunca|no)\s+(?:se\s+)?(?:puede\s+)?garantiza", answer)
    assert not re.search(r"(?:es|totalmente) segur[ao]|sin riesgo", answer)
