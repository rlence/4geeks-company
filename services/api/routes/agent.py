"""Adaptador HTTP del grafo compilado, sin lógica de RAG."""
from fastapi import APIRouter, HTTPException, Request, Response, Header
from auth import get_current_user
from pydantic import BaseModel, ConfigDict, Field, field_validator

from support_agent.service import AgentError
from support_agent.memory.repository import MemoryConflict
from uuid import UUID

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    question: str = Field(max_length=1000)
    conversation_id: str | None = None

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, value):
        return str(UUID(value)) if value is not None else None


class AgentQueryResponse(BaseModel):
    answer: str
    conversation_id: UUID | None = None


@router.post("/query", response_model=AgentQueryResponse, response_model_exclude_none=True)
def query_agent(payload: AgentQueryRequest, request: Request, response: Response, authorization: str = Header(default="")):
    # RAG público conservado; identidad validada solo cuando se proporciona sesión.
    access_token = None
    owner_id = None
    if authorization:
        owner_id = get_current_user(authorization).doc_id
        access_token = authorization.removeprefix("Bearer ").strip()
    elif payload.conversation_id:
        raise HTTPException(401, "Se requiere iniciar sesión para continuar la conversación.")
    service = getattr(request.app.state, "support_agent", None)
    if service is None:
        raise HTTPException(503, "El agente no está disponible en este momento.")
    try:
        if owner_id is None:
            answer, run_id = service.query(payload.question, access_token=access_token)
            conversation_id = None
        else:
            answer, run_id, conversation_id = service.query_with_memory(
                payload.question, owner_id=owner_id,
                conversation_id=payload.conversation_id,
                access_token=access_token,
            )
    except MemoryConflict as exc:
        raise HTTPException(409, str(exc)) from None
    except AgentError as exc:
        invalid = exc.code == "invalid_question"
        raise HTTPException(
            422 if invalid else 503,
            "La pregunta no puede estar vacía." if invalid else "El agente no está disponible en este momento.",
            headers={"X-Agent-Run-Id": exc.run_id},
        ) from None
    response.headers["X-Agent-Run-Id"] = run_id
    return AgentQueryResponse(answer=answer, conversation_id=conversation_id)
