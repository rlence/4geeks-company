"""Consumidor del reporte semanal; el mensaje solo transporta la fecha ISO."""

import logging
import sys
import time
from datetime import date
from pathlib import Path

from celery_app import app
from dead_letters import record_terminal_failure, safe_error

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data" / "pipelines"))
from pipeline import weekly_location_performance_flow  # noqa: E402

LOG = logging.getLogger("reporting.worker")
MAX_RETRIES = 3


@app.task(name="reporting.queue_probe")
def queue_probe() -> dict:
    """Comprueba productor, broker, worker y backend sin tocar datos de negocio."""
    return {"ok": True}


@app.task(bind=True, name="reporting.weekly_report", max_retries=MAX_RETRIES)
def run_weekly_report(self, week_start: str) -> dict:
    target = date.fromisoformat(week_start)
    if target.weekday() != 0:
        raise ValueError("week_start must be an ISO Monday")
    attempt = self.request.retries + 1
    started = time.monotonic()
    LOG.info("task_id=%s attempt=%s state=started", self.request.id, attempt)
    try:
        result = weekly_location_performance_flow(week_start=target, triggered_by="manual")
    except Exception as exc:
        duration = time.monotonic() - started
        LOG.error("task_id=%s attempt=%s state=error duration_seconds=%.3f error=%s",
                  self.request.id, attempt, duration, safe_error(exc, max_chars=None))
        if self.request.retries < MAX_RETRIES:
            self.retry(exc=exc, countdown=min(2 ** self.request.retries, 60))
        try:
            record_terminal_failure(self.request.id, target, attempt, exc)
        except Exception:
            LOG.exception("task_id=%s state=dead_letter_persist_failed", self.request.id)
        raise
    LOG.info("task_id=%s attempt=%s state=success duration_seconds=%.3f",
             self.request.id, attempt, time.monotonic() - started)
    return {"week_start": result["week_start"], "records_loaded": result["records_loaded"]}
