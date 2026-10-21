"""Celery compartido por productor HTTP, worker y Flower."""

import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("brasaland", broker=REDIS_URL, backend=REDIS_URL, include=["report_tasks"])
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="reporting",
    task_routes={"reporting.weekly_report": {"queue": "reporting"}},
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3300,
    task_time_limit=3600,
    task_publish_retry=False,
    result_expires=172800,
    broker_transport_options={
        "visibility_timeout": 7200,
        "socket_connect_timeout": 0.15,
        "socket_timeout": 0.5,
    },
)
