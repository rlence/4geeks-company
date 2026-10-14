"""Nodos con responsabilidad única; el RAG se importa, nunca se duplica."""
import sys
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "pipelines"))
import rag  # noqa: E402
from .prompts import MANAGER_POLICY
from .guardrails.external import safe_records
from .guardrails.output import check_output


class AgentState(TypedDict):
    question: str
    context: list[dict]
    answer: str | None
    error_code: str | None
    decision: dict
    tool_result: dict
    rag_failed: bool
    outcome: str
    memory_context: list[dict]


class StateContract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    question: str = Field(max_length=1000)
    context: list[dict] = Field(default_factory=list)
    answer: str | None = None
    error_code: Literal["invalid_question"] | None = None
    decision: dict = Field(default_factory=dict)
    tool_result: dict = Field(default_factory=dict)
    rag_failed: bool = False
    outcome: Literal["completed", "partial", "fallback"] = "completed"
    memory_context: list[dict] = Field(default_factory=list)


class NodeFailure(RuntimeError):
    def __init__(self, node: str):
        self.node = node
        super().__init__(f"Falló el nodo {node}")


def receive_question(state):
    return {"question": rag.normalize(state["question"])}


def invalid_question(state):
    return {"error_code": "invalid_question"}


def retrieve_context(state):
    try:
        context = rag.retrieve(state.get("decision", {}).get("rag_question") or state["question"])
    except Exception:
        if state.get("decision", {}).get("source") == "both":
            return {"context": [], "rag_failed": True}
        raise
    return {"context": safe_records(context)}


def generate_answer(state):
    try:
        question = state.get("decision", {}).get("rag_question") or state["question"]
        if state.get("memory_context"):
            from .memory.logic import answer_with_memory
            answer = answer_with_memory(question, state["context"], state["memory_context"])
        else:
            answer = rag.generate_answer(question, state["context"], system_prompt=MANAGER_POLICY + "\n" + rag.SYSTEM_PROMPT)
    except Exception:
        if state.get("decision", {}).get("source") == "both":
            return {"answer": None, "rag_failed": True}
        raise
    if not isinstance(answer, str) or not answer.strip():
        if state.get("decision", {}).get("source") == "both":
            return {"answer": None, "rag_failed": True}
        raise ValueError("Respuesta del modelo vacía o inválida")
    return {"answer": answer.strip()}


def route_question(state) -> Literal["classify_request", "invalid_question"]:
    return "classify_request" if state["question"] else "invalid_question"


def route_context(state) -> Literal["generate_answer", "insufficient_context", "combine_answer"]:
    if state.get("rag_failed"):
        return "combine_answer"
    return "generate_answer" if state["context"] else "insufficient_context"


def guarded(name, function):
    def run(state):
        try:
            StateContract.model_validate(state)
            output = function(state)
            if output.get("answer") is not None:
                output["answer"] = check_output(output["answer"])
            return output
        except Exception as exc:
            raise NodeFailure(name) from exc
    return run


def classify_request(state):
    from . import routing
    from .contracts import Decision
    decision = Decision.model_validate(routing.classify(state["question"]))
    from .guardrails.policy import unsafe_reason
    from .guardrails.events import record
    if decision.source == "rag":
        decision.rag_question = state["question"]
    elif decision.rag_question and (unsafe_reason(decision.rag_question) or
            decision.rag_question.casefold() not in state["question"].casefold()):
        record("routing", "security", "block", "untrusted_rewrite")
        decision = Decision(source="unavailable")
    return {"decision": decision.model_dump()}


def route_decision(state):
    if state.get("memory_context") and state["decision"]["source"] in {"clarify", "unavailable"}:
        return "answer_from_memory"
    return {"rag": "retrieve_context", "incidents": "lookup_incident", "both": "lookup_incident",
            "clarify": "clarify_request", "readonly": "clarify_request",
            "unavailable": "routing_fallback"}[state["decision"]["source"]]


def lookup_incident(state):
    from .contracts import Decision
    from .tools.mcp_incidents import lookup, validate_result
    return {"tool_result": validate_result(lookup(Decision.model_validate(state["decision"])))}


def route_tool(state):
    if state["decision"]["source"] == "both": return "retrieve_context"
    return "answer_incident" if state["tool_result"]["status"] == "ok" else "tool_fallback"


def answer_incident(state):
    from .tools.mcp_incidents import format_result
    answer = format_result(state["tool_result"])
    if state["tool_result"]["status"] == "ok" and state.get("memory_context"):
        notes = "; ".join(f"{m['fact']} (aprobado por ti: {m['approved_at'][:10]})"
                          for m in state["memory_context"])
        answer += "\n\nContexto que aprobaste recordar, no estado oficial: " + notes
    return {"answer": answer,
            "outcome": "completed" if state["tool_result"]["status"] == "ok" else "fallback"}


def clarify_request(state):
    answer = ("Solo puedo consultar incidencias; los cambios se realizan desde el gestor."
              if state["decision"]["source"] == "readonly" else
              "Indica el número de ticket, su estado o su categoría para consultar tus incidencias.")
    return {"answer": answer}


def routing_fallback(state):
    return {"answer": "No pude determinar qué fuente consultar ahora mismo. Inténtalo de nuevo.", "outcome": "fallback"}


def answer_from_memory(state):
    from .memory.logic import answer_with_memory
    answer = answer_with_memory(state["question"], [], state["memory_context"])
    if not answer:
        raise ValueError("Respuesta del modelo vacía")
    return {"answer": answer}


def route_answer(state):
    return "combine_answer" if state.get("decision", {}).get("source") == "both" else END


def combine_answer(state):
    from .tools.mcp_incidents import format_result
    policy = state.get("answer") if not state.get("rag_failed") else None
    return {"answer": format_result(state["tool_result"]) + "\n\nPolíticas: " +
            (policy or "No pude consultar la documentación ahora mismo."),
            "outcome": "partial" if state.get("rag_failed") or state["tool_result"]["status"] != "ok" else "completed"}


# Mismas funciones de ruta para el grafo y la traza: no reclasificar al registrar.
ROUTES = {"receive_question": route_question, "classify_request": route_decision,
          "lookup_incident": route_tool, "retrieve_context": route_context,
          "generate_answer": route_answer, "insufficient_context": route_answer}


def next_node(node, state):
    value = ROUTES[node](state) if node in ROUTES else END
    return "END" if value == END else value


def build_graph():
    builder = StateGraph(AgentState)
    nodes = {"receive_question": receive_question, "invalid_question": invalid_question,
             "classify_request": classify_request, "retrieve_context": retrieve_context,
             "generate_answer": generate_answer, "insufficient_context": generate_answer,
             "lookup_incident": lookup_incident, "answer_incident": answer_incident,
             "tool_fallback": answer_incident, "clarify_request": clarify_request,
             "routing_fallback": routing_fallback, "combine_answer": combine_answer,
             "answer_from_memory": answer_from_memory}
    for name, function in nodes.items():
        builder.add_node(name, guarded(name, function))
    builder.add_edge(START, "receive_question")
    destinations = {"receive_question": ["classify_request", "invalid_question"],
        "classify_request": ["retrieve_context", "lookup_incident", "clarify_request", "routing_fallback",
                             "answer_from_memory"],
        "lookup_incident": ["retrieve_context", "answer_incident", "tool_fallback"],
        "retrieve_context": ["generate_answer", "insufficient_context", "combine_answer"],
        "generate_answer": ["combine_answer", END], "insufficient_context": ["combine_answer", END]}
    for name in nodes:
        if name in ROUTES:
            builder.add_conditional_edges(name, ROUTES[name], destinations[name])
        else:
            builder.add_edge(name, END)
    return builder
