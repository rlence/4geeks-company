"""Configuración explícita; no contiene secretos ni valores de entorno reales."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    resource_url: str
    issuer: str
    api_url: str
    auth_type: str = "oidc"
    host: str = "0.0.0.0"
    port: int = 8010
    request_timeout: float = 8.0

    @classmethod
    def from_env(cls) -> "Settings":
        required = {
            "resource_url": os.environ.get("MCP_RESOURCE_URL"),
            "issuer": os.environ.get("MCP_AUTH_ISSUER"),
            "api_url": os.environ.get("COMPANY_API_URL"),
        }
        missing = [name.upper() for name, value in required.items() if not value]
        if missing:
            raise RuntimeError("Faltan variables MCP obligatorias: " + ", ".join(missing))
        auth_type = os.environ.get("MCP_AUTH_TYPE", "oidc").lower()
        if auth_type not in {"oidc", "oauth"}:
            raise RuntimeError("MCP_AUTH_TYPE debe ser 'oidc' u 'oauth'")
        return cls(
            **required,
            auth_type=auth_type,
            host=os.environ.get("MCP_HOST", "0.0.0.0"),
            port=int(os.environ.get("MCP_PORT", "8010")),
            request_timeout=float(os.environ.get("MCP_REQUEST_TIMEOUT", "8")),
        )
