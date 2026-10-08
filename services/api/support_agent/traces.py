"""Formato de trazas y escritura atómica; sin dependencia de proveedores."""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node: Literal["receive_question", "invalid_question", "retrieve_context",
                  "generate_answer", "insufficient_context", "runtime", "classify_request",
                  "lookup_incident", "answer_incident", "tool_fallback", "clarify_request",
                  "routing_fallback", "combine_answer", "answer_from_memory", "memory_decision"]
    status: Literal["completed", "failed"]
    output: dict = Field(default_factory=dict)
    next_node: str | None = None
    error_code: str | None = None


class Trace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1, 2, 3] = 3
    run_id: UUID
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    question: str
    status: Literal["running", "completed", "invalid_question", "failed", "partial", "fallback"] = "running"
    provenance: dict
    events: list[Event] = Field(default_factory=list)
    answer: str | None = None
    error_code: str | None = None


def save_trace(directory: Path, trace: Trace):
    destination = directory / f"{trace.run_id}.json"
    temporary = destination.with_suffix(".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(trace.model_dump_json(indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def load_trace(path: Path) -> Trace:
    trace = Trace.model_validate_json(path.read_text(encoding="utf-8"))
    if trace.status == "running" or trace.finished_at is None or not trace.events:
        raise ValueError(f"Traza incompleta: {path.name}")
    return trace
