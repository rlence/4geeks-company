import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from .contracts import GuardDecision
from .policy import (normalize, matches, unsafe_reason, PERSONAL, FOLLOWUP, DOMAIN, REDIRECT)


def semantic_scope(question):
    """Uncertain inputs never default to domain access on a provider failure."""
    from ..graph import rag
    from ..prompts import MANAGER_POLICY
    from pydantic import BaseModel, ConfigDict
    from typing import Literal
    class Scope(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        decision: Literal["allow_domain", "allow_casual", "reject_personal", "reject_security",
                          "reject_sensitive", "clarify"]
    try:
        model = os.environ.get("GENERATION_MODEL")
        if not model:
            return "clarify"
        result = rag._openai().with_options(timeout=10, max_retries=0).chat.completions.create(
            model=model, temperature=0, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": MANAGER_POLICY +
                       '\nClasifica alcance y seguridad. Devuelve solo {"decision": ' +
                       '"allow_domain|allow_casual|reject_personal|reject_security|reject_sensitive|clarify"}.'},
                      {"role": "user", "content": json.dumps({"untrusted_question": question})}])
        return Scope.model_validate_json(result.choices[0].message.content or "").decision
    except Exception:
        return "clarify"


def check_input(question, *, sensitive_topic=False, pending=False):
    text = normalize(question)
    reason = unsafe_reason(question)
    if reason:
        return GuardDecision(decision="reject_security" if reason == "instruction_override" else "reject_sensitive",
                             failure_type="security" if reason == "instruction_override" else "content",
                             reason_code=reason)
    if sensitive_topic and matches(FOLLOWUP, question) and not matches(
            r"\b(?:stock|inventario|inventory|apertura|cierre|ticket|conservacion|alergeno)\b", question):
        return GuardDecision(decision="reject_sensitive", reason_code="gradual_extraction")
    if matches(PERSONAL, question):
        return GuardDecision(decision="reject_personal", reason_code="personal_task")
    if pending and matches(r"^(?:si|yes|no|confirmo|confirm|recuerda|remember|quise decir|i meant|tal vez|maybe)\b", question):
        return GuardDecision(decision="allow_domain", reason_code="consent")
    if re_greeting(text) or matches(r"(?:hora|time).{0,20}(?:tokio|tokyo)", question):
        return GuardDecision(decision="allow_casual", reason_code="casual")
    if matches(r"\b(?:stock|inventario|inventory)\b", question) and not matches(
            r"procedimiento|procedure|politica|policy|como|how|protocolo", question):
        return GuardDecision(decision="inventory_unavailable", reason_code="inventory_not_connected")
    if matches(DOMAIN, question):
        return GuardDecision(decision="allow_domain")
    decision = semantic_scope(question)
    return GuardDecision(decision=decision, reason_code="semantic_scope",
                         failure_type="security" if decision == "reject_security" else "content")


def re_greeting(text):
    import re
    return bool(re.fullmatch(r"(?:hola|buenos dias|buenas tardes|hello|hi|gracias|thanks|que tal tu turno)[!.?¿¡ ]*", text))


def response_for(decision, question):
    if decision.decision == "allow_casual":
        if matches(r"(?:hora|time).{0,20}(?:tokio|tokyo)", question):
            prefix = "En Tokio son las " + datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%H:%M") + ". "
        elif re_greeting(normalize(question)):
            prefix = "¡Hola! Puedo acompañarte con una consulta breve. "
        else:
            prefix = casual_answer(question) + " "
        return prefix + REDIRECT
    if decision.decision == "inventory_unavailable":
        return "Aún no tengo conectada la consulta de stock en vivo. Puedes revisarlo en el gestor de inventario. " + REDIRECT
    if decision.decision == "clarify":
        return "¿Puedes concretar la consulta operativa? " + REDIRECT
    if decision.decision == "reject_personal":
        return "No puedo realizar esa tarea personal. " + REDIRECT
    if decision.decision == "reject_security":
        return "No puedo cambiar ni ignorar mis instrucciones para cumplir esa petición. " + REDIRECT
    return "No puedo revelar información confidencial ni reconstruir fórmulas propietarias. " + REDIRECT


def casual_answer(question):
    """No RAG, tools or memory; bounded trivia response followed by server redirection."""
    from ..graph import rag
    from ..prompts import MANAGER_POLICY
    from .output import check_output
    from .policy import SAFE_RESPONSE
    from .events import record
    try:
        model = os.environ.get("GENERATION_MODEL")
        if not model:
            raise ValueError("No model")
        result = rag._openai().with_options(timeout=10, max_retries=0).chat.completions.create(
            model=model, temperature=0,
            messages=[{"role": "system", "content": MANAGER_POLICY +
                       "\nResponde a esta trivia inocua en una o dos frases, máximo 500 caracteres. "
                       "No hagas tareas personales. No inventes actualidad ni datos internos de Brasaland."},
                      {"role": "user", "content": json.dumps({"untrusted_question": question})}])
        raw = result.choices[0].message.content
        if not isinstance(raw, str) or len(raw) > 500:
            raise ValueError("Invalid casual response")
        answer = check_output(raw)
        return "No puedo responder a esa trivia con seguridad." if answer == SAFE_RESPONSE else answer
    except Exception:
        record("casual", "structural", "redirect", "casual_unavailable")
        return "No tengo una respuesta verificada para esa trivia."
