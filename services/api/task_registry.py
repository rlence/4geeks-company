"""Marcador de IDs aceptados: Celery llama PENDING también a IDs desconocidos."""

from uuid import UUID

from redis import Redis

from celery_app import REDIS_URL

REGISTRY_TTL_SECONDS = 172800


def get_redis() -> Redis:
    return Redis.from_url(REDIS_URL, socket_connect_timeout=0.15, socket_timeout=0.5)


def task_key(task_id: str) -> str:
    return f"brasaland:task:{UUID(task_id)}"


def reserve_task(task_id: str) -> None:
    if not get_redis().set(task_key(task_id), "accepted", ex=REGISTRY_TTL_SECONDS, nx=True):
        raise RuntimeError("task id already exists")


def remove_task(task_id: str) -> None:
    get_redis().delete(task_key(task_id))


def is_accepted(task_id: str) -> bool:
    return get_redis().get(task_key(task_id)) == b"accepted"
