"""Tests unitarios del pipeline RAG (Hito 7).

Corre vía `python -m pytest tests/pipelines/test_rag.py`. Este repo no tiene
un venv en la raíz —qdrant-client/openai viven en el de services/api— así
que el comando real equivalente, desde la raíz del monorepo, es:

    uv run --project services/api python -m pytest tests/pipelines/test_rag.py

Ni Qdrant ni el proveedor de modelos se tocan en ningún test: el cliente
vectorial es un stub en memoria y el LLM va mockeado, tal como pide el rule.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "data" / "process"))
sys.path.insert(0, str(_ROOT / "data" / "pipelines"))

import rag  # noqa: E402  (data/pipelines/rag.py)
import rag_index  # noqa: E402  (data/process/rag_index.py)


# ---------------------------------------------------------------------------
# Dobles de prueba
# ---------------------------------------------------------------------------


def _point(score: float, text: str, source_document: str = "loyalty-program", index: int = 0):
    return SimpleNamespace(
        score=score,
        payload={
            "company": "brasaland",
            "source_document": source_document,
            "section": "Niveles del programa",
            "language": "es",
            "chunk_index": index,
            "text": text,
        },
    )


class FakeQdrant:
    """Stub en memoria: devuelve los puntos que se le configuren, sin red."""

    def __init__(self, points):
        self._points = points
        self.last_limit = None

    def query_points(self, *, collection_name, query, limit, with_payload):
        self.last_limit = limit
        return SimpleNamespace(points=self._points[:limit])


@pytest.fixture
def fake_embed(monkeypatch):
    monkeypatch.setattr(rag, "embed", lambda text: [0.1, 0.2, 0.3])


def _use_qdrant(monkeypatch, points):
    fake = FakeQdrant(points)
    monkeypatch.setattr(rag, "_qdrant", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# retrieve()
# ---------------------------------------------------------------------------


def test_retrieve_excluye_resultados_bajo_el_umbral(monkeypatch, fake_embed):
    _use_qdrant(
        monkeypatch,
        [_point(0.91, "Oro (50+ puntos)"), _point(0.12, "ruido irrelevante")],
    )

    results = rag.retrieve("¿cuántos puntos para Oro?", k=5, min_score=0.35)

    assert len(results) == 1
    assert results[0]["text"] == "Oro (50+ puntos)"


def test_retrieve_puede_devolver_menos_de_k(monkeypatch, fake_embed):
    _use_qdrant(monkeypatch, [_point(0.80, "un solo chunk bueno"), _point(0.20, "malo")])

    results = rag.retrieve("pregunta", k=5, min_score=0.35)

    assert len(results) == 1, "no se rellena hasta k con vecinos por debajo del umbral"


def test_retrieve_devuelve_lista_vacia_si_nada_supera_el_umbral(monkeypatch, fake_embed):
    _use_qdrant(monkeypatch, [_point(0.10, "irrelevante"), _point(0.05, "más irrelevante")])

    assert rag.retrieve("¿horario del local de Miami?", min_score=0.35) == []


def test_retrieve_devuelve_payloads_no_objetos_del_sdk(monkeypatch, fake_embed):
    _use_qdrant(monkeypatch, [_point(0.90, "texto del chunk")])

    results = rag.retrieve("pregunta")

    assert all(isinstance(r, dict) for r in results)
    assert results[0]["source_document"] == "loyalty-program"
    assert not hasattr(results[0], "score"), "el score no viaja fuera de retrieve()"


# ---------------------------------------------------------------------------
# query()
# ---------------------------------------------------------------------------


def test_query_devuelve_la_salida_del_modelo(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda q, **kw: [_point(0.9, "Oro: 50+ puntos").payload])
    monkeypatch.setattr(
        rag, "generate_answer", lambda question, context: "Necesitas 50 puntos para Oro."
    )

    assert rag.query("¿cuántos puntos para Oro?") == "Necesitas 50 puntos para Oro."


def test_query_no_devuelve_texto_crudo_del_chunk(monkeypatch):
    chunk_text = "TEXTO-CRUDO-DEL-CHUNK-QUE-NO-DEBE-SALIR"
    monkeypatch.setattr(rag, "retrieve", lambda q, **kw: [_point(0.9, chunk_text).payload])
    monkeypatch.setattr(
        rag, "generate_answer", lambda question, context: "Respuesta redactada por el modelo."
    )

    answer = rag.query("pregunta")

    assert chunk_text not in answer
    assert answer == "Respuesta redactada por el modelo."


def test_query_llama_a_generate_answer_aunque_no_haya_contexto(monkeypatch):
    """Sin resultados, la respuesta honesta la produce igualmente el modelo —
    no hay un return fijo en Python que salte la generación."""
    llamadas = []
    monkeypatch.setattr(rag, "retrieve", lambda q, **kw: [])

    def fake_generate(question, context):
        llamadas.append(context)
        return "No tengo esa información en la base de conocimiento."

    monkeypatch.setattr(rag, "generate_answer", fake_generate)

    answer = rag.query("¿cuál es el horario del local de Miami?")

    assert llamadas == [[]], "generate_answer debe llamarse incluso con contexto vacío"
    assert "no tengo" in answer.lower()


def test_generate_answer_usa_el_modelo_de_generacion_no_el_de_embeddings(monkeypatch):
    monkeypatch.setenv("GENERATION_MODEL", "modelo-de-chat")
    monkeypatch.setenv("EMBEDDING_MODEL", "modelo-de-embeddings")
    capturado = {}

    class FakeOpenAI:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        def _create(self, *, model, messages, temperature):
            capturado["model"] = model
            capturado["messages"] = messages
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="respuesta"))]
            )

    monkeypatch.setattr(rag, "_openai", FakeOpenAI)

    rag.generate_answer("¿puntos para Oro?", [_point(0.9, "Oro (50+ puntos)").payload])

    assert capturado["model"] == "modelo-de-chat"
    assert capturado["model"] != "modelo-de-embeddings"
    assert "Oro (50+ puntos)" in capturado["messages"][1]["content"]


# ---------------------------------------------------------------------------
# chunk_document() — la estrategia está hecha a medida de este corpus
# ---------------------------------------------------------------------------


def test_chunking_mantiene_la_lista_junto_a_su_linea_de_entrada():
    documento = (
        "# Programa de Lealtad\n\n"
        "Párrafo introductorio del programa.\n\n"
        "Niveles del programa:\n"
        "- Bronce (0-19 puntos): descuento en bebidas.\n"
        "- Plata (20-49 puntos): descuento en el plato principal.\n"
        "- Oro (50+ puntos): 15% de descuento permanente.\n\n"
        "Párrafo final sobre la app.\n"
    )

    chunks = rag_index.chunk_document(documento, "loyalty-program")

    niveles = [c for c in chunks if c["section"] == "Niveles del programa"]
    assert len(niveles) == 1, "los tres niveles van juntos, no en chunks separados"
    assert "Bronce" in niveles[0]["text"]
    assert "Oro (50+ puntos)" in niveles[0]["text"]


def test_chunking_reune_una_lista_separada_de_su_entrada_por_una_linea_en_blanco():
    """Defensivo: el corpus hoy no tiene este caso, pero los documentos los
    edita gente de operaciones y una línea en blanco de más no debe partir
    una regla en dos chunks."""
    documento = (
        "# Protocolo\n\n"
        "Causas que requieren escalamiento:\n\n"
        "- Desperdicio superior a 5 kg en una semana.\n"
        "- Tres semanas consecutivas de merma no explicada.\n"
    )

    chunks = rag_index.chunk_document(documento, "waste-protocol")

    escalamiento = [c for c in chunks if c["section"] == "Causas que requieren escalamiento"]
    assert len(escalamiento) == 1
    assert "5 kg" in escalamiento[0]["text"]


def test_chunking_incluye_el_payload_del_context():
    documento = "# Guía de Alérgenos del Menú\n\nPárrafo uno.\n\nPárrafo dos.\n\nPárrafo tres.\n"

    chunks = rag_index.chunk_document(documento, "menu-allergens")

    for posicion, chunk in enumerate(chunks):
        assert chunk["company"] == "brasaland"
        assert chunk["language"] == "es"
        assert chunk["source_document"] == "menu-allergens"
        assert chunk["chunk_index"] == posicion
        assert chunk["section"]
        assert chunk["text"]


def test_cada_documento_real_produce_al_menos_tres_chunks():
    """El CONTEXT §5 exige ≥3 chunks por documento — se comprueba contra el
    corpus de verdad, no contra un documento de laboratorio."""
    for documento in rag_index.load_documents():
        chunks = rag_index.chunk_document(documento["text"], documento["source_document"])
        assert len(chunks) >= rag_index.MIN_CHUNKS_PER_DOCUMENT, documento["source_document"]


def test_ids_de_punto_son_deterministas():
    """Idempotencia de setup(): el mismo (documento, posición) siempre da el
    mismo ID, así que reindexar sobreescribe en vez de duplicar."""
    primero = rag_index._point_id("waste-protocol", 3)
    segundo = rag_index._point_id("waste-protocol", 3)

    assert primero == segundo
    assert primero != rag_index._point_id("waste-protocol", 4)
    assert primero != rag_index._point_id("menu-allergens", 3)
