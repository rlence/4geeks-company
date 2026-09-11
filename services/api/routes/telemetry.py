import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from supabase import Client

from cache import TTLCache
from models import TelemetryEvent
from supabase_client import get_supabase_client

# services/telemetry es un módulo plano sibling de services/api, sin
# pyproject.toml propio (ver Decisión 1 del plan de Project 6.3): una
# dependencia uv de path se resolvería a una ruta absoluta de esta
# máquina al exportar requirements.txt, y rompería el build de Docker.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "telemetry"))
from analysis import (  # noqa: E402
    api_latency_p95_by_route_per_day,
    auth_failure_rate_by_day,
    error_rate_by_day,
    events_per_day_by_type,
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

logger = logging.getLogger("api.telemetry")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.propagate = False

# El reporte no recalcula en cada request: mismo (start_date, end_date)
# dentro de 60s devuelve el resultado ya calculado, mismo patrón que
# _suppliers_cache en routes/suppliers.py.
REPORT_CACHE_TTL_SECONDS = 60
_report_cache = TTLCache(ttl_seconds=REPORT_CACHE_TTL_SECONDS)


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


def _parse_bound(value: str | None, default: datetime) -> datetime:
    if value is None:
        return default
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@router.get("/report")
def get_report(
    start_date: str | None = None,
    end_date: str | None = None,
    supabase: Client = Depends(get_supabase_client),
) -> dict:
    end = _parse_bound(end_date, datetime.now(timezone.utc))
    start = _parse_bound(start_date, end - timedelta(days=7))

    cache_key = (start.isoformat(), end.isoformat())
    cached = _report_cache.get(cache_key)
    if cached is not None:
        return cached

    report = {
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        "metrics": {
            "events_per_day": events_per_day_by_type(supabase, start, end),
            "error_rate_by_day": error_rate_by_day(supabase, start, end),
            "api_latency_p95_by_route": api_latency_p95_by_route_per_day(supabase, start, end),
            "auth_failure_rate": auth_failure_rate_by_day(supabase, start, end),
        },
    }
    _report_cache.set(cache_key, report)
    return report
