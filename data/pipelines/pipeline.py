"""Pipeline de Desempeño de Negocio — Hito 6, Partes 2 y 3.

Extrae de `telemetry_events` (solo lectura, schema `public`), transforma
con `data/process/weekly_aggregation.py`, y carga en
`reporting.weekly_location_performance` (upsert). Cada corrida se registra
en `reporting.pipeline_runs`. No toca `services/telemetry/analysis.py` ni
`GET /telemetry/report`.

Parte 3: el flow principal ya no contiene la lógica ETL directamente —
coordina 4 subflows (extracción, transformación, carga, snapshot opcional),
cada uno con inputs/outputs explícitos y ejecutable de forma independiente.

Corre como script (`if __name__ == "__main__"`) usando el venv de
services/api, que es donde viven prefect/pandas/supabase-py en este
monorepo (ver Contexto de context/plans/hito6-part-2.md — data/ no tiene
su propio entorno para no romper el import en proceso que necesita
services/reporting/endpoints.py):

    cd services/api && uv run python ../../data/pipelines/pipeline.py
"""

import logging
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE
from prefect.states import State
from prefect.tasks import task_input_hash
from supabase import Client, create_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from process.weekly_aggregation import (  # noqa: E402
    compute_weekly_kpis,
    dedup_events,
    validate_weekly_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "data" / "eval"

logger = logging.getLogger("pipelines.weekly_location_performance")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False


def get_supabase_client() -> Client:
    # Decidido a propósito: no importa services/api/config.py, que exige
    # JWT_SECRET_KEY/RESEND_API_KEY que no tienen nada que ver con este
    # pipeline — se lee el mismo .env raíz directamente.
    load_dotenv(REPO_ROOT / ".env")
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def _previous_iso_week_start(today: date) -> date:
    monday_this_week = today - timedelta(days=today.weekday())
    return monday_this_week - timedelta(days=7)


SOURCE_EVENT_TYPES = [
    "inbound_order_created",
    "stock_waste_registered",
    "stock_threshold_triggered",
    "ingredient_price_variance_detected",
]

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(retries=3, retry_delay_seconds=5, cache_policy=NO_CACHE)
def extract_telemetry_events(client: Client, week_start: date, week_end: date) -> list[dict]:
    # retries=3 / retry_delay_seconds=5: llamada de red a Supabase — 3
    # reintentos cortos absorben un timeout transitorio sin retrasar de
    # forma perceptible una corrida semanal (el flow completo corre una
    # vez por semana, unos segundos extra no importan).
    # cache_policy=NO_CACHE: el cache policy por defecto de Prefect 3
    # hashea los inputs de la task, y `client` (supabase.Client) no es
    # serializable — sin esto la task explota al intentar cachear.
    response = (
        client.table("telemetry_events")
        .select("event_id,event_type,timestamp,tags")
        .gte("timestamp", week_start.isoformat())
        .lt("timestamp", week_end.isoformat())
        .in_("event_type", SOURCE_EVENT_TYPES)
        .execute()
    )
    return response.data


@task(cache_policy=NO_CACHE)
def dedup_events_task(events: list[dict]) -> list[dict]:
    return dedup_events(events)


@task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
def compute_weekly_kpis_task(events: list[dict], week_start: date) -> list[dict]:
    # cache_key_fn=task_input_hash: la clave es el hash de (events,
    # week_start) — si la misma corrida se reintenta dentro de la hora
    # (mismo ticket: "si una task ya corrió exitosamente en la última
    # hora, no debe repetirse"), Prefect reusa el resultado sin volver a
    # correr el groupby de Pandas sobre el mismo input.
    return compute_weekly_kpis(events, week_start)


@task(cache_policy=NO_CACHE)
def validate_weekly_rows_task(rows: list[dict]) -> list[dict]:
    return validate_weekly_rows(rows)


@task(retries=3, retry_delay_seconds=5, cache_policy=NO_CACHE)
def load_weekly_performance(client: Client, rows: list[dict]) -> int:
    if not rows:
        return 0
    client.schema("reporting").table("weekly_location_performance").upsert(
        rows, on_conflict="location_id,week_start"
    ).execute()
    return len(rows)


@task
def snapshot_to_eval(rows: list[dict], week_start: date) -> None:
    # Paso opcional/no crítico: exporta un snapshot para QA manual. Si
    # falla (ej. permisos de disco), no debe tumbar la corrida — ver el
    # manejo con return_state=True en el flow principal.
    import json

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    path = EVAL_DIR / f"weekly_location_performance_{week_start.isoformat()}.json"
    path.write_text(json.dumps(rows, indent=2))


@task(retries=3, retry_delay_seconds=5, cache_policy=NO_CACHE)
def log_pipeline_run(client: Client, run_id: str | None = None, **fields: Any) -> str:
    run_id = run_id or str(uuid.uuid4())
    client.schema("reporting").table("pipeline_runs").upsert([{"id": run_id, **fields}]).execute()
    return run_id


# ---------------------------------------------------------------------------
# Subflows — cada uno con inputs/outputs explícitos, sin estado global
# compartido, ejecutable y monitoreable por separado del flow principal.
# ---------------------------------------------------------------------------


@flow(name="extract_weekly_events_flow", validate_parameters=False)
def extract_weekly_events_flow(client: Client, week_start: date, week_end: date) -> list[dict]:
    # validate_parameters=False: Prefect valida por defecto los tipos de
    # parámetros del flow con Pydantic, y supabase.Client no es un tipo
    # que Pydantic sepa validar como instancia arbitraria — además, los
    # tests inyectan un fake client en su lugar (ver reporting_fakes.py),
    # que la validación estricta rechazaría igual aunque fuera válido.
    return extract_telemetry_events(client, week_start, week_end)


@flow(name="transform_weekly_performance_flow")
def transform_weekly_performance_flow(events: list[dict], week_start: date) -> list[dict]:
    deduped = dedup_events_task(events)
    kpis = compute_weekly_kpis_task(deduped, week_start)
    return validate_weekly_rows_task(kpis)


@flow(name="load_weekly_performance_flow", validate_parameters=False)
def load_weekly_performance_flow(client: Client, rows: list[dict]) -> int:
    return load_weekly_performance(client, rows)


@flow(name="snapshot_weekly_eval_flow")
def snapshot_weekly_eval_flow(rows: list[dict], week_start: date) -> None:
    snapshot_to_eval(rows, week_start)


# ---------------------------------------------------------------------------
# Flow principal — coordina los subflows, no contiene lógica ETL.
# ---------------------------------------------------------------------------


@flow(name="weekly_location_performance_flow")
def weekly_location_performance_flow(week_start: date | None = None) -> dict:
    run_logger = get_run_logger()
    client = get_supabase_client()

    week_start = week_start or _previous_iso_week_start(datetime.now(timezone.utc).date())
    week_end = week_start + timedelta(days=7)
    started_at = datetime.now(timezone.utc)

    run_id = log_pipeline_run(
        client,
        week_start=week_start.isoformat(),
        started_at=started_at.isoformat(),
        status="running",
        triggered_by="manual",
    )

    try:
        events = extract_weekly_events_flow(client, week_start, week_end)
        rows = transform_weekly_performance_flow(events, week_start)
        stored = load_weekly_performance_flow(client, rows)

        snapshot_state: State = snapshot_weekly_eval_flow(rows, week_start, return_state=True)
        if snapshot_state.is_failed():
            run_logger.warning(
                "snapshot_weekly_eval_flow falló, no crítico — la corrida sigue: %s", snapshot_state
            )

        log_pipeline_run(
            client,
            run_id=run_id,
            week_start=week_start.isoformat(),
            started_at=started_at.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            status="completed",
            records_extracted=len(events),
            records_loaded=stored,
            triggered_by="manual",
        )
        return {"week_start": week_start.isoformat(), "records_loaded": stored}
    except Exception as exc:
        log_pipeline_run(
            client,
            run_id=run_id,
            week_start=week_start.isoformat(),
            started_at=started_at.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            status="failed",
            error_message=str(exc),
            triggered_by="manual",
        )
        raise


if __name__ == "__main__":
    result = weekly_location_performance_flow()
    logger.info("weekly_location_performance_flow terminó: %s", result)
