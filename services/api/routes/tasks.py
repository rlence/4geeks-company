"""Consulta HTTP de las tareas aceptadas por la API."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from redis.exceptions import RedisError

from celery_app import app
from task_registry import is_accepted

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
def get_task(task_id: UUID) -> dict:
    key = str(task_id)
    try:
        if not is_accepted(key):
            raise HTTPException(404, "task not found or expired")
        result = app.AsyncResult(key)
        state = result.state
    except RedisError as exc:
        raise HTTPException(503, "task backend unavailable") from exc
    status = {
        "PENDING": "pending", "RECEIVED": "pending", "RETRY": "pending",
        "STARTED": "started", "SUCCESS": "success", "FAILURE": "failure",
        "REVOKED": "failure",
    }.get(state, "pending")
    body = {"task_id": key, "status": status, "result": None}
    if state == "RETRY":
        body["retrying"] = True
    if state == "SUCCESS" and isinstance(result.result, dict):
        body["result"] = {
            "week_start": result.result.get("week_start"),
            "records_loaded": result.result.get("records_loaded"),
        }
    return body
