"""
Lógica pura de auth.py (hashing, JWT, resolución de usuario autenticado),
sin pasar por HTTP. Complementa a los tests de routes/auth.py, que cubren
el comportamiento a nivel de endpoint.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from freezegun import freeze_time

import config
from auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database import users_table


class TestHashPassword:
    def test_verify_password_accepts_the_original_password(self):
        hashed = hash_password("brasaland2026")
        assert verify_password("brasaland2026", hashed) is True

    def test_hash_is_salted_so_two_hashes_of_the_same_password_differ(self):
        assert hash_password("brasaland2026") != hash_password("brasaland2026")

    def test_verify_password_rejects_the_wrong_password(self):
        hashed = hash_password("brasaland2026")
        assert verify_password("wrong-password", hashed) is False

    def test_verify_password_handles_unicode_passwords(self):
        password = "ñoño-contraseña-con-acentos-áéíóú"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_password_longer_than_72_bytes_raises_value_error(self):
        # Hallazgo de IA (ver TESTING.md): bcrypt trunca/rechaza a partir de 72
        # bytes. hash_password no lo maneja, así que hoy un password muy largo
        # revienta con un ValueError sin controlar en vez de un 422 legible.
        password = "x" * 100
        with pytest.raises(ValueError):
            hash_password(password)


class TestAccessToken:
    def test_create_and_decode_round_trip_returns_the_same_user_id(self):
        token = create_access_token(user_id=42)
        assert decode_access_token(token) == 42

    def test_token_still_valid_one_second_before_expiry(self):
        with freeze_time("2026-01-01 00:00:00"):
            token = create_access_token(user_id=7)
            just_before_expiry = datetime.now(timezone.utc) + timedelta(
                minutes=config.ACCESS_TOKEN_TTL_MINUTES, seconds=-1
            )
        with freeze_time(just_before_expiry):
            assert decode_access_token(token) == 7

    def test_token_is_rejected_one_second_after_expiry(self):
        with freeze_time("2026-01-01 00:00:00"):
            token = create_access_token(user_id=7)
            after_expiry = datetime.now(timezone.utc) + timedelta(
                minutes=config.ACCESS_TOKEN_TTL_MINUTES, seconds=1
            )
        with freeze_time(after_expiry):
            with pytest.raises(HTTPException) as exc_info:
                decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_token_signed_with_a_different_secret_is_rejected(self):
        bad_token = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            "not-the-real-secret",
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(bad_token)
        assert exc_info.value.status_code == 401

    def test_malformed_token_is_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("this-is-not-a-jwt")
        assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    def test_valid_bearer_token_returns_the_matching_user(self):
        user_id = users_table.insert(
            {"email": "a@brasaland.com", "hashed_password": hash_password("x")}
        )
        token = create_access_token(user_id)

        user = get_current_user(authorization=f"Bearer {token}")

        assert user.doc_id == user_id
        assert user["email"] == "a@brasaland.com"

    def test_extra_whitespace_after_the_bearer_prefix_is_tolerated(self):
        user_id = users_table.insert(
            {"email": "b@brasaland.com", "hashed_password": hash_password("x")}
        )
        token = create_access_token(user_id)

        user = get_current_user(authorization=f"Bearer  {token}")

        assert user.doc_id == user_id

    def test_missing_authorization_header_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization="")
        assert exc_info.value.status_code == 401

    def test_valid_token_for_a_deleted_user_raises_401(self):
        user_id = users_table.insert(
            {"email": "c@brasaland.com", "hashed_password": hash_password("x")}
        )
        token = create_access_token(user_id)
        users_table.remove(doc_ids=[user_id])

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=f"Bearer {token}")
        assert exc_info.value.status_code == 401
