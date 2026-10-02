import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from mcpauth.config import AuthServerConfig, AuthServerType, AuthorizationServerMetadata
from mcpauth.types import AuthInfo
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcps.brasaland_company.config import Settings  # noqa: E402
from mcps.brasaland_company import server  # noqa: E402

RESOURCE = "http://testserver/mcp"
ISSUER = "https://issuer.test"
INCIDENT = {
    "id": 482,
    "title": "Ticket de prueba",
    "description": "Descripción suficientemente larga",
    "category": "technical",
    "status": "open",
    "origin": "api",
    "created_by": "7",
    "created_at": "2026-09-30T10:00:00Z",
    "updated_at": "2026-09-30T10:00:00Z",
    "resolved_at": None,
    "version": 1,
}


def _verify(token):
    scopes = {
        "read": ["mcp:access", "incidents:read", "inventory:read"],
        "all": ["mcp:access", "incidents:read", "incidents:write", "inventory:read"],
    }.get(token, [])
    return AuthInfo(
        token=token,
        issuer=ISSUER,
        client_id="test-client",
        subject="7",
        audience=RESOURCE,
        scopes=scopes,
        claims={},
    )


@pytest.fixture
def mcp_client(monkeypatch):
    calls = []

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path == "/api/incidents":
                payload = {"items": [INCIDENT], "total": 1, "limit": 20, "offset": 0}
            elif path.startswith("/api/incidents/"):
                payload = {**INCIDENT, "status": kwargs.get("json", {}).get("status", "open")}
            elif path == "/inventory/products":
                payload = [{"id": 1, "name": "Carne", "sku": "CARNE", "unit": "kg", "category": "meat", "country": "CO", "current_stock": 8.5}]
            else:
                payload = []
            return httpx.Response(200, json=payload, request=httpx.Request(method, "http://api.test" + path))

    monkeypatch.setattr(server.httpx, "AsyncClient", FakeAsyncClient)
    auth_server = AuthServerConfig(
        type=AuthServerType.OIDC,
        metadata=AuthorizationServerMetadata(
            issuer=ISSUER,
            authorization_endpoint=ISSUER + "/authorize",
            token_endpoint=ISSUER + "/token",
            jwks_uri=ISSUER + "/jwks",
            response_types_supported=["code"],
        ),
    )
    app = server.create_app(
        Settings(resource_url=RESOURCE, issuer=ISSUER, api_url="http://api.test"),
        authorization_server=auth_server,
        verify_access_token=_verify,
    )
    with TestClient(app) as client:
        yield client, calls


def _rpc(client, method, params=None, token="all", request_id=1):
    return client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"},
    )


def test_metadata_and_tool_discovery_are_protected_and_descriptive(mcp_client):
    client, _ = mcp_client
    metadata = client.get("/.well-known/oauth-protected-resource/mcp")
    assert metadata.status_code == 200
    assert metadata.json()["scopes_supported"] == server.SCOPES
    assert client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).status_code == 401
    response = _rpc(client, "tools/list")
    tools = {item["name"]: item for item in response.json()["result"]["tools"]}
    assert set(tools) == {"get_incident", "list_incidents", "create_incident", "update_incident_status", "inventory_access"}
    assert tools["inventory_access"]["description"]
    assert tools["inventory_access"]["inputSchema"]["properties"]["operation"]["enum"] == ["read", "write"]


def test_mcpauth_verifies_signature_issuer_audience_and_base_scope(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class JwksClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr("mcpauth.utils._create_verify_jwt.PyJWKClient", JwksClient)
    auth_server = AuthServerConfig(
        type=AuthServerType.OIDC,
        metadata=AuthorizationServerMetadata(
            issuer=ISSUER,
            authorization_endpoint=ISSUER + "/authorize",
            token_endpoint=ISSUER + "/token",
            jwks_uri=ISSUER + "/jwks",
            response_types_supported=["code"],
        ),
    )
    app = server.create_app(
        Settings(resource_url=RESOURCE, issuer=ISSUER, api_url="http://api.test"),
        authorization_server=auth_server,
    )
    now = datetime.now(timezone.utc)
    claims = {
        "iss": ISSUER,
        "aud": RESOURCE,
        "sub": "7",
        "client_id": "signed-client",
        "scope": "mcp:access incidents:read",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test"})
    bad_audience = jwt.encode({**claims, "aud": "https://other.test/mcp"}, private_key, algorithm="RS256")
    with TestClient(app) as client:
        assert _rpc(client, "tools/list", token=token).status_code == 200
        denied = _rpc(client, "tools/list", token=bad_audience)
        assert denied.status_code == 401
        assert denied.json()["error"] == "invalid_audience"


def test_valid_token_without_base_scope_cannot_list_tools(mcp_client):
    client, _ = mcp_client
    response = _rpc(client, "tools/list", token="without-scopes")
    assert response.status_code == 403
    assert response.json()["error"] == "missing_required_scopes"


def test_status_update_uses_lifecycle_endpoint_and_forwards_token(mcp_client):
    client, calls = mcp_client
    response = _rpc(
        client,
        "tools/call",
        {"name": "update_incident_status", "arguments": {"incident_id": 482, "status": "resolved", "expected_version": 1}},
    )
    assert response.status_code == 200 and not response.json()["result"]["isError"]
    method, path, kwargs = calls[-1]
    assert (method, path) == ("PATCH", "/api/incidents/482/status")
    assert kwargs["headers"] == {"Authorization": "Bearer all"}


def test_scopes_and_inventory_write_are_explicitly_rejected(mcp_client):
    client, calls = mcp_client
    denied = _rpc(
        client,
        "tools/call",
        {"name": "create_incident", "arguments": {"title": "Fallo técnico", "description": "Descripción suficientemente larga", "category": "technical"}},
        token="read",
    )
    assert denied.json()["result"]["isError"]
    assert "insufficient_scope" in denied.text
    before = len(calls)
    readonly = _rpc(
        client,
        "tools/call",
        {"name": "inventory_access", "arguments": {"operation": "write", "resource": "products"}},
        token="read",
    )
    assert readonly.json()["result"]["isError"]
    assert "inventory_read_only" in readonly.text
    assert len(calls) == before


def test_inventory_read_calls_real_api_contract(mcp_client, caplog):
    client, calls = mcp_client
    caplog.set_level("INFO", logger="brasaland.mcp")
    response = _rpc(
        client,
        "tools/call",
        {"name": "inventory_access", "arguments": {"operation": "read", "resource": "products", "country": "CO"}},
        token="read",
    )
    assert response.status_code == 200 and not response.json()["result"]["isError"]
    assert calls[-1][0:2] == ("GET", "/inventory/products")
    assert calls[-1][2]["params"] == {"country": "CO"}
    assert "client=test-client tool=inventory_access result=ok" in caplog.text
