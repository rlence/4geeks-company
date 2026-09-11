"""services/reporting/endpoints.py — los 3 endpoints de Hito 6 Parte 2:
estado de la última corrida, disparo manual, y consulta de KPIs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data" / "pipelines"))
import pipeline  # noqa: E402

from main import app  # noqa: E402
from reporting_fakes import FakeReportingClient  # noqa: E402
from supabase_client import get_supabase_client  # noqa: E402


def _override_supabase(client: FakeReportingClient):
    app.dependency_overrides[get_supabase_client] = lambda: client


def _clear_override():
    app.dependency_overrides.pop(get_supabase_client, None)


class TestGetLatestPipelineRun:
    def test_returns_empty_dict_when_no_runs_exist(self, client):
        fake = FakeReportingClient()
        _override_supabase(fake)
        try:
            response = client.get("/reporting/pipeline-runs/latest")
        finally:
            _clear_override()

        assert response.status_code == 200
        assert response.json() == {}

    def test_returns_the_most_recent_run(self, client):
        fake = FakeReportingClient()
        fake.seed(
            "reporting",
            "pipeline_runs",
            [
                {"id": "1", "week_start": "2026-08-31", "started_at": "2026-08-31T05:00:00+00:00", "status": "completed"},
                {"id": "2", "week_start": "2026-09-07", "started_at": "2026-09-07T05:00:00+00:00", "status": "completed"},
            ],
        )
        _override_supabase(fake)
        try:
            response = client.get("/reporting/pipeline-runs/latest")
        finally:
            _clear_override()

        assert response.status_code == 200
        assert response.json()["id"] == "2"


class TestGetWeeklyLocationPerformance:
    def test_defaults_to_the_most_recent_week_start(self, client):
        fake = FakeReportingClient()
        fake.seed(
            "reporting",
            "weekly_location_performance",
            [
                {
                    "location_id": "1",
                    "country": "CO",
                    "week_start": "2026-08-31",
                    "total_purchase_cost": 100,
                    "total_waste_cost": 10,
                    "waste_ratio": 0.1,
                    "stockout_events_count": 0,
                    "price_alert_events_count": 0,
                    "currency": "COP",
                },
                {
                    "location_id": "1",
                    "country": "CO",
                    "week_start": "2026-09-07",
                    "total_purchase_cost": 200,
                    "total_waste_cost": 20,
                    "waste_ratio": 0.1,
                    "stockout_events_count": 1,
                    "price_alert_events_count": 0,
                    "currency": "COP",
                },
            ],
        )
        _override_supabase(fake)
        try:
            response = client.get("/reporting/weekly-location-performance")
        finally:
            _clear_override()

        assert response.status_code == 200
        body = response.json()
        assert body["week_start"] == "2026-09-07"
        assert len(body["locations"]) == 1
        assert body["locations"][0]["total_purchase_cost"] == 200

    def test_returns_all_locations_for_an_explicit_week_start(self, client):
        fake = FakeReportingClient()
        fake.seed(
            "reporting",
            "weekly_location_performance",
            [
                {
                    "location_id": "1",
                    "country": "CO",
                    "week_start": "2026-09-07",
                    "total_purchase_cost": 200,
                    "total_waste_cost": 20,
                    "waste_ratio": 0.1,
                    "stockout_events_count": 1,
                    "price_alert_events_count": 0,
                    "currency": "COP",
                },
                {
                    "location_id": "2",
                    "country": "US",
                    "week_start": "2026-09-07",
                    "total_purchase_cost": 80,
                    "total_waste_cost": 0,
                    "waste_ratio": 0,
                    "stockout_events_count": 0,
                    "price_alert_events_count": 0,
                    "currency": "USD",
                },
            ],
        )
        _override_supabase(fake)
        try:
            response = client.get("/reporting/weekly-location-performance", params={"week_start": "2026-09-07"})
        finally:
            _clear_override()

        assert response.status_code == 200
        assert len(response.json()["locations"]) == 2

    def test_returns_empty_locations_when_the_table_has_no_data(self, client):
        fake = FakeReportingClient()
        _override_supabase(fake)
        try:
            response = client.get("/reporting/weekly-location-performance")
        finally:
            _clear_override()

        assert response.status_code == 200
        assert response.json() == {"week_start": None, "locations": []}


class TestTriggerPipelineRun:
    def test_runs_the_flow_and_returns_its_result(self, client, monkeypatch, tmp_path):
        fake = FakeReportingClient()
        fake.seed(
            "public",
            "telemetry_events",
            [
                {
                    "event_id": "a",
                    "event_type": "inbound_order_created",
                    "timestamp": "2026-09-08T10:00:00+00:00",
                    "tags": {"location_id": 1, "country": "CO", "quantity": 10, "unit_cost": 5000},
                }
            ],
        )
        # El endpoint importa el flow directo desde data/pipelines/pipeline.py
        # (no pasa por Depends/get_supabase_client) — se monkeypatchea el
        # cliente del propio módulo pipeline, no el override de FastAPI.
        monkeypatch.setattr(pipeline, "get_supabase_client", lambda: fake)
        monkeypatch.setattr(pipeline, "EVAL_DIR", tmp_path)

        response = client.post(
            "/reporting/pipeline-runs", params={"week_start": "2026-09-07"}
        )

        # El endpoint no acepta query params hoy — llama al flow con su
        # semana por defecto; solo confirmamos que corre end-to-end.
        assert response.status_code == 200
        assert "records_loaded" in response.json()
        assert len(fake.rows("reporting", "pipeline_runs")) == 1
