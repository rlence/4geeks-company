"""services/telemetry/analysis.py — transformaciones Pandas sobre eventos.

El fake client no valida filtros de Supabase (eso se verifica en vivo,
Fase 3 del plan) — solo confirma que cada función transforma bien un set
fijo de filas: agrupa por día/tipo, calcula el ratio de error con el
denominador correcto, y extrae route/p95_ms de tags descartando nulos.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "telemetry"))

from analysis import (  # noqa: E402
    api_latency_p95_by_route_per_day,
    auth_failure_rate_by_day,
    error_rate_by_day,
    events_per_day_by_type,
)


class FakeExecuteResult:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def select(self, columns: str) -> "FakeQuery":
        return self

    def gte(self, column: str, value: str) -> "FakeQuery":
        return self

    def lt(self, column: str, value: str) -> "FakeQuery":
        return self

    def in_(self, column: str, values: list[str]) -> "FakeQuery":
        return FakeQuery([row for row in self._rows if row.get(column) in values])

    def execute(self) -> FakeExecuteResult:
        return FakeExecuteResult(self._rows)


class FakeClient:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def table(self, name: str) -> FakeQuery:
        assert name == "telemetry_events"
        return FakeQuery(self._rows)


START = datetime(2026, 9, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 3, tzinfo=timezone.utc)


class TestEventsPerDayByType:
    def test_groups_by_date_and_event_type(self):
        client = FakeClient(
            [
                {"timestamp": "2026-09-01T10:00:00Z", "event_type": "login_succeeded"},
                {"timestamp": "2026-09-01T12:00:00Z", "event_type": "login_succeeded"},
                {"timestamp": "2026-09-02T09:00:00Z", "event_type": "frontend_error_captured"},
            ]
        )

        result = events_per_day_by_type(client, START, END)

        assert {"date": "2026-09-01", "event_type": "login_succeeded", "count": 2} in result
        assert {
            "date": "2026-09-02",
            "event_type": "frontend_error_captured",
            "count": 1,
        } in result

    def test_empty_window_returns_empty_list(self):
        client = FakeClient([])

        assert events_per_day_by_type(client, START, END) == []


class TestErrorRateByDay:
    def test_computes_ratio_of_error_events_over_total(self):
        client = FakeClient(
            [
                {"timestamp": "2026-09-01T10:00:00Z", "event_type": "frontend_error_captured"},
                {"timestamp": "2026-09-01T11:00:00Z", "event_type": "login_succeeded"},
                {"timestamp": "2026-09-01T12:00:00Z", "event_type": "login_succeeded"},
                {"timestamp": "2026-09-01T13:00:00Z", "event_type": "login_succeeded"},
            ]
        )

        result = error_rate_by_day(client, START, END)

        assert len(result) == 1
        assert result[0]["date"] == "2026-09-01"
        assert result[0]["total"] == 4
        assert result[0]["errors"] == 1
        assert result[0]["error_rate"] == 0.25


class TestApiLatencyP95ByRoutePerDay:
    def test_extracts_route_and_p95_from_tags(self):
        client = FakeClient(
            [
                {
                    "timestamp": "2026-09-01T10:00:00Z",
                    "event_type": "api_latency_recorded",
                    "tags": {"route": "/suppliers", "p95_ms": 120, "count": 10},
                },
                {
                    "timestamp": "2026-09-01T11:00:00Z",
                    "event_type": "api_latency_recorded",
                    "tags": {"route": "/suppliers", "p95_ms": 180, "count": 5},
                },
            ]
        )

        result = api_latency_p95_by_route_per_day(client, START, END)

        assert len(result) == 1
        assert result[0]["route"] == "/suppliers"
        assert result[0]["p95_ms"] == 150
        assert result[0]["samples"] == 15

    def test_drops_rows_with_no_route_in_tags(self):
        client = FakeClient(
            [
                {
                    "timestamp": "2026-09-01T10:00:00Z",
                    "event_type": "api_latency_recorded",
                    "tags": {"p95_ms": 120, "count": 1},
                }
            ]
        )

        assert api_latency_p95_by_route_per_day(client, START, END) == []


class TestAuthFailureRateByDay:
    def test_computes_daily_failure_ratio(self):
        client = FakeClient(
            [
                {"timestamp": "2026-09-01T10:00:00Z", "event_type": "login_attempt_failed"},
                {"timestamp": "2026-09-01T11:00:00Z", "event_type": "login_succeeded"},
                {"timestamp": "2026-09-01T12:00:00Z", "event_type": "login_succeeded"},
                {"timestamp": "2026-09-01T13:00:00Z", "event_type": "login_succeeded"},
            ]
        )

        result = auth_failure_rate_by_day(client, START, END)

        assert result == [{"date": "2026-09-01", "auth_failure_rate": 0.25}]
