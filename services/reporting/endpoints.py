"""Endpoints del Pipeline de Desempeño de Negocio (Hito 6, Parte 2).

Vive fuera de services/api/routes/ a propósito — el rule de este hito pide
los endpoints en su propio módulo, separado de services/telemetry/. Capa
delgada de HTTP: ninguna lógica de ETL vive acá, solo lecturas directas y
la invocación del flow importado desde data/pipelines/.
"""

import sys
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends
from supabase import Client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
from supabase_client import get_supabase_client  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data" / "pipelines"))
from pipeline import weekly_location_performance_flow  # noqa: E402

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get("/pipeline-runs/latest")
def get_latest_pipeline_run(supabase: Client = Depends(get_supabase_client)) -> dict:
    response = (
        supabase.schema("reporting")
        .table("pipeline_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else {}


@router.post("/pipeline-runs")
def trigger_pipeline_run(week_start: str | None = None) -> dict:
    # week_start opcional: permite recalcular una semana específica ya
    # publicada (evento tardío, corrección) en vez de solo la última.
    parsed_week_start = date.fromisoformat(week_start) if week_start else None
    return weekly_location_performance_flow(week_start=parsed_week_start)


@router.get("/weekly-location-performance")
def get_weekly_location_performance(
    week_start: str | None = None, supabase: Client = Depends(get_supabase_client)
) -> dict:
    def performance_table():
        return supabase.schema("reporting").table("weekly_location_performance")

    resolved_week_start = week_start
    if resolved_week_start is None:
        latest = (
            performance_table().select("week_start").order("week_start", desc=True).limit(1).execute()
        )
        if not latest.data:
            return {"week_start": None, "locations": []}
        resolved_week_start = latest.data[0]["week_start"]

    rows = performance_table().select("*").eq("week_start", resolved_week_start).execute().data
    locations = [
        {
            "location_id": row["location_id"],
            "country": row["country"],
            "total_purchase_cost": row["total_purchase_cost"],
            "total_waste_cost": row["total_waste_cost"],
            "waste_ratio": row["waste_ratio"],
            "stockout_events_count": row["stockout_events_count"],
            "price_alert_events_count": row["price_alert_events_count"],
            "currency": row["currency"],
        }
        for row in rows
    ]
    return {"week_start": resolved_week_start, "locations": locations}
