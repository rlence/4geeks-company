import logging

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from supabase import Client

from models import TelemetryEvent
from supabase_client import get_supabase_client

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

logger = logging.getLogger("api.telemetry")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.propagate = False


def _to_row(event: TelemetryEvent) -> dict:
    return {
        "event_id": event.eventId,
        "timestamp": event.timestamp,
        "session_id": event.sessionId,
        "user_id": event.userId,
        "event_type": event.event_type,
        "schema_version": event.schemaVersion,
        "request_id": event.requestId,
        "tags": event.properties,
    }


@router.post("/events")
def receive_events(
    payload: dict, supabase: Client = Depends(get_supabase_client)
) -> dict[str, int]:
    raw_events = payload.get("events", [])

    rows = []
    rejected = 0
    for raw in raw_events:
        try:
            event = TelemetryEvent.model_validate(raw)
        except ValidationError:
            rejected += 1
            continue
        rows.append(_to_row(event))

    if rows:
        # upsert + ignore_duplicates en vez de insert: un reintento del
        # frontend (mismo batch tras un timeout) reenvía los mismos
        # eventId — sin esto, la segunda entrega rompería por violación
        # de la PK en vez de no-opear sobre la fila ya guardada.
        supabase.table("telemetry_events").upsert(
            rows, on_conflict="event_id", ignore_duplicates=True
        ).execute()

    logger.info(
        "telemetry batch received=%d stored=%d rejected=%d",
        len(raw_events),
        len(rows),
        rejected,
    )
    return {"received": len(raw_events), "stored": len(rows), "rejected": rejected}
