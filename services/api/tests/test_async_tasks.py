"""Estados HTTP y trabajo del consumidor, sin red externa."""

from datetime import date
from uuid import uuid4

import report_tasks
import routes.tasks as task_routes
from dead_letters import safe_error


def test_status_projection_and_safe_result(client, monkeypatch):
    task_id = str(uuid4())
    monkeypatch.setattr(task_routes, "is_accepted", lambda _: True)

    class Result:
        state = "SUCCESS"
        result = {"week_start": "2026-09-07", "records_loaded": 2, "secret": "never return"}

    monkeypatch.setattr(task_routes.app, "AsyncResult", lambda _: Result())
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json() == {
        "task_id": task_id, "status": "success",
        "result": {"week_start": "2026-09-07", "records_loaded": 2},
    }


def test_unknown_task_is_not_reported_as_pending(client, monkeypatch):
    monkeypatch.setattr(task_routes, "is_accepted", lambda _: False)
    assert client.get(f"/tasks/{uuid4()}").status_code == 404


def test_retry_state_is_projected(client, monkeypatch):
    monkeypatch.setattr(task_routes, "is_accepted", lambda _: True)

    class Result:
        state = "RETRY"
        result = RuntimeError("internal")

    monkeypatch.setattr(task_routes.app, "AsyncResult", lambda _: Result())
    body = client.get(f"/tasks/{uuid4()}").json()
    assert body["status"] == "pending" and body["retrying"] is True
    assert body["result"] is None


def test_worker_calls_existing_flow_with_only_week_start(monkeypatch):
    calls = []
    monkeypatch.setattr(report_tasks, "weekly_location_performance_flow", lambda **kw: calls.append(kw) or {"week_start": "2026-09-07", "records_loaded": 2})
    result = report_tasks.run_weekly_report.apply(args=["2026-09-07"]).get()
    assert result == {"week_start": "2026-09-07", "records_loaded": 2}
    assert calls == [{"week_start": date(2026, 9, 7), "triggered_by": "manual"}]


def test_terminal_failure_records_dead_letter(monkeypatch):
    saved = []
    monkeypatch.setattr(report_tasks, "weekly_location_performance_flow", lambda **_: (_ for _ in ()).throw(RuntimeError("failed")))
    monkeypatch.setattr(report_tasks, "record_terminal_failure", lambda *args: saved.append(args))
    monkeypatch.setattr(report_tasks, "MAX_RETRIES", 0)
    result = report_tasks.run_weekly_report.apply(args=["2026-09-07"], throw=False)
    assert result.state == "FAILURE"
    assert saved[0][1:3] == (date(2026, 9, 7), 1)


def test_safe_error_redacts_environment_secret(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://private")
    assert "redis://private" not in safe_error(RuntimeError("redis://private unavailable"))


def test_worker_retries_then_succeeds(monkeypatch):
    attempts = []

    def flaky(**_kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("transient")
        return {"week_start": "2026-09-07", "records_loaded": 1}

    monkeypatch.setattr(report_tasks, "weekly_location_performance_flow", flaky)
    monkeypatch.setattr(report_tasks, "record_terminal_failure", lambda *_: (_ for _ in ()).throw(AssertionError("DLQ on success")))
    result = report_tasks.run_weekly_report.apply(args=["2026-09-07"], throw=False)
    assert result.state == "SUCCESS"
    assert len(attempts) == 3
