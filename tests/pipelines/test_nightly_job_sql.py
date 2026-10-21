"""Prueba del lock real: usar solo una base PostgreSQL local y desechable.

Antes de correrla, aplicar services/api/sql/job_runs.sql y fijar
NIGHTLY_TEST_POSTGRES_DSN con un socket Unix temporal. Esta suite trunca
job_runs deliberadamente; nunca apuntarla a Supabase compartido.
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from services import job_runner  # noqa: E402


@pytest.fixture
def dsn():
    value = os.environ.get("NIGHTLY_TEST_POSTGRES_DSN")
    if not value:
        pytest.skip("NIGHTLY_TEST_POSTGRES_DSN no configurado")
    if "host=/private/tmp/" not in value and "host=/tmp/" not in value:
        pytest.fail("la prueba destructiva requiere un socket PostgreSQL temporal local")
    with psycopg.connect(value) as conn:
        conn.execute("truncate public.job_runs")
    yield value
    with psycopg.connect(value) as conn:
        conn.execute("truncate public.job_runs")


def claim(dsn, target_date, barrier=None):
    with psycopg.connect(dsn) as conn:
        if barrier:
            barrier.wait()
        return conn.execute(
            "select outcome, run_id from public.claim_nightly_job(%s, %s, %s)",
            ("nightly_export", target_date, 60),
        ).fetchone()


def test_only_one_of_two_processes_can_claim_and_duplicate_stays_skipped(dsn):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(dsn, "2026-10-20", barrier), range(2)))
    assert sorted(result[0] for result in results) == ["already_processing", "claimed"]
    with psycopg.connect(dsn) as conn:
        assert conn.execute("select count(*) from public.job_runs").fetchone()[0] == 1
    run_id = next(run_id for outcome, run_id in results if outcome == "claimed")
    assert claim(dsn, "2026-10-21")[0] == "already_processing"
    with psycopg.connect(dsn) as conn:
        assert conn.execute(
            "select public.finish_nightly_job(%s, 'completed', null)", (run_id,)
        ).fetchone()[0]
    assert claim(dsn, "2026-10-20")[0] == "already_completed"
    assert claim(dsn, "2026-10-21")[0] == "claimed"


def test_stale_processing_is_failed_before_next_claim(dsn):
    outcome, run_id = claim(dsn, "2026-10-20")
    assert outcome == "claimed"
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "update public.job_runs set heartbeat_at = now() - interval '2 hours' where id = %s",
            (run_id,),
        )
    assert claim(dsn, "2026-10-21")[0] == "claimed"
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "select status, error_message from public.job_runs where id = %s", (run_id,)
        ).fetchone()
    assert row == ("failed", "stale_run_recovered")


def test_completed_day_cannot_be_reserved_again_even_with_pending_row(dsn):
    outcome, run_id = claim(dsn, "2026-10-20")
    assert outcome == "claimed"
    with psycopg.connect(dsn) as conn:
        assert conn.execute(
            "select public.finish_nightly_job(%s, 'completed', null)", (run_id,)
        ).fetchone()[0]
        pending_id = conn.execute(
            "insert into public.job_runs (job_name, target_date, status) "
            "values ('nightly_export', '2026-10-20', 'pending') returning id"
        ).fetchone()[0]
    with psycopg.connect(dsn) as conn:
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "update public.job_runs set status = 'processing' where id = %s", (pending_id,)
            )
        conn.rollback()


def test_anonymous_role_cannot_read_or_claim(dsn):
    with psycopg.connect(dsn) as conn:
        conn.execute("set role anon")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select * from public.job_runs")
        conn.rollback()
    with psycopg.connect(dsn) as conn:
        conn.execute("set role anon")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "select * from public.claim_nightly_job('nightly_export', '2026-10-20', 60)"
            )
        conn.rollback()


def test_python_rpc_contract_and_service_role_permissions(dsn):
    class RpcClient:
        def rpc(self, name, params):
            with psycopg.connect(dsn) as conn:
                conn.execute("set role service_role")
                if name == "claim_nightly_job":
                    outcome, run_id = conn.execute(
                        "select outcome, run_id from public.claim_nightly_job(%s,%s,%s)",
                        (params["p_job_name"], params["p_target_date"],
                         params["p_stale_after_seconds"]),
                    ).fetchone()
                    data = [{"outcome": outcome, "run_id": str(run_id) if run_id else None}]
                elif name == "heartbeat_nightly_job":
                    data = conn.execute(
                        "select public.heartbeat_nightly_job(%s)", (params["p_run_id"],)
                    ).fetchone()[0]
                else:
                    data = conn.execute(
                        "select public.finish_nightly_job(%s,%s,%s)",
                        (params["p_run_id"], params["p_status"], params["p_error_message"]),
                    ).fetchone()[0]
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))

    client = RpcClient()
    target = date(2026, 10, 20)
    reserved = job_runner.claim_run(client, target)
    assert reserved.outcome == "claimed"
    job_runner.heartbeat_run(client, reserved.run_id)
    job_runner.finish_run(client, reserved.run_id, "completed")
    assert job_runner.claim_run(client, target).outcome == "already_completed"
