# Brasaland Company Tools MCP

Servidor MCP remoto mediante **Streamable HTTP**. Usa MCP Auth como resource server OAuth 2.1/OIDC; FastMCP solo publica el protocolo y las herramientas.

## Configuración

El proveedor debe publicar metadata OIDC/OAuth, JWKS y access tokens JWT cuyo `iss` coincida con `MCP_AUTH_ISSUER` y cuyo `aud` sea exactamente `MCP_RESOURCE_URL`.

```dotenv
MCP_RESOURCE_URL=https://<codespace>-8010.app.github.dev/mcp
MCP_AUTH_ISSUER=https://<proveedor>/oidc
MCP_AUTH_TYPE=oidc
MCP_AUTH_JWKS_URI=https://<proveedor>/.well-known/jwks.json
COMPANY_API_URL=http://127.0.0.1:8000
MCP_URL=http://127.0.0.1:8010/mcp
MCP_PORT=8010
```

Scopes publicados y aplicados por herramienta:

- `mcp:access`: acceso base obligatorio para discovery e invocación.
- `incidents:read`: `get_incident`, `list_incidents`.
- `incidents:write`: `create_incident`, `update_incident_status`.
- `inventory:read`: `inventory_access`. `operation=write` se rechaza siempre con `inventory_read_only`.

La API vuelve a validar el mismo access token. El usuario se resuelve con el claim numérico `app_user_id`, con un `sub` numérico o con el claim `email` de un usuario ya existente.

## Ejecución

Desde la raíz del monorepo:

```bash
uv run --project services/api python -m mcps.brasaland_company
```

El endpoint MCP es `/mcp` y la metadata RFC 9728 se publica en `/.well-known/oauth-protected-resource/mcp`. Para MCP Playground, reenvía el puerto 8010 en Codespaces con visibilidad pública y usa la URL pública completa terminada en `/mcp`.

## Errores estables

- `authentication_required` / HTTP 401: falta un token válido.
- `insufficient_scope` / HTTP 403: faltan scopes.
- `validation_error`: argumentos inválidos.
- `inventory_read_only`: escritura de inventario bloqueada por diseño.
- `not_found`, `conflict`, `upstream_timeout`, `upstream_unavailable`: fallo concreto de la API de negocio.
