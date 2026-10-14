from .policy import unsafe_reason, SAFE_RESPONSE
from .events import record


def check_output(answer):
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 12000:
        record("output", "structural", "block", "invalid_answer")
        return SAFE_RESPONSE
    reason = unsafe_reason(answer)
    # Detect verbatim system text even when it contains no trigger words.
    from ..prompts import MANAGER_POLICY
    from .policy import normalize
    normalized = normalize(answer)
    from ..graph import rag
    from ..routing import PROMPT
    from ..memory.logic import DECIDE_PROMPT, EVALUATE_PROMPT
    for prompt in (MANAGER_POLICY, rag.SYSTEM_PROMPT, PROMPT, DECIDE_PROMPT, EVALUATE_PROMPT):
        words = normalize(prompt).split()
        if any(" ".join(words[i:i + 12]) in normalized for i in range(len(words) - 11)):
            reason = "system_disclosure"
    if reason:
        record("output", "security" if reason in {"instruction_override", "system_disclosure"} else "content",
               "block", reason)
        return SAFE_RESPONSE
    return answer.strip()
