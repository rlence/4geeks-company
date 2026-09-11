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
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key-not-for-prod")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from auth import hash_password  # noqa: E402
from database import password_reset_tokens_table, suppliers_table, users_table  # noqa: E402
from main import app  # noqa: E402
from supabase_client import get_supabase_client  # noqa: E402


class FakeSupabaseTable:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._pending: list[dict] | None = None

    def upsert(
        self, rows: list[dict], on_conflict: str | None = None, ignore_duplicates: bool = False
    ) -> "FakeSupabaseTable":
        self._pending = rows
        return self

    def execute(self) -> None:
        assert self._pending is not None
        existing_ids = {row["event_id"] for row in self._rows}
        for row in self._pending:
            if row["event_id"] not in existing_ids:
                self._rows.append(row)
                existing_ids.add(row["event_id"])
        self._pending = None


class FakeSupabaseClient:
    """Sustituye al cliente supabase-py real en tests: sin red, solo
    acumula en memoria lo que el endpoint intentaría persistir (con la
    misma semántica ON CONFLICT (event_id) DO NOTHING del upsert real)."""

    def __init__(self) -> None:
        self.inserted_rows: list[dict] = []
        self.upsert_calls: list[list[dict]] = []

    def table(self, name: str) -> FakeSupabaseTable:
        assert name == "telemetry_events"
        table = FakeSupabaseTable(self.inserted_rows)
        original_upsert = table.upsert

        def tracked_upsert(rows: list[dict], **kwargs) -> FakeSupabaseTable:
            self.upsert_calls.append(rows)
            return original_upsert(rows, **kwargs)

        table.upsert = tracked_upsert  # type: ignore[method-assign]
        return table


@pytest.fixture
def fake_supabase() -> FakeSupabaseClient:
    fake = FakeSupabaseClient()
    app.dependency_overrides[get_supabase_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_supabase_client, None)


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
