import time
from typing import Any, Hashable


class TTLCache:
    """Diccionario en memoria con expiración por entrada. Sin locks:
    uvicorn en dev corre un solo worker y las rutas son funciones sync
    (FastAPI las corre en threadpool, pero una carrera aquí en el peor
    caso resulta en una lectura extra a TinyDB, nunca en un dato corrupto)."""

    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._store: dict[Hashable, tuple[float, Any]] = {}

    def get(self, key: Hashable) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            del self._store[key]
            return None
        return value

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._store.clear()
