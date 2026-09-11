"""Pipeline de análisis técnico sobre telemetry_events (Project 6.3).

Cada función: carga (SQL, vía el Client de supabase-py) -> refina/convierte
tipos (Pandas) -> agrupa -> agrega -> devuelve una lista de dicts
serializable a JSON. Ninguna función crea su propio cliente ni aplica una
ventana de fechas por defecto — start_date/end_date los resuelve el
endpoint una sola vez.
"""

from datetime import datetime
from typing import Any

import pandas as pd

ERROR_EVENT_TYPES = ["frontend_error_captured", "api_request_failed"]


def _load(
    client: Any,
    start_date: datetime,
    end_date: datetime,
    columns: str,
    event_types: list[str] | None = None,
) -> pd.DataFrame:
    query = (
        client.table("telemetry_events")
        .select(columns)
        .gte("timestamp", start_date.isoformat())
        .lt("timestamp", end_date.isoformat())
    )
    if event_types is not None:
        query = query.in_("event_type", event_types)
    return pd.DataFrame(query.execute().data)


def events_per_day_by_type(client: Any, start_date: datetime, end_date: datetime) -> list[dict]:
    """Volumen de eventos por día y por tipo — qué tipos dominan, con dimensión temporal."""
    df = _load(client, start_date, end_date, "timestamp,event_type")
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["timestamp"], utc=True).dt.date.astype(str)
    return (
        df.groupby(["date", "event_type"])
        .size()
        .reset_index(name="count")
        .to_dict("records")
    )


def error_rate_by_day(client: Any, start_date: datetime, end_date: datetime) -> list[dict]:
    """Fracción de eventos del día que son de error (frontend_error_captured / api_request_failed)."""
    df = _load(client, start_date, end_date, "timestamp,event_type")
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["timestamp"], utc=True).dt.date.astype(str)
    df["is_error"] = df["event_type"].isin(ERROR_EVENT_TYPES)
    grouped = df.groupby("date").agg(total=("event_type", "count"), errors=("is_error", "sum"))
    grouped["error_rate"] = grouped["errors"] / grouped["total"]
    return grouped.reset_index().to_dict("records")


def api_latency_p95_by_route_per_day(
    client: Any, start_date: datetime, end_date: datetime
) -> list[dict]:
    """p95 de latencia promedio por endpoint por día, a partir de api_latency_recorded."""
    df = _load(
        client, start_date, end_date, "timestamp,tags", event_types=["api_latency_recorded"]
    )
    if df.empty:
        return []

    df["route"] = df["tags"].apply(lambda tags: tags.get("route"))
    df["p95_ms"] = df["tags"].apply(lambda tags: tags.get("p95_ms"))
    df["sample_count"] = df["tags"].apply(lambda tags: tags.get("count"))
    df = df.dropna(subset=["route"])
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["timestamp"], utc=True).dt.date.astype(str)
    grouped = df.groupby(["date", "route"]).agg(
        p95_ms=("p95_ms", "mean"), samples=("sample_count", "sum")
    )
    return grouped.reset_index().to_dict("records")


def auth_failure_rate_by_day(
    client: Any, start_date: datetime, end_date: datetime
) -> list[dict]:
    """Tasa diaria de fallos de login: login_attempt_failed / (login_attempt_failed + login_succeeded)."""
    df = _load(
        client,
        start_date,
        end_date,
        "timestamp,event_type",
        event_types=["login_attempt_failed", "login_succeeded"],
    )
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["timestamp"], utc=True).dt.date.astype(str)
    counts = df.groupby(["date", "event_type"]).size().unstack(fill_value=0)
    for column in ("login_attempt_failed", "login_succeeded"):
        if column not in counts:
            counts[column] = 0
    counts["auth_failure_rate"] = counts["login_attempt_failed"] / (
        counts["login_attempt_failed"] + counts["login_succeeded"]
    )
    return counts.reset_index()[["date", "auth_failure_rate"]].to_dict("records")
