from typing import Literal
from pydantic import BaseModel, ConfigDict

class GuardDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    decision: Literal["allow_domain", "allow_casual", "reject_personal", "reject_security",
                      "reject_sensitive", "clarify", "inventory_unavailable"]
    guardrail_id: str = "input"
    failure_type: Literal["structural", "content", "security"] = "content"
    reason_code: str = "scope"
    policy_version: str = "1"
