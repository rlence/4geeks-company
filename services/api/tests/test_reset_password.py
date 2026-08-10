"""POST /auth/reset-password — lógica de negocio de canje de un token de reset."""

import hashlib
from datetime import datetime, timedelta, timezone

from auth import verify_password
from database import password_reset_tokens_table, users_table


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _insert_reset_token(user_id: int, *, token: str, expires_in_minutes: int, used: bool = False) -> int:
    return password_reset_tokens_table.insert(
        {
            "token_hash": _hash_token(token),
            "user_id": user_id,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
            ).isoformat(),
            "used": used,
        }
    )


def test_valid_token_changes_the_password_and_marks_the_token_used(client, existing_user):
    token = "valid-reset-token"
    record_id = _insert_reset_token(existing_user["id"], token=token, expires_in_minutes=30)

    response = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "brand-new-password"}
    )

    assert response.status_code == 200
    updated_user = users_table.get(doc_id=existing_user["id"])
    assert verify_password("brand-new-password", updated_user["hashed_password"]) is True
    assert verify_password(existing_user["password"], updated_user["hashed_password"]) is False
    assert password_reset_tokens_table.get(doc_id=record_id)["used"] is True


def test_reusing_an_already_used_token_is_rejected(client, existing_user):
    token = "one-time-token"
    _insert_reset_token(existing_user["id"], token=token, expires_in_minutes=30, used=True)

    response = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "another-password"}
    )

    assert response.status_code == 400


def test_expired_token_is_rejected(client, existing_user):
    token = "expired-token"
    _insert_reset_token(existing_user["id"], token=token, expires_in_minutes=-1)

    response = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "another-password"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Token expirado"


def test_unknown_token_is_rejected(client):
    response = client.post(
        "/auth/reset-password",
        json={"token": "this-token-was-never-issued", "new_password": "another-password"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Token inválido o ya utilizado"
