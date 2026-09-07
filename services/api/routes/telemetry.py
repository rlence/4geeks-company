import logging

from fastapi import APIRouter

from models import TelemetryBatch

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

logger = logging.getLogger("api.telemetry")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.propagate = False


@router.post("/events")
def receive_events(payload: TelemetryBatch) -> dict[str, int]:
    logger.info(
        "telemetry batch received count=%d event_types=%s",
        len(payload.events),
        [event.event_type for event in payload.events],
    )
    return {"received": len(payload.events)}
