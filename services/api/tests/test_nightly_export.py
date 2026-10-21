"""Proyecto 9: exportación y orquestación, sin red ni proveedor real."""

import csv
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts import nightly_export as job  # noqa: E402
from services.job_runner import Claim  # noqa: E402


class Query:
    def __init__(self, rows, fail_page=None):
        self.rows = rows
        self.fail_page = fail_page
        self.lower = None
        self.upper = None
        self.start = 0
        self.stop = None

    def select(self, _columns):
        return self

    def gte(self, _column, value):
        self.lower = value
        return self

    def lt(self, _column, value):
        self.upper = value
        return self

    def order(self, _column):
        return self

    def range(self, start, stop):
        self.start, self.stop = start, stop
        return self

    def execute(self):
        if self.start == self.fail_page:
            raise RuntimeError("page unavailable")
        rows = sorted(
            (row for row in self.rows if self.lower <= row["timestamp"] < self.upper),
            key=lambda row: (row["timestamp"], row["event_id"]),
        )
        return SimpleNamespace(data=rows[self.start : self.stop + 1])


class Client:
    def __init__(self, rows, fail_page=None):
        self.rows = rows
        self.fail_page = fail_page

    def table(self, name):
        assert name == "telemetry_events"
        return Query(self.rows, self.fail_page)


def row(event_id, timestamp):
    return {
        "event_id": event_id, "timestamp": timestamp,
        "session_id": "session", "user_id": None, "event_type": "api_request",
        "schema_version": "1", "request_id": None, "tags": {"country": "CO"},
    }


def test_date_resolution(monkeypatch):
    monkeypatch.delenv("TARGET_DATE", raising=False)
    assert job.resolve_target_date(date(2026, 1, 1)) == date(2025, 12, 31)
    monkeypatch.setenv("TARGET_DATE", "2026-02-14")
    assert job.resolve_target_date() == date(2026, 2, 14)
    monkeypatch.setenv("TARGET_DATE", "2026-2-14")
    with pytest.raises(ValueError):
        job.resolve_target_date()


def test_exports_all_pages_and_utc_day_atomically(monkeypatch, tmp_path):
    monkeypatch.setattr(job, "PAGE_SIZE", 2)
    heartbeats = []
    monkeypatch.setattr(job, "heartbeat_run", lambda _client, run_id: heartbeats.append(run_id))
    client = Client([
        row("outside-before", "2026-02-13T23:59:59+00:00"),
        row("a", "2026-02-14T00:00:00+00:00"),
        row("b", "2026-02-14T12:00:00+00:00"),
        row("c", "2026-02-14T23:59:59+00:00"),
        row("outside-after", "2026-02-15T00:00:00+00:00"),
    ])
    path = tmp_path / "telemetry_2026-02-14.csv"
    job.export_day(client, date(2026, 2, 14), "run-1", path)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [item["event_id"] for item in rows] == ["a", "b", "c"]
    assert rows[0]["tags"] == '{"country": "CO"}'
    assert heartbeats == ["run-1", "run-1"]
    assert not list(tmp_path.glob("*.tmp"))


def test_failed_page_does_not_publish_partial_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(job, "PAGE_SIZE", 2)
    monkeypatch.setattr(job, "heartbeat_run", lambda *_: None)
    client = Client([
        row("a", "2026-02-14T01:00:00+00:00"),
        row("b", "2026-02-14T02:00:00+00:00"),
        row("c", "2026-02-14T03:00:00+00:00"),
    ], fail_page=2)
    path = tmp_path / "telemetry_2026-02-14.csv"
    with pytest.raises(RuntimeError, match="page unavailable"):
        job.export_day(client, date(2026, 2, 14), "run-1", path)
    assert not path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_run_completes_then_skips_duplicate(monkeypatch, tmp_path):
    target = date(2026, 2, 14)
    path = tmp_path / "telemetry_2026-02-14.csv"
    calls = []
    monkeypatch.setattr(job, "claim_run", lambda *_: Claim("claimed", "run-1"))
    monkeypatch.setattr(job, "export_day", lambda *_args: path.write_text(",".join(job.CSV_COLUMNS) + "\n"))
    monkeypatch.setattr(job, "run_pipeline", lambda *_: calls.append("pipeline"))
    monkeypatch.setattr(job, "finish_run", lambda *_args: calls.append(_args[2]))
    assert job.run(target, client=object(), destination=path) == 0
    assert calls == ["pipeline", "completed"]

    monkeypatch.setattr(job, "claim_run", lambda *_: Claim("already_completed", None))
    assert job.run(target, client=object(), destination=path) == 0
    assert calls == ["pipeline", "completed"]


def test_child_failure_marks_run_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(job, "claim_run", lambda *_: Claim("claimed", "run-2"))
    monkeypatch.setattr(job, "export_day", lambda *_: None)
    monkeypatch.setattr(job, "run_pipeline", lambda *_: (_ for _ in ()).throw(RuntimeError("pipeline failed")))
    finished = []
    monkeypatch.setattr(job, "finish_run", lambda *_args: finished.append(_args[2:]))
    assert job.run(date(2026, 2, 14), client=object(), destination=tmp_path / "x.csv") == 1
    assert finished == [("failed", "RuntimeError: pipeline failed")]


def test_nightly_pipeline_uses_existing_weekly_cli(monkeypatch):
    captured = {}
    monkeypatch.setattr(job, "heartbeat_run", lambda *_: None)

    class Process:
        returncode = 0

        def poll(self):
            return 0

    def popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Process()

    monkeypatch.setattr(job.subprocess, "Popen", popen)
    job.run_pipeline(object(), date(2026, 2, 15), "run-3")
    assert captured["command"][-4:] == [
        "--week-start", "2026-02-09", "--triggered-by", "schedule",
    ]
    assert captured["kwargs"]["start_new_session"] is True
