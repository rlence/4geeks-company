from datetime import datetime, timedelta, timezone
from functools import lru_cache
import os

import bcrypt
import jwt
from fastapi import Header, HTTPException
from tinydb import Query
from tinydb.table import Document

import config
from database import users_table


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token de sesión inválido o expirado") from exc


@lru_cache(maxsize=4)
def _oidc_jwks_client(jwks_uri: str):
    return jwt.PyJWKClient(jwks_uri)


def _external_identity(token: str) -> Document | None:
    """Valida tokens OAuth externos antes de mapearlos a un usuario local."""
    issuer = os.environ.get("MCP_AUTH_ISSUER")
    audience = os.environ.get("MCP_RESOURCE_URL")
    jwks_uri = os.environ.get("MCP_AUTH_JWKS_URI")
    if not all((issuer, audience, jwks_uri)):
        return None
    try:
        key = _oidc_jwks_client(jwks_uri).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256", "PS256", "ES256", "ES384", "ES512"],
            audience=audience,
            issuer=issuer,
        )
    except jwt.PyJWTError:
        return None

    app_user_id = claims.get("app_user_id")
    subject = claims.get("sub")
    candidate = app_user_id if isinstance(app_user_id, int) else subject
    if isinstance(candidate, str) and candidate.isdecimal():
        return users_table.get(doc_id=int(candidate))
    email = claims.get("email")
    return get_user_by_email(email) if isinstance(email, str) else None


def get_user_by_email(email: str) -> Document | None:
    return users_table.get(Query().email == email)


def get_current_user(authorization: str = Header(default="")) -> Document:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el header Authorization")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        user_id = decode_access_token(token)
        user = users_table.get(doc_id=user_id)
    except HTTPException:
        user = _external_identity(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Token de sesión u OAuth inválido o expirado")
    return user
