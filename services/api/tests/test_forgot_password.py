"""
POST /auth/forgot-password — lógica de negocio: se crea (o no) un token de
reset, y la respuesta al cliente nunca delata si el email existe.

`send_password_reset_email` habla con Resend por HTTP real (mail.py). Se
mockea el nombre importado en routes.auth (no en mail), porque `from mail
import send_password_reset_email` ya vinculó el nombre localmente ahí.
"""

from datetime import datetime, timezone

from tinydb import Query

from database import password_reset_tokens_table


def test_existing_email_creates_a_reset_token_for_that_user(client, existing_user, monkeypatch):
    monkeypatch.setattr("routes.auth.send_password_reset_email", lambda *a, **kw: None)

    response = client.post(
        "/auth/forgot-password", json={"email": existing_user["email"]}
    )

    assert response.status_code == 200
    assert response.json() == {}
    record = password_reset_tokens_table.get(Query().user_id == existing_user["id"])
    assert record is not None
    assert record["used"] is False
    expires_at = datetime.fromisoformat(record["expires_at"])
    assert expires_at > datetime.now(timezone.utc)


def test_nonexistent_email_gives_the_same_generic_response_and_creates_no_token(
    client, monkeypatch
):
    send_email = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("no debería enviarse email"))
    monkeypatch.setattr("routes.auth.send_password_reset_email", send_email)

    response = client.post(
        "/auth/forgot-password", json={"email": "nobody@brasaland.com"}
    )

    assert response.status_code == 200
    assert response.json() == {}
    assert len(password_reset_tokens_table) == 0


def test_token_is_still_created_even_if_sending_the_email_fails(
    client, existing_user, monkeypatch
):
    def _raise(*args, **kwargs):
        raise RuntimeError("Resend está caído")

    monkeypatch.setattr("routes.auth.send_password_reset_email", _raise)

    response = client.post(
        "/auth/forgot-password", json={"email": existing_user["email"]}
    )

    # Falla silenciosa por diseño: el endpoint igual responde 200 y el token
    # de reset queda creado, aunque el email nunca haya salido.
    assert response.status_code == 200
    record = password_reset_tokens_table.get(Query().user_id == existing_user["id"])
    assert record is not None
