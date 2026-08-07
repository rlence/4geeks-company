import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from tinydb import Query

import config
from auth import (
    create_access_token,
    get_current_user,
    get_user_by_email,
    hash_password,
    verify_password,
)
from database import password_reset_tokens_table, users_table
from mail import send_password_reset_email
from models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    token = create_access_token(user.doc_id)
    return TokenResponse(access_token=token)


@router.post("/forgot-password", status_code=200)
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    user = get_user_by_email(payload.email)

    if user is not None:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=config.RESET_TOKEN_TTL_MINUTES
        )
        password_reset_tokens_table.insert(
            {
                "token_hash": _hash_token(token),
                "user_id": user.doc_id,
                "expires_at": expires_at.isoformat(),
                "used": False,
            }
        )
        reset_url = f"{config.FRONTEND_URL}/reset-password?token={token}"
        try:
            send_password_reset_email(payload.email, reset_url)
        except Exception:
            logger.exception("Fallo enviando el email de restablecimiento a %s", payload.email)

    return {}


@router.post("/reset-password", status_code=200)
def reset_password(payload: ResetPasswordRequest) -> dict:
    token_hash = _hash_token(payload.token)
    query = Query()
    record = password_reset_tokens_table.get(
        (query.token_hash == token_hash) & (query.used == False)  # noqa: E712
    )

    if record is None:
        raise HTTPException(status_code=400, detail="Token inválido o ya utilizado")

    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expirado")

    users_table.update(
        {"hashed_password": hash_password(payload.new_password)},
        doc_ids=[record["user_id"]],
    )
    password_reset_tokens_table.update({"used": True}, doc_ids=[record.doc_id])

    return {}


@router.post("/change-password", status_code=200)
def change_password(
    payload: ChangePasswordRequest, current_user=Depends(get_current_user)
) -> dict:
    if not verify_password(payload.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")

    users_table.update(
        {"hashed_password": hash_password(payload.new_password)},
        doc_ids=[current_user.doc_id],
    )
    return {}
