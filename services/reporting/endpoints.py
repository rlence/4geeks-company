"""Endpoints del Pipeline de Desempeño de Negocio (Hito 6, Parte 2).

Vive fuera de services/api/routes/ a propósito — el rule de este hito pide
los endpoints en su propio módulo, separado de services/telemetry/. Capa
delgada de HTTP: ninguna lógica de ETL vive acá, solo lecturas directas y
la invocación del flow importado desde data/pipelines/.
"""

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from supabase import Client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
from supabase_client import get_supabase_client  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data" / "pipelines"))
from pipeline import _previous_iso_week_start  # noqa: E402
from celery_app import app as celery_app  # noqa: E402
from task_registry import remove_task, reserve_task  # noqa: E402

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


@router.post("/pipeline-runs", status_code=status.HTTP_202_ACCEPTED)
def trigger_pipeline_run(response: Response, week_start: date | None = None) -> dict:
    # Resolver la fecha ahora: si el worker empieza mañana, el pedido no cambia.
    target = week_start or _previous_iso_week_start(datetime.now(timezone.utc).date())
    if target.weekday() != 0:
        raise HTTPException(422, "week_start must be an ISO Monday")
    task_id = str(uuid4())
    try:
        reserve_task(task_id)
        celery_app.send_task(
            "reporting.weekly_report", args=[target.isoformat()],
            task_id=task_id, queue="reporting",
        )
    except Exception as exc:
        try:
            remove_task(task_id)
        except Exception:
            pass
        raise HTTPException(503, "task broker unavailable") from exc
    response.headers["Location"] = f"/tasks/{task_id}"
    return {"task_id": task_id}


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
