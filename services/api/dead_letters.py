"""Auditoría en BD y publicación de referencias a la cola terminal."""

import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv
from supabase import create_client

from celery_app import app

LOG = logging.getLogger("reporting.dead_letters")
TABLE = "task_dead_letters"


def get_client():
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def safe_error(exc: BaseException, *, max_chars: int | None = 500) -> str:
    message = f"{type(exc).__name__}: {exc}"
    for name in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL", "REDIS_URL"):
        secret = os.environ.get(name)
        if secret:
            message = message.replace(secret, "[redacted]")
    return message[:max_chars] if max_chars is not None else message


def record_terminal_failure(task_id: str, week_start: date, attempts: int, exc: BaseException) -> None:
    client = get_client()
    client.table(TABLE).upsert({
        "task_id": task_id,
        "task_name": "reporting.weekly_report",
        "week_start": week_start.isoformat(),
        "attempt_count": attempts,
        "error_message": safe_error(exc),
        "publish_status": "pending",
    }, on_conflict="task_id").execute()
    publish_dead_letter(task_id, client)


def publish_dead_letter(task_id: str, client=None) -> None:
    client = client or get_client()
    message_id = str(uuid5(NAMESPACE_URL, f"brasaland-dead-letter:{task_id}"))
    app.send_task("reporting.dead_letter", args=[task_id], queue="dead_letter", task_id=message_id)
    client.table(TABLE).update({
        "publish_status": "published", "published_at": datetime.now(timezone.utc).isoformat(),
    }).eq("task_id", task_id).execute()
    LOG.info("task_id=%s state=dead_letter_published", task_id)
