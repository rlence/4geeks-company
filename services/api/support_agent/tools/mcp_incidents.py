"""Cliente MCP del agente; no importa repositorios ni servicios de incidencias."""

import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import os
from uuid import uuid4

from langchain_mcp_adapters.client import MultiServerMCPClient

current_access_token = ContextVar("mcp_access_token", default=None)
TIMEOUT_SECONDS = 10.0


def _normalize(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    if isinstance(value, list):
        texts = [block.get("text") for block in value if isinstance(block, dict) and isinstance(block.get("text"), str)]
        if len(texts) == 1:
            return _normalize(texts[0])
    return None


async def invoke_tool(name: str, arguments: dict, token: str):
    url = os.environ.get("MCP_URL")
    if not url:
        raise RuntimeError("MCP_URL no configurada")
    client = MultiServerMCPClient(
        {
            "brasaland": {
                "transport": "streamable_http",
                "url": url,
                "headers": {"Authorization": f"Bearer {token}"},
                "timeout": TIMEOUT_SECONDS,
                "sse_read_timeout": TIMEOUT_SECONDS,
            }
        },
        handle_tool_errors=False,
    )
    tools = {tool.name: tool for tool in await client.get_tools(server_name="brasaland")}
    if name not in tools:
        raise RuntimeError(f"Tool MCP no disponible: {name}")
    message = await tools[name].ainvoke(
        {"name": name, "args": arguments, "id": str(uuid4()), "type": "tool_call"}
    )
    artifact = getattr(message, "artifact", None)
    if isinstance(artifact, dict) and isinstance(artifact.get("structured_content"), dict):
        return artifact["structured_content"]
    return getattr(message, "content", message)


async def read_incidents(decision, access_token):
    if not access_token:
        return {"status": "unauthorized", "items": []}
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            if decision.ticket_id:
                raw = await invoke_tool("get_incident", {"incident_id": decision.ticket_id}, access_token)
                item = _normalize(raw)
                if not item:
                    return {"status": "invalid_response", "items": []}
                items, total = [item], 1
            else:
                arguments = {"limit": 10, "offset": 0}
                if decision.status:
                    arguments["status"] = decision.status
                if decision.category:
                    arguments["category"] = decision.category
                result = _normalize(await invoke_tool("list_incidents", arguments, access_token))
                if not result or not isinstance(result.get("items"), list):
                    return {"status": "invalid_response", "items": []}
                items, total = result["items"], result.get("total", len(result["items"]))
            fields = {"id", "status", "category", "origin", "updated_at", "resolved_at"}
            safe_items = [{key: value for key, value in item.items() if key in fields} for item in items]
            return {
                "status": "ok",
                "items": safe_items,
                "total": total,
                "queried_at": datetime.now(timezone.utc).isoformat(),
            }
    except (TimeoutError, asyncio.TimeoutError):
        return {"status": "timeout", "items": []}
    except Exception as exc:
        message = str(exc)
        if "not_found" in message:
            return {"status": "not_found", "items": []}
        if "authentication" in message or "401" in message:
            return {"status": "unauthorized", "items": []}
        return {"status": "unavailable", "items": []}


def lookup(decision):
    return asyncio.run(read_incidents(decision, current_access_token.get()))


def format_result(result):
    if result["status"] != "ok":
        return {
            "not_found": "No encontré ese ticket entre tus incidencias accesibles.",
            "unauthorized": "Necesitas iniciar sesión con OAuth para consultar tus incidencias.",
        }.get(result["status"], "No pude confirmar el estado de las incidencias ahora mismo. Inténtalo de nuevo.")
    if not result["items"]:
        return "No encontré incidencias tuyas con esos filtros."
    names = {"open": "abierto", "in_progress": "en progreso", "resolved": "resuelto"}
    lines = [
        f"Ticket {item['id']}: {names[item['status']]}. Categoría: {item['category']}. "
        f"Actualizado: {item['updated_at']}."
        for item in result["items"]
    ]
    if result["total"] > len(result["items"]):
        lines.append(f"Se muestran {len(result['items'])} de {result['total']} resultados. Acota los filtros en el gestor.")
    return "\n".join(lines)
