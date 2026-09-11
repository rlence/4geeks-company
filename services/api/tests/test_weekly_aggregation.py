"""data/process/weekly_aggregation.py — transformación pura del pipeline
de Desempeño de Negocio (Hito 6, Parte 2). Sin Prefect, sin Supabase.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))

from process.weekly_aggregation import compute_weekly_kpis, dedup_events  # noqa: E402

WEEK_START = date(2026, 9, 7)


def _event(event_id: str, event_type: str, **tags) -> dict:
    return {"event_id": event_id, "event_type": event_type, "tags": tags}


class TestDedupEvents:
    def test_drops_events_with_a_repeated_event_id(self):
        events = [
            _event("a", "inbound_order_created", location_id=1),
            _event("a", "inbound_order_created", location_id=1),
            _event("b", "inbound_order_created", location_id=1),
        ]

        assert len(dedup_events(events)) == 2


class TestComputeWeeklyKpis:
    def test_empty_input_returns_empty_list(self):
        assert compute_weekly_kpis([], WEEK_START) == []

    def test_aggregates_purchase_and_waste_cost_per_location(self):
        events = [
            _event("a", "inbound_order_created", location_id=1, country="CO", quantity=10, unit_cost=5000),
            _event("b", "stock_waste_registered", location_id=1, country="CO", quantity=2, unit_cost=5000),
            _event("c", "stock_threshold_triggered", location_id=1, country="CO"),
            _event("d", "inbound_order_created", location_id=2, country="US", quantity=4, unit_cost=20),
        ]

        rows = compute_weekly_kpis(events, WEEK_START)
        by_location = {row["location_id"]: row for row in rows}

        assert by_location["1"]["total_purchase_cost"] == 50000.0
        assert by_location["1"]["total_waste_cost"] == 10000.0
        assert by_location["1"]["waste_ratio"] == 0.2
        assert by_location["1"]["stockout_events_count"] == 1
        assert by_location["1"]["price_alert_events_count"] == 0
        assert by_location["1"]["currency"] == "COP"
        assert by_location["1"]["week_start"] == "2026-09-07"

        assert by_location["2"]["total_purchase_cost"] == 80.0
        assert by_location["2"]["currency"] == "USD"

    def test_waste_ratio_is_zero_when_there_were_no_purchases(self):
        events = [
            _event("a", "stock_waste_registered", location_id=1, country="CO", quantity=2, unit_cost=5000),
        ]

        rows = compute_weekly_kpis(events, WEEK_START)

        assert rows[0]["total_purchase_cost"] == 0.0
        assert rows[0]["waste_ratio"] == 0.0

    def test_events_missing_location_id_or_country_are_dropped(self):
        events = [
            _event("a", "inbound_order_created", country="CO", quantity=10, unit_cost=5000),
            _event("b", "inbound_order_created", location_id=1, quantity=10, unit_cost=5000),
        ]

        assert compute_weekly_kpis(events, WEEK_START) == []

    def test_price_alert_events_are_counted(self):
        events = [
            _event("a", "ingredient_price_variance_detected", location_id=1, country="CO"),
            _event("b", "ingredient_price_variance_detected", location_id=1, country="CO"),
        ]

        rows = compute_weekly_kpis(events, WEEK_START)

        assert rows[0]["price_alert_events_count"] == 2
        assert rows[0]["total_purchase_cost"] == 0.0
