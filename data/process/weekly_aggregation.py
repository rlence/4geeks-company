"""Transformación pura del pipeline de Desempeño de Negocio (Hito 6, Parte 2).

Sin Prefect ni I/O de red — recibe eventos ya extraídos de telemetry_events
(filas crudas: event_id, timestamp, event_type, tags, ...) y devuelve filas
listas para reporting.weekly_location_performance. Testeable sin mockear
Supabase ni Prefect. `data/pipelines/pipeline.py` envuelve estas funciones
en tasks; esta capa no sabe que Prefect existe.
"""

from datetime import date

import pandas as pd

COUNTRY_CURRENCY = {"CO": "COP", "US": "USD"}

_COST_EVENT_TYPES = ["inbound_order_created", "stock_waste_registered"]
_COUNT_EVENT_TYPES = ["stock_threshold_triggered", "ingredient_price_variance_detected"]

_COST_COLUMN_RENAME = {
    "inbound_order_created": "total_purchase_cost",
    "stock_waste_registered": "total_waste_cost",
}
_COUNT_COLUMN_RENAME = {
    "stock_threshold_triggered": "stockout_events_count",
    "ingredient_price_variance_detected": "price_alert_events_count",
}

_OUTPUT_COLUMNS = [
    "location_id",
    "country",
    "week_start",
    "total_purchase_cost",
    "total_waste_cost",
    "waste_ratio",
    "stockout_events_count",
    "price_alert_events_count",
    "currency",
]


def dedup_events(events: list[dict]) -> list[dict]:
    """Descarta duplicados por event_id — telemetry_events es append-only,
    pero la transformación no confía en que la capa de captura/almacenamiento
    ya garantizó unicidad (defensivo, ver PIPELINE_DESIGN.md §2.5)."""
    seen: set[str] = set()
    deduped = []
    for event in events:
        event_id = event.get("event_id")
        if event_id in seen:
            continue
        seen.add(event_id)
        deduped.append(event)
    return deduped


def compute_weekly_kpis(events: list[dict], week_start: date) -> list[dict]:
    """Agrupa por (location_id, country) y calcula los 5 campos de
    reporting.weekly_location_performance. `events` ya viene filtrado por
    event_type y ventana de tiempo desde la etapa de extracción (SQL)."""
    if not events:
        return []

    df = pd.DataFrame(events)
    df["location_id"] = df["tags"].apply(lambda t: t.get("location_id"))
    df["country"] = df["tags"].apply(lambda t: t.get("country"))
    df["quantity"] = df["tags"].apply(lambda t: t.get("quantity", 0) or 0)
    df["unit_cost"] = df["tags"].apply(lambda t: t.get("unit_cost", 0) or 0)
    df = df.dropna(subset=["location_id", "country"])
    if df.empty:
        return []
    df["cost"] = df["quantity"].astype(float) * df["unit_cost"].astype(float)

    cost_by_type = (
        df[df["event_type"].isin(_COST_EVENT_TYPES)]
        .groupby(["location_id", "country", "event_type"])["cost"]
        .sum()
        .unstack(fill_value=0.0)
    )
    counts_by_type = (
        df[df["event_type"].isin(_COUNT_EVENT_TYPES)]
        .groupby(["location_id", "country", "event_type"])
        .size()
        .unstack(fill_value=0)
    )

    combined = cost_by_type.join(counts_by_type, how="outer").fillna(0)
    for column in (*_COST_EVENT_TYPES, *_COUNT_EVENT_TYPES):
        if column not in combined:
            combined[column] = 0
    combined = combined.rename(columns={**_COST_COLUMN_RENAME, **_COUNT_COLUMN_RENAME})

    combined["waste_ratio"] = combined.apply(
        lambda row: row["total_waste_cost"] / row["total_purchase_cost"]
        if row["total_purchase_cost"] > 0
        else 0.0,
        axis=1,
    )
    combined["stockout_events_count"] = combined["stockout_events_count"].astype(int)
    combined["price_alert_events_count"] = combined["price_alert_events_count"].astype(int)

    combined = combined.reset_index()
    combined["location_id"] = combined["location_id"].astype(str)
    combined["week_start"] = week_start.isoformat()
    combined["currency"] = combined["country"].map(COUNTRY_CURRENCY).fillna("USD")

    return combined[_OUTPUT_COLUMNS].to_dict("records")
