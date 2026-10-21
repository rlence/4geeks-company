"""Persistencia de la orquestación nocturna; independiente de FastAPI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

REPO_ROOT = Path(__file__).resolve().parents[1]
JOB_NAME = "nightly_export"


@dataclass(frozen=True)
class Claim:
    outcome: str
    run_id: str | None


def get_client() -> Client:
    load_dotenv(REPO_ROOT / ".env")
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def has_processing_lock(client: Any) -> bool:
    return bool(
        client.table("job_runs").select("id").eq("job_name", JOB_NAME)
        .eq("status", "processing").limit(1).execute().data
    )


def has_completed_for_date(client: Any, target_date: date) -> bool:
    return bool(
        client.table("job_runs").select("id").eq("job_name", JOB_NAME)
        .eq("target_date", target_date.isoformat()).eq("status", "completed")
        .limit(1).execute().data
    )


def claim_run(client: Any, target_date: date, stale_after_seconds: int = 7200) -> Claim:
    data = client.rpc("claim_nightly_job", {
        "p_job_name": JOB_NAME,
        "p_target_date": target_date.isoformat(),
        "p_stale_after_seconds": stale_after_seconds,
    }).execute().data
    if not isinstance(data, list) or len(data) != 1:
        raise RuntimeError("claim_nightly_job returned an invalid result")
    outcome, run_id = data[0].get("outcome"), data[0].get("run_id")
    if outcome not in {"claimed", "already_processing", "already_completed"}:
        raise RuntimeError("claim_nightly_job returned an unknown outcome")
    if (outcome == "claimed") != bool(run_id):
        raise RuntimeError("claim_nightly_job returned an inconsistent run id")
    return Claim(outcome, run_id)


def heartbeat_run(client: Any, run_id: str) -> None:
    if client.rpc("heartbeat_nightly_job", {"p_run_id": run_id}).execute().data is not True:
        raise RuntimeError("nightly job lost its processing reservation")


def finish_run(client: Any, run_id: str, status: str, error_message: str | None = None) -> None:
    if status not in {"completed", "failed"}:
        raise ValueError("invalid final status")
    if client.rpc("finish_nightly_job", {
        "p_run_id": run_id,
        "p_status": status,
        "p_error_message": error_message,
    }).execute().data is not True:
        raise RuntimeError("nightly job could not finalize its processing reservation")
