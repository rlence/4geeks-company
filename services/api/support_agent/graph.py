"""Nodos con responsabilidad única; el RAG se importa, nunca se duplica."""
import sys
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "pipelines"))
import rag  # noqa: E402


class AgentState(TypedDict):
    question: str
    context: list[dict]
    answer: str | None
    error_code: str | None


class StateContract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    question: str = Field(max_length=1000)
    context: list[dict] = Field(default_factory=list)
    answer: str | None = None
    error_code: Literal["invalid_question"] | None = None


class NodeFailure(RuntimeError):
    def __init__(self, node: str):
        self.node = node
        super().__init__(f"Falló el nodo {node}")


def receive_question(state):
    return {"question": rag.normalize(state["question"])}


def invalid_question(state):
    return {"error_code": "invalid_question"}


def retrieve_context(state):
    context = rag.retrieve(state["question"])
    StateContract(question=state["question"], context=context)
    if any(not isinstance(chunk.get("text"), str) for chunk in context):
        raise ValueError("Payload sin texto")
    return {"context": context}


def generate_answer(state):
    answer = rag.generate_answer(state["question"], state["context"])
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Respuesta del modelo vacía o inválida")
    return {"answer": answer.strip()}


def route_question(state) -> Literal["retrieve_context", "invalid_question"]:
    return "retrieve_context" if state["question"] else "invalid_question"


def route_context(state) -> Literal["generate_answer", "insufficient_context"]:
    return "generate_answer" if state["context"] else "insufficient_context"


def guarded(name, function):
    def run(state):
        try:
            StateContract.model_validate(state)
            return function(state)
        except Exception as exc:
            raise NodeFailure(name) from exc
    return run


def build_graph():
    builder = StateGraph(AgentState)
    for name, function in (
        ("receive_question", receive_question),
        ("invalid_question", invalid_question),
        ("retrieve_context", retrieve_context),
        ("generate_answer", generate_answer),
        # Contexto vacío: conserva el contrato RAG de respuesta generada por LLM.
        ("insufficient_context", generate_answer),
    ):
        builder.add_node(name, guarded(name, function))
    builder.add_edge(START, "receive_question")
    builder.add_conditional_edges("receive_question", route_question)
    builder.add_conditional_edges("retrieve_context", route_context)
    for name in ("invalid_question", "generate_answer", "insufficient_context"):
        builder.add_edge(name, END)
    return builder
