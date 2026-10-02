"""FastMCP sobre Streamable HTTP, protegido exclusivamente por MCP Auth."""

import json
import logging
from typing import Annotated, Literal

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware as MCPMiddleware, MiddlewareContext
from mcpauth import MCPAuth, ResourceServerConfig
from mcpauth.config import AuthServerConfig, AuthServerType
from mcpauth.types import ResourceServerMetadata, VerifyAccessTokenFunction
from mcpauth.utils import fetch_server_config
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.routing import Mount

from .config import Settings
from .contracts import Category, Country, Incident, IncidentList, InventoryResult, Status

logger = logging.getLogger("brasaland.mcp")
SCOPES = ["mcp:access", "incidents:read", "incidents:write", "inventory:read"]


def _error(code: str, message: str, **details) -> ToolError:
    return ToolError(json.dumps({"code": code, "message": message, **details}, ensure_ascii=False))


class CompanyApi:
    def __init__(self, base_url: str, auth: MCPAuth, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.timeout = timeout

    def require(self, *required: str):
        info = self.auth.auth_info
        if info is None:
            raise _error("authentication_required", "Se necesita un access token OAuth válido.")
        missing = sorted(set(required) - set(info.scopes))
        if missing:
            raise _error(
                "insufficient_scope",
                "El token no concede los permisos necesarios para esta herramienta.",
                required_scopes=list(required),
                missing_scopes=missing,
            )
        return info

    async def request(self, method: str, path: str, *, params=None, json_body=None):
        info = self.require()
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    path,
                    params=params,
                    json=json_body,
                    headers={"Authorization": f"Bearer {info.token}"},
                )
        except httpx.TimeoutException as exc:
            raise _error("upstream_timeout", "La API de la compañía agotó el tiempo de espera.") from exc
        except httpx.HTTPError as exc:
            raise _error("upstream_unavailable", "No se pudo conectar con la API de la compañía.") from exc

        if response.is_success:
            return response.json()
        code, message = {
            401: ("upstream_authentication_error", "La API rechazó la identidad OAuth."),
            403: ("upstream_authorization_error", "La identidad no tiene permiso en la API."),
            404: ("not_found", "El recurso solicitado no existe o no es accesible."),
            409: ("conflict", "El recurso cambió; vuelve a consultarlo antes de actualizar."),
            422: ("validation_error", "La API rechazó los datos enviados."),
        }.get(response.status_code, ("upstream_error", "La API no pudo completar la operación."))
        raise _error(code, message, upstream_status=response.status_code)


class ToolAuditMiddleware(MCPMiddleware):
    def __init__(self, auth: MCPAuth):
        self.auth = auth

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        info = self.auth.auth_info
        client = (info.client_id or info.subject) if info else "unauthenticated"
        tool_name = getattr(context.message, "name", "unknown")
        result_name = "error"
        try:
            result = await call_next(context)
            result_name = "error" if getattr(result, "is_error", False) else "ok"
            return result
        finally:
            logger.info("mcp_tool client=%s tool=%s result=%s", client, tool_name, result_name)


def _auth_server(settings: Settings) -> AuthServerConfig:
    kind = AuthServerType.OIDC if settings.auth_type == "oidc" else AuthServerType.OAUTH
    return fetch_server_config(settings.issuer, kind)


def create_app(
    settings: Settings | None = None,
    *,
    authorization_server: AuthServerConfig | None = None,
    verify_access_token: VerifyAccessTokenFunction | None = None,
) -> Starlette:
    settings = settings or Settings.from_env()
    server_config = authorization_server or _auth_server(settings)
    auth = MCPAuth(
        protected_resources=ResourceServerConfig(
            metadata=ResourceServerMetadata(
                resource=settings.resource_url,
                resource_name="Brasaland Company Tools",
                authorization_servers=[server_config],
                scopes_supported=SCOPES,
                bearer_methods_supported=["header"],
            )
        )
    )
    verifier = verify_access_token or "jwt"
    bearer = auth.bearer_auth_middleware(
        verifier,
        audience=settings.resource_url,
        required_scopes=["mcp:access"],
        resource=settings.resource_url,
    )
    api = CompanyApi(settings.api_url, auth, settings.request_timeout)
    mcp = FastMCP(
        "Brasaland Company Tools",
        instructions=(
            "Herramientas OAuth para incidencias e inventario de Brasaland. "
            "El inventario es estrictamente de solo lectura."
        ),
        mask_error_details=True,
        middleware=[ToolAuditMiddleware(auth)],
    )

    @mcp.tool(
        name="get_incident",
        description=(
            "Consulta por ID un ticket del usuario autenticado. Requiere incidents:read; "
            "no revela tickets de otros usuarios."
        ),
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_incident(incident_id: Annotated[int, Field(gt=0, le=9007199254740991)]) -> Incident:
        api.require("incidents:read")
        return Incident.model_validate(await api.request("GET", f"/api/incidents/{incident_id}"))

    @mcp.tool(
        name="list_incidents",
        description=(
            "Lista tickets del usuario autenticado con filtros opcionales de estado y categoría. "
            "Requiere incidents:read."
        ),
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_incidents(
        status: Status | None = None,
        category: Category | None = None,
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> IncidentList:
        api.require("incidents:read")
        params = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if category is not None:
            params["category"] = category
        return IncidentList.model_validate(await api.request("GET", "/api/incidents", params=params))

    @mcp.tool(
        name="create_incident",
        description=(
            "Crea un ticket para el usuario autenticado. Requiere incidents:write. "
            "Categorías válidas: operations, technical y other."
        ),
        annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False),
    )
    async def create_incident(
        title: Annotated[str, Field(min_length=5, max_length=160)],
        description: Annotated[str, Field(min_length=10, max_length=4000)],
        category: Category,
    ) -> Incident:
        api.require("incidents:write")
        payload = {"title": title, "description": description, "category": category}
        return Incident.model_validate(await api.request("POST", "/api/incidents", json_body=payload))

    @mcp.tool(
        name="update_incident_status",
        description=(
            "Cambia el estado de un ticket mediante el endpoint de ciclo de vida "
            "PATCH /api/incidents/{id}/status. Requiere incidents:write y la versión actual."
        ),
        annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
    )
    async def update_incident_status(
        incident_id: Annotated[int, Field(gt=0, le=9007199254740991)],
        status: Status,
        expected_version: Annotated[int, Field(gt=0)],
    ) -> Incident:
        api.require("incidents:write")
        payload = {"status": status, "expected_version": expected_version}
        return Incident.model_validate(
            await api.request("PATCH", f"/api/incidents/{incident_id}/status", json_body=payload)
        )

    @mcp.tool(
        name="inventory_access",
        description=(
            "Consulta productos o historial de movimientos del inventario. Esta herramienta es "
            "estrictamente de solo lectura: operation='write' siempre devuelve inventory_read_only. "
            "Requiere inventory:read."
        ),
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def inventory_access(
        operation: Literal["read", "write"],
        resource: Literal["products", "orders"],
        country: Country | None = None,
        ingredient_id: Annotated[int | None, Field(gt=0, le=9007199254740991)] = None,
    ) -> InventoryResult:
        api.require("inventory:read")
        if operation == "write":
            raise _error(
                "inventory_read_only",
                "El servidor MCP no permite crear, editar ni borrar datos de inventario.",
            )
        if resource == "orders" and (country is not None or ingredient_id is not None):
            raise _error(
                "validation_error",
                "country e ingredient_id solo se admiten al consultar products.",
            )
        if resource == "products":
            path = f"/inventory/products/{ingredient_id}" if ingredient_id else "/inventory/products"
            payload = await api.request("GET", path, params={"country": country} if country else None)
            items = [payload] if ingredient_id else payload
        else:
            items = await api.request("GET", "/inventory/orders")
        return InventoryResult(resource=resource, items=items)

    mcp_app = mcp.http_app(
        path="/mcp",
        transport="streamable-http",
        stateless_http=True,
        json_response=True,
        middleware=[StarletteMiddleware(bearer)],
    )
    metadata_routes = list(auth.resource_metadata_router().routes)
    app = Starlette(routes=[*metadata_routes, Mount("/", app=mcp_app)], lifespan=mcp_app.lifespan)
    app.state.mcp = mcp
    app.state.mcp_auth = auth
    return app
