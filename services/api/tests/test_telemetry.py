"""routes/telemetry.py — stub POST /telemetry/events (Fase 1 de Project 6.1).

Solo valida el envelope y cuenta eventos; no persiste nada todavía.
"""


def _valid_event(**overrides) -> dict:
    event = {
        "eventId": "5b1e6e2a-1f7e-4b7a-9c3a-9f6b2e6a1a11",
        "timestamp": "2026-09-07T12:00:00Z",
        "sessionId": "8a2c1d3e-4f5a-4b6c-9d7e-1a2b3c4d5e6f",
        "userId": "1",
        "event_type": "backoffice_section_viewed",
        "schemaVersion": "1.0.0",
        "requestId": None,
        "properties": {"route": "/suppliers"},
    }
    event.update(overrides)
    return event


class TestReceiveEvents:
    def test_empty_batch_is_accepted(self, client):
        response = client.post("/telemetry/events", json={"events": []})

        assert response.status_code == 200
        assert response.json() == {"received": 0}

    def test_batch_with_events_returns_the_count(self, client):
        payload = {"events": [_valid_event(), _valid_event(event_type="login_succeeded")]}

        response = client.post("/telemetry/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"received": 2}

    def test_event_missing_a_required_envelope_field_is_rejected(self, client):
        event = _valid_event()
        del event["sessionId"]

        response = client.post("/telemetry/events", json={"events": [event]})

        assert response.status_code == 422

    def test_properties_accepts_any_shape_no_per_event_allowlist_yet(self, client):
        # Documenta el comportamiento actual: este stub (Fase 1) valida solo
        # el envelope, no el allowlist por evento de event-schemas.json —
        # eso llega con la persistencia real (próximo proyecto).
        payload = {"events": [_valid_event(properties={"cualquier_cosa": 123})]}

        response = client.post("/telemetry/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"received": 1}
