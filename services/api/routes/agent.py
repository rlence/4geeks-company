"""Adaptador HTTP del grafo compilado, sin lógica de RAG."""
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from support_agent.service import AgentError

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    question: str = Field(max_length=1000)


class AgentQueryResponse(BaseModel):
    answer: str


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(payload: AgentQueryRequest, request: Request, response: Response):
    service = getattr(request.app.state, "support_agent", None)
    if service is None:
        raise HTTPException(503, "El agente no está disponible en este momento.")
    try:
        answer, run_id = service.query(payload.question)
    except AgentError as exc:
        invalid = exc.code == "invalid_question"
        raise HTTPException(
            422 if invalid else 503,
            "La pregunta no puede estar vacía." if invalid else "El agente no está disponible en este momento.",
            headers={"X-Agent-Run-Id": exc.run_id},
        ) from None
    response.headers["X-Agent-Run-Id"] = run_id
    return AgentQueryResponse(answer=answer)
