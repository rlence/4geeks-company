"""Exportación nocturna y ejecución aislada del pipeline de Brasaland.

Ejecutar con el Python del venv de services/api, desde cualquier cwd:
    services/api/.venv/bin/python scripts/nightly_export.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, time as clock_time, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from services.job_runner import claim_run, finish_run, get_client, heartbeat_run  # noqa: E402

JOB_NAME = "nightly_export"
CSV_COLUMNS = (
    "event_id", "timestamp", "session_id", "user_id", "event_type",
    "schema_version", "request_id", "tags",
)
PAGE_SIZE = 500
HEARTBEAT_SECONDS = 30
STALE_AFTER_SECONDS = 7200
PIPELINE_TIMEOUT_SECONDS = 3600
LOG = logging.getLogger(JOB_NAME)


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


class JobInterrupted(Exception):
    """SIGTERM/CTRL-C recibido mientras una corrida está reservada."""


def _interrupt(_signum: int, _frame: Any) -> None:
    raise JobInterrupted("interrupted")


def _log(target_date: date, status: str, message: str, *, error: bool = False) -> None:
    level = logging.ERROR if error else logging.INFO
    LOG.log(level, "job=%s target_date=%s status=%s %s", JOB_NAME, target_date, status, message)


def _safe_error(exc: BaseException) -> str:
    message = f"{type(exc).__name__}: {exc}"
    for key in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL"):
        value = os.environ.get(key)
        if value:
            message = message.replace(value, "[redacted]")
    return message[:500]


def resolve_target_date(today: date | None = None) -> date:
    value = os.environ.get("TARGET_DATE")
    if value is not None:
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError("TARGET_DATE must use YYYY-MM-DD")
        return date.fromisoformat(value)
    return (today or datetime.now(timezone.utc).date()) - timedelta(days=1)


def _csv_path(target_date: date) -> Path:
    return REPO_ROOT / "data" / "raw" / f"telemetry_{target_date.isoformat()}.csv"


def _valid_existing_csv(path: Path) -> bool:
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            return tuple(next(csv.reader(stream))) == CSV_COLUMNS
    except (OSError, StopIteration, csv.Error, UnicodeError):
        return False


def export_day(client: Any, target_date: date, run_id: str, destination: Path | None = None) -> Path:
    destination = destination or _csv_path(target_date)
    if destination.exists():
        if not _valid_existing_csv(destination):
            raise RuntimeError("existing CSV has an invalid header")
        _log(target_date, "processing", "existing_csv_reused")
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    start = datetime.combine(target_date, clock_time.min, timezone.utc)
    end = start + timedelta(days=1)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", prefix=f".{destination.stem}.",
            suffix=".tmp", dir=destination.parent, delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            offset = 0
            while True:
                query = (
                    client.table("telemetry_events").select(",".join(CSV_COLUMNS))
                    .gte("timestamp", start.isoformat()).lt("timestamp", end.isoformat())
                    .order("timestamp").order("event_id")
                    .range(offset, offset + PAGE_SIZE - 1)
                )
                rows = query.execute().data
                if not isinstance(rows, list):
                    raise RuntimeError("telemetry query returned an invalid page")
                for row in rows:
                    writer.writerow({
                        column: json.dumps(row[column], ensure_ascii=False, sort_keys=True)
                        if column == "tags" else row.get(column)
                        for column in CSV_COLUMNS
                    })
                heartbeat_run(client, run_id)
                offset += len(rows)
                if len(rows) < PAGE_SIZE:
                    break
            stream.flush()
            os.fsync(stream.fileno())
        if destination.exists():
            raise RuntimeError("CSV appeared while exporting")
        os.replace(temp_path, destination)
        temp_path = None
        _log(target_date, "processing", f"csv_exported rows={offset}")
        return destination
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _stop_child(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def run_pipeline(client: Any, target_date: date, run_id: str) -> None:
    week_start = target_date - timedelta(days=target_date.weekday())
    heartbeat_run(client, run_id)
    command = [
        sys.executable, str(REPO_ROOT / "data" / "pipelines" / "pipeline.py"),
        "--week-start", week_start.isoformat(), "--triggered-by", "schedule",
    ]
    process = subprocess.Popen(
        command, cwd=REPO_ROOT, start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    _log(target_date, "processing", f"pipeline_started week_start={week_start}")
    deadline = time.monotonic() + PIPELINE_TIMEOUT_SECONDS
    try:
        while process.poll() is None:
            heartbeat_run(client, run_id)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("pipeline exceeded its time limit")
            try:
                process.wait(timeout=min(HEARTBEAT_SECONDS, remaining))
            except subprocess.TimeoutExpired:
                pass
        if process.returncode != 0:
            raise RuntimeError(f"pipeline exited with code {process.returncode}")
        _log(target_date, "processing", f"pipeline_completed week_start={week_start}")
    finally:
        _stop_child(process)


def run(target_date: date, *, client: Any | None = None, destination: Path | None = None) -> int:
    client = client or get_client()
    claim = claim_run(client, target_date, STALE_AFTER_SECONDS)
    if claim.outcome != "claimed":
        if claim.outcome == "already_completed" and not (destination or _csv_path(target_date)).exists():
            _log(target_date, "failed", "completed_run_missing_csv", error=True)
            return 1
        _log(target_date, claim.outcome, "skipped")
        return 0

    assert claim.run_id is not None
    _log(target_date, "processing", f"started run_id={claim.run_id}")
    try:
        export_day(client, target_date, claim.run_id, destination)
        run_pipeline(client, target_date, claim.run_id)
        finish_run(client, claim.run_id, "completed")
    except BaseException as exc:
        message = _safe_error(exc)
        try:
            finish_run(client, claim.run_id, "failed", message)
        except Exception as final_error:
            _log(target_date, "failed", f"finalization_error={_safe_error(final_error)}", error=True)
        _log(target_date, "failed", message, error=True)
        return 1
    _log(target_date, "completed", f"finished run_id={claim.run_id}")
    return 0


def main() -> int:
    handler = logging.StreamHandler()
    handler.setFormatter(UTCFormatter(
        "%(asctime)sZ %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    ))
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)
    LOG.propagate = False
    target_date: date | None = None
    try:
        target_date = resolve_target_date()
        signal.signal(signal.SIGTERM, _interrupt)
        signal.signal(signal.SIGINT, _interrupt)
        return run(target_date)
    except Exception as exc:
        LOG.error("job=%s target_date=%s status=failed %s", JOB_NAME,
                  target_date or "unresolved", _safe_error(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
