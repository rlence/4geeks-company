"""Recuperación y generación del asistente de conocimiento (Hito 7).

`query()` es la única función que deben llamar consumidores externos
(hoy: services/api/routes/knowledge.py). Se compone de dos pasos que viven
en funciones separadas a propósito: el agente LangGraph de un hito
posterior llamará `retrieve()` y `generate_answer()` como pasos distintos,
sin ejecutar la recuperación dos veces ni re-envolver un monolito.

La respuesta final SIEMPRE la genera el modelo a partir del contexto
recuperado. En ningún camino se devuelve texto crudo de la base vectorial
—ni siquiera cuando no se recupera nada: ese caso también pasa por el
modelo, que responde que no tiene información suficiente.
"""

import logging
import os
import sys
from pathlib import Path

from qdrant_client import models

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data" / "process"))
from rag_index import COLLECTION_NAME, _openai, _qdrant, embed, normalize  # noqa: E402

logger = logging.getLogger("rag.pipeline")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.propagate = False

# Umbral de similitud coseno. Con un corpus de solo 18 chunks casi cualquier
# pregunta tiene algún vecino, así que este umbral es lo único que separa un
# "no tengo esa información" honesto de una respuesta construida sobre un
# chunk irrelevante. Afinado con data/eval/recall_at_3.py — ver
# docs/rag/rag-design.md para el criterio.
MIN_SCORE = 0.35

DEFAULT_K = 5

SYSTEM_PROMPT = """\
Eres el asistente de conocimiento de Brasaland, una cadena de restaurantes \
a la brasa con locales en Colombia y Florida. Respondes a gerentes de local \
como lo haría un vendedor entrenado: con seguridad, de forma directa y \
accionable, en español.

Reglas que no puedes romper:

1. Responde ÚNICAMENTE con información presente en el CONTEXTO que se te \
entrega. No uses conocimiento general sobre restaurantes ni sobre Brasaland.
2. No inventes ningún dato numérico. Cualquier porcentaje, monto, peso, \
plazo o cantidad de puntos debe aparecer literalmente en el CONTEXTO.
3. Los montos en dólares y pesos colombianos se citan tal como aparecen en \
el CONTEXTO. Nunca conviertas de una moneda a otra.
4. En preguntas sobre alérgenos, sigue la redacción del contexto al pie de \
la letra. Nunca afirmes que un plato es seguro o "sin riesgo" para una \
persona alérgica: el protocolo de Brasaland es que nunca se garantiza cero \
riesgo de contaminación cruzada.
5. Si el CONTEXTO está vacío o no contiene lo necesario para responder, \
dilo con claridad: que la base de conocimiento no tiene esa información y \
que conviene consultar con el área correspondiente. No rellenes el hueco \
con suposiciones.
"""


def retrieve(query: str, *, k: int = DEFAULT_K, min_score: float = MIN_SCORE) -> list[dict]:
    """Busca los chunks más cercanos a la pregunta y filtra por similitud.

    Devuelve los payloads (dicts), no objetos del SDK de Qdrant: quien
    consume esta función no debería depender del cliente vectorial. Puede
    devolver menos de `k` resultados, incluso ninguno — no se fuerza a
    rellenar hasta k con vecinos malos.
    """
    response = _qdrant().query_points(
        collection_name=COLLECTION_NAME,
        query=embed(query),
        limit=k,
        with_payload=True,
    )

    payloads = []
    for point in response.points:
        if point.score < min_score:
            continue
        payload = dict(point.payload or {})
        payloads.append(payload)

    # Los scores se registran del lado servidor para poder depurar y afinar
    # el umbral; nunca salen al cliente (lo prohíbe la Fase 3 del rule).
    logger.info(
        "retrieve q=%r k=%d min_score=%.2f -> %d/%d sobre el umbral (scores=%s)",
        query[:60],
        k,
        min_score,
        len(payloads),
        len(response.points),
        [round(p.score, 3) for p in response.points],
    )
    return payloads


def _format_context(context: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"[Fuente: {chunk.get('source_document')} — {chunk.get('section')}]\n{chunk.get('text', '')}"
        for chunk in context
    )


def generate_answer(question: str, context: list[dict]) -> str:
    """Arma el prompt con el contexto recuperado y llama al LLM de generación.

    Usa GENERATION_MODEL, nunca EMBEDDING_MODEL. Se llama incluso con
    `context` vacío: la respuesta honesta de "no tengo esa información"
    también la produce el modelo, no un return fijo en Python.
    """
    model = os.environ.get("GENERATION_MODEL")
    if not model:
        raise RuntimeError("Falta GENERATION_MODEL en el entorno.")

    user_prompt = (
        f"CONTEXTO:\n{_format_context(context) if context else '(sin resultados relevantes)'}\n\n"
        f"PREGUNTA DEL GERENTE: {question}"
    )

    response = _openai().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


def query(question: str) -> str:
    """Punto de entrada único: recuperar y generar."""
    return generate_answer(question, retrieve(normalize(question)))


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    pregunta = " ".join(sys.argv[1:]) or "¿Cuántos puntos necesito para el nivel Oro?"
    print(query(pregunta))
