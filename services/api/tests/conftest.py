"""
Fixtures compartidas. El bloque de arriba de todo (antes de cualquier import
de la app) fija DB_PATH a un archivo temporal y valores dummy de secretos,
para que los tests nunca toquen db.json ni dependan de .env real.
"""

import os
import shutil
import tempfile
from pathlib import Path

_TEST_DB_DIR = tempfile.mkdtemp(prefix="brasaland_test_db_")
os.environ["DB_PATH"] = str(Path(_TEST_DB_DIR) / "test_db.json")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-prod-32-bytes-min")
os.environ.setdefault("RESEND_API_KEY", "test-resend-key-not-for-prod")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from auth import hash_password  # noqa: E402
from database import password_reset_tokens_table, suppliers_table, users_table  # noqa: E402
from main import app  # noqa: E402


def pytest_sessionfinish(session, exitstatus) -> None:
    shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_tables():
    users_table.truncate()
    suppliers_table.truncate()
    password_reset_tokens_table.truncate()
    yield
    users_table.truncate()
    suppliers_table.truncate()
    password_reset_tokens_table.truncate()


@pytest.fixture
def existing_user() -> dict:
    """Inserta un usuario conocido y devuelve sus credenciales en texto plano."""
    email = "test.user@brasaland.com"
    password = "correct-horse-battery"
    user_id = users_table.insert(
        {"email": email, "hashed_password": hash_password(password)}
    )
    return {"id": user_id, "email": email, "password": password}


@pytest.fixture
def auth_headers(client: TestClient, existing_user: dict) -> dict:
    """Header Authorization válido para existing_user, vía el propio endpoint de login."""
    response = client.post(
        "/auth/login",
        json={"email": existing_user["email"], "password": existing_user["password"]},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
