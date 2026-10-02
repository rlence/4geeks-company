from contextlib import asynccontextmanager

import logging
import sys
import time
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from inventory.database import close_engine
from inventory.errors import InventoryError
from routes.inventory import router as inventory_router
from fastapi.middleware.cors import CORSMiddleware

from routes.incidents import router as incidents_router
from routes.agent import router as agent_router
from support_agent.service import open_service

from routes.auth import router as auth_router
from routes.knowledge import router as knowledge_router
from routes.suppliers import router as suppliers_router
from routes.telemetry import router as telemetry_router

# services/reporting es un módulo plano sibling de services/api (mismo
# mecanismo sys.path que services/telemetry, ver context/plans/hito6-part-2.md).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reporting"))
from endpoints import router as reporting_router  # noqa: E402

@asynccontextmanager
async def lifespan(app):
    with open_service() as service:
        app.state.support_agent = service
        try:
            yield
        finally:
            app.state.support_agent = None
            close_engine()


app = FastAPI(
    lifespan=lifespan,
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
async def inventory_audit(request: Request, call_next):
    if not request.url.path.startswith("/inventory/"):
        return await call_next(request)
    correlation = str(uuid4())
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", "/inventory/unknown")
    logger.info("inventory request_id=%s method=%s route=%s user=%s status=%s",
                correlation, request.method, route,
                getattr(request.state, "inventory_owner", "unauthenticated"), response.status_code)
    response.headers["X-Request-Id"] = correlation
    return response


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
app.include_router(reporting_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(incidents_router)
app.include_router(inventory_router)

@app.exception_handler(InventoryError)
async def inventory_error(request: Request, exc: InventoryError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
