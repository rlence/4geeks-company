"""POST /auth/login — lógica de negocio: ¿a quién se le concede una sesión?"""

from auth import decode_access_token


def test_correct_credentials_return_a_token_for_the_right_user(client, existing_user):
    response = client.post(
        "/auth/login",
        json={"email": existing_user["email"], "password": existing_user["password"]},
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert decode_access_token(token) == existing_user["id"]


def test_empty_password_is_treated_as_invalid_credentials_not_a_crash(client, existing_user):
    response = client.post(
        "/auth/login", json={"email": existing_user["email"], "password": ""}
    )

    assert response.status_code == 401


def test_wrong_password_is_rejected(client, existing_user):
    response = client.post(
        "/auth/login",
        json={"email": existing_user["email"], "password": "not-the-password"},
    )

    assert response.status_code == 401


def test_nonexistent_email_gives_the_same_response_as_wrong_password(client, existing_user):
    # No debe ser posible distinguir "el email no existe" de "la password es
    # incorrecta" por status ni por mensaje: eso permitiría enumerar usuarios.
    wrong_password_response = client.post(
        "/auth/login",
        json={"email": existing_user["email"], "password": "not-the-password"},
    )
    unknown_email_response = client.post(
        "/auth/login",
        json={"email": "nobody@brasaland.com", "password": "whatever"},
    )

    assert unknown_email_response.status_code == wrong_password_response.status_code == 401
    assert unknown_email_response.json()["detail"] == wrong_password_response.json()["detail"]
