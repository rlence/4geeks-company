"""Tests unitarios de las tasks de transformación del pipeline de
Desempeño de Negocio (Hito 6, Parte 3).

Corre vía `python -m pytest tests/pipelines/test_pipeline.py`. Este repo
no tiene un venv en la raíz — prefect/pandas viven en el venv de
services/api (ver Contexto de context/plans/hito6-part-2.md), así que el
comando real equivalente, corrido desde la raíz del monorepo, es:

    uv run --project services/api python -m pytest tests/pipelines/test_pipeline.py

Cada task se testea llamando a `.fn(...)` — la función subyacente sin el
motor de Prefect — así los tests no dependen de una base de datos ni de
ninguna API externa, tal como pide el rule.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data" / "pipelines"))

from pipeline import (  # noqa: E402
    compute_weekly_kpis_task,
    dedup_events_task,
    validate_weekly_rows_task,
)

WEEK_START = date(2026, 9, 7)


def _event(event_id: str, event_type: str, **tags) -> dict:
    return {"event_id": event_id, "event_type": event_type, "tags": tags}


class TestDedupEventsTask:
    def test_drops_events_with_a_repeated_event_id(self):
        events = [
            _event("a", "inbound_order_created", location_id=1, country="CO"),
            _event("a", "inbound_order_created", location_id=1, country="CO"),
            _event("b", "inbound_order_created", location_id=1, country="CO"),
        ]

        assert len(dedup_events_task.fn(events)) == 2


class TestComputeWeeklyKpisTask:
    def test_waste_ratio_matches_the_hand_calculated_value(self):
        # "Ratio de merma" (hito-6-part-1.md §2): costo de merma / costo de
        # compra de la semana. 10 u. a 5000 c/u compradas, 2 u. a 5000 c/u
        # mermadas -> compra=50000, merma=10000, ratio=10000/50000=0.2.
        events = [
            _event(
                "a", "inbound_order_created", location_id=1, country="CO", quantity=10, unit_cost=5000
            ),
            _event(
                "b", "stock_waste_registered", location_id=1, country="CO", quantity=2, unit_cost=5000
            ),
        ]

        rows = compute_weekly_kpis_task.fn(events, WEEK_START)

        assert len(rows) == 1
        assert rows[0]["total_purchase_cost"] == 50000.0
        assert rows[0]["total_waste_cost"] == 10000.0
        assert rows[0]["waste_ratio"] == 0.2

    def test_empty_input_returns_empty_list(self):
        assert compute_weekly_kpis_task.fn([], WEEK_START) == []


class TestValidateWeeklyRowsTask:
    def test_drops_rows_with_unknown_country_or_non_numeric_cost(self):
        rows = [
            {
                "location_id": "1",
                "country": "XX",  # país desconocido — no CO/US
                "total_purchase_cost": 100.0,
                "total_waste_cost": 0.0,
            },
            {
                "location_id": "2",
                "country": "CO",
                "total_purchase_cost": None,  # campo nulo donde no se espera
                "total_waste_cost": 0.0,
            },
            {
                "location_id": "3",
                "country": "US",
                "total_purchase_cost": -50.0,  # tipo correcto, valor inválido
                "total_waste_cost": 0.0,
            },
            {
                "location_id": "4",
                "country": "CO",
                "total_purchase_cost": 100.0,
                "total_waste_cost": 10.0,
            },
        ]

        result = validate_weekly_rows_task.fn(rows)

        assert [row["location_id"] for row in result] == ["4"]
