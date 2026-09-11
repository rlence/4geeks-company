"""data/pipelines/pipeline.py — flow de Prefect del pipeline de
Desempeño de Negocio (Hito 6, Parte 2). Corre contra un fake cliente
Supabase inyectado por monkeypatch (nunca toca la red).
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data" / "pipelines"))

import pipeline  # noqa: E402

from reporting_fakes import FakeReportingClient  # noqa: E402

WEEK_START = date(2026, 9, 7)


def _seed_telemetry_events(client: FakeReportingClient) -> None:
    client.seed(
        "public",
        "telemetry_events",
        [
            {
                "event_id": "a",
                "event_type": "inbound_order_created",
                "timestamp": "2026-09-08T10:00:00+00:00",
                "tags": {"location_id": 1, "country": "CO", "quantity": 10, "unit_cost": 5000},
            },
            {
                "event_id": "b",
                "event_type": "stock_waste_registered",
                "timestamp": "2026-09-09T10:00:00+00:00",
                "tags": {"location_id": 1, "country": "CO", "quantity": 2, "unit_cost": 5000},
            },
        ],
    )


class TestWeeklyLocationPerformanceFlow:
    def test_loads_computed_rows_and_logs_a_completed_run(self, monkeypatch, tmp_path):
        fake_client = FakeReportingClient()
        _seed_telemetry_events(fake_client)
        monkeypatch.setattr(pipeline, "get_supabase_client", lambda: fake_client)
        monkeypatch.setattr(pipeline, "EVAL_DIR", tmp_path)

        result = pipeline.weekly_location_performance_flow(week_start=WEEK_START)

        assert result == {"week_start": "2026-09-07", "records_loaded": 1}

        performance_rows = fake_client.rows("reporting", "weekly_location_performance")
        assert len(performance_rows) == 1
        assert performance_rows[0]["location_id"] == "1"
        assert performance_rows[0]["total_purchase_cost"] == 50000.0

        run_rows = fake_client.rows("reporting", "pipeline_runs")
        assert len(run_rows) == 1
        run = run_rows[0]
        assert run["status"] == "completed"
        assert run["records_extracted"] == 2
        assert run["records_loaded"] == 1
        assert {"started_at", "finished_at", "records_extracted", "records_loaded", "status"} <= run.keys()

    def test_running_twice_does_not_duplicate_rows(self, monkeypatch, tmp_path):
        fake_client = FakeReportingClient()
        _seed_telemetry_events(fake_client)
        monkeypatch.setattr(pipeline, "get_supabase_client", lambda: fake_client)
        monkeypatch.setattr(pipeline, "EVAL_DIR", tmp_path)

        pipeline.weekly_location_performance_flow(week_start=WEEK_START)
        pipeline.weekly_location_performance_flow(week_start=WEEK_START)

        performance_rows = fake_client.rows("reporting", "weekly_location_performance")
        assert len(performance_rows) == 1
        assert performance_rows[0]["total_purchase_cost"] == 50000.0

    def test_a_failing_optional_snapshot_task_does_not_fail_the_flow(self, monkeypatch, tmp_path):
        fake_client = FakeReportingClient()
        _seed_telemetry_events(fake_client)
        monkeypatch.setattr(pipeline, "get_supabase_client", lambda: fake_client)

        def _broken_snapshot(rows, week_start):
            raise RuntimeError("disco lleno, a propósito para el test")

        monkeypatch.setattr(pipeline.snapshot_to_eval, "fn", _broken_snapshot)

        result = pipeline.weekly_location_performance_flow(week_start=WEEK_START)

        assert result == {"week_start": "2026-09-07", "records_loaded": 1}
        run = fake_client.rows("reporting", "pipeline_runs")[0]
        assert run["status"] == "completed"

    def test_extraction_only_pulls_events_within_the_requested_week(self, monkeypatch, tmp_path):
        fake_client = FakeReportingClient()
        fake_client.seed(
            "public",
            "telemetry_events",
            [
                {
                    "event_id": "in-window",
                    "event_type": "inbound_order_created",
                    "timestamp": "2026-09-08T10:00:00+00:00",
                    "tags": {"location_id": 1, "country": "CO", "quantity": 1, "unit_cost": 100},
                },
                {
                    "event_id": "out-of-window",
                    "event_type": "inbound_order_created",
                    "timestamp": "2026-09-20T10:00:00+00:00",
                    "tags": {"location_id": 1, "country": "CO", "quantity": 1, "unit_cost": 999},
                },
            ],
        )
        monkeypatch.setattr(pipeline, "get_supabase_client", lambda: fake_client)
        monkeypatch.setattr(pipeline, "EVAL_DIR", tmp_path)

        pipeline.weekly_location_performance_flow(week_start=WEEK_START)

        performance_rows = fake_client.rows("reporting", "weekly_location_performance")
        assert performance_rows[0]["total_purchase_cost"] == 100.0
