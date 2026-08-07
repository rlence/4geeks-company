from datetime import datetime, timedelta, timezone

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
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token de sesión inválido o expirado") from exc


def get_user_by_email(email: str) -> Document | None:
    return users_table.get(Query().email == email)


def get_current_user(authorization: str = Header(default="")) -> Document:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el header Authorization")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_access_token(token)

    user = users_table.get(doc_id=user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user
