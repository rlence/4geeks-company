"""POST /auth/change-password — lógica de negocio del cambio autenticado de password."""

from auth import verify_password
from database import users_table


def test_correct_current_password_updates_the_hash(client, existing_user, auth_headers):
    response = client.post(
        "/auth/change-password",
        json={
            "current_password": existing_user["password"],
            "new_password": "a-brand-new-password",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    updated_user = users_table.get(doc_id=existing_user["id"])
    assert verify_password("a-brand-new-password", updated_user["hashed_password"]) is True
    assert verify_password(existing_user["password"], updated_user["hashed_password"]) is False


def test_reusing_the_same_password_is_currently_allowed(client, existing_user, auth_headers):
    # Hallazgo de IA (ver TESTING.md): no hay validación que impida que
    # new_password == current_password. Se documenta el comportamiento actual,
    # no se "arregla" silenciosamente — es una decisión de producto pendiente.
    response = client.post(
        "/auth/change-password",
        json={
            "current_password": existing_user["password"],
            "new_password": existing_user["password"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200


def test_wrong_current_password_is_rejected(client, existing_user, auth_headers):
    response = client.post(
        "/auth/change-password",
        json={"current_password": "not-the-real-password", "new_password": "whatever12345"},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_missing_authorization_header_is_rejected(client, existing_user):
    response = client.post(
        "/auth/change-password",
        json={
            "current_password": existing_user["password"],
            "new_password": "whatever12345",
        },
    )

    assert response.status_code == 401


def test_malformed_authorization_header_is_rejected(client, existing_user):
    response = client.post(
        "/auth/change-password",
        json={
            "current_password": existing_user["password"],
            "new_password": "whatever12345",
        },
        headers={"Authorization": "not-a-bearer-token"},
    )

    assert response.status_code == 401
