import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from routes.auth import router as auth_router
from routes.suppliers import router as suppliers_router
from routes.telemetry import router as telemetry_router

app = FastAPI(
    title="Brasaland — API",
    description="API de gestión del directorio de proveedores y autenticación de usuarios.",
    version="0.1.0",
)

logger = logging.getLogger("api.timing")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.propagate = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000

    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} | {duration:.1f}ms"
    )
    return response


app.include_router(suppliers_router)
app.include_router(auth_router)
app.include_router(telemetry_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
