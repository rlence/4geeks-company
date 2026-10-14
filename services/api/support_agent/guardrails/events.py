"""Per-request telemetry, without raw payloads or credentials."""
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

current_events = ContextVar("guardrail_events", default=None)
current_run = ContextVar("guardrail_run", default=None)
logger = logging.getLogger("agent.guardrails")

def record(guardrail_id, failure_type, action, reason_code):
    event = dict(agent_id="manager_support", run_id=current_run.get(), guardrail_id=guardrail_id,
                 failure_type=failure_type, action=action, reason_code=reason_code,
                 policy_version="1", occurred_at=datetime.now(timezone.utc).isoformat())
    events = current_events.get()
    if events is not None:
        events.append(event)
    logger.info("guardrail %s", event)
