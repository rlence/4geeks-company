"""Endpoint del asistente de base de conocimiento (Hito 7).

Capa delgada de HTTP: ninguna lógica de recuperación ni de generación vive
aquí. El router solo valida la pregunta, delega en query() de
data/pipelines/rag.py y devuelve el string generado.

Nunca se exponen al cliente los resultados crudos de Qdrant, los chunks ni
las puntuaciones de similitud — eso se registra del lado servidor, dentro
del propio pipeline.
"""

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# data/pipelines es un módulo plano sibling de services/, alcanzado por
# sys.path relativo — mismo mecanismo que routes/telemetry.py y
# services/reporting/endpoints.py (ver .agents/rules/monorepo-imports.md).
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data" / "pipelines"))
from rag import query  # noqa: E402

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

logger = logging.getLogger("api.knowledge")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.propagate = False


class KnowledgeQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class KnowledgeQueryResponse(BaseModel):
    answer: str


@router.post("/query", response_model=KnowledgeQueryResponse)
def ask_knowledge_base(payload: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    try:
        answer = query(payload.question)
    except Exception:
        # Un fallo de Qdrant o del proveedor de modelos debe verse como un
        # error, no como una respuesta vacía: la UI distingue los dos casos
        # y el gerente no debe interpretar un 200 mudo como "no hay datos".
        logger.exception("knowledge query failed question=%r", payload.question[:60])
        raise HTTPException(
            status_code=503,
            detail="La base de conocimiento no está disponible en este momento.",
        )

    return KnowledgeQueryResponse(answer=answer)
