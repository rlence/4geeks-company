"""routes/telemetry.py — endpoint real POST /telemetry/events (Project 6.2).

Valida cada evento del lote individualmente, persiste los válidos en
Supabase con un único upsert por lote (event_id como PK, ignore_duplicates
para tolerar reintentos), y reporta received/stored/rejected.
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
    def test_empty_batch_is_accepted_without_calling_upsert(self, client, fake_supabase):
        response = client.post("/telemetry/events", json={"events": []})

        assert response.status_code == 200
        assert response.json() == {"received": 0, "stored": 0, "rejected": 0}
        assert fake_supabase.upsert_calls == []

    def test_valid_batch_is_stored_in_a_single_bulk_upsert(self, client, fake_supabase):
        payload = {
            "events": [
                _valid_event(),
                _valid_event(
                    eventId="ffffffff-ffff-4fff-8fff-ffffffffffff",
                    event_type="login_succeeded",
                ),
            ]
        }

        response = client.post("/telemetry/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"received": 2, "stored": 2, "rejected": 0}
        assert len(fake_supabase.upsert_calls) == 1
        assert len(fake_supabase.upsert_calls[0]) == 2
        assert len(fake_supabase.inserted_rows) == 2

    def test_retrying_the_same_batch_does_not_duplicate_rows(self, client, fake_supabase):
        # Reintento del frontend tras un timeout: mismo eventId reenviado.
        # ON CONFLICT (event_id) DO NOTHING evita duplicar la fila.
        payload = {"events": [_valid_event()]}

        client.post("/telemetry/events", json=payload)
        response = client.post("/telemetry/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"received": 1, "stored": 1, "rejected": 0}
        assert len(fake_supabase.inserted_rows) == 1

    def test_event_missing_a_required_envelope_field_is_rejected_without_failing_the_batch(
        self, client, fake_supabase
    ):
        invalid_event = _valid_event()
        del invalid_event["sessionId"]
        payload = {"events": [_valid_event(), invalid_event]}

        response = client.post("/telemetry/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"received": 2, "stored": 1, "rejected": 1}
        assert len(fake_supabase.inserted_rows) == 1

    def test_fully_invalid_batch_stores_nothing_and_does_not_call_upsert(
        self, client, fake_supabase
    ):
        invalid_event = _valid_event()
        del invalid_event["sessionId"]

        response = client.post("/telemetry/events", json={"events": [invalid_event]})

        assert response.status_code == 200
        assert response.json() == {"received": 1, "stored": 0, "rejected": 1}
        assert fake_supabase.upsert_calls == []

    def test_properties_accepts_any_shape_no_per_event_allowlist_here(self, client, fake_supabase):
        # El allowlist por evento (event-schemas.json) lo aplica el frontend
        # (Project 6.1) al emitir; este endpoint solo valida el envelope.
        payload = {"events": [_valid_event(properties={"cualquier_cosa": 123})]}

        response = client.post("/telemetry/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"received": 1, "stored": 1, "rejected": 0}
        assert fake_supabase.inserted_rows[0]["tags"] == {"cualquier_cosa": 123}

    def test_stored_row_maps_envelope_fields_to_table_columns(self, client, fake_supabase):
        payload = {"events": [_valid_event()]}

        client.post("/telemetry/events", json=payload)

        row = fake_supabase.inserted_rows[0]
        assert row == {
            "event_id": "5b1e6e2a-1f7e-4b7a-9c3a-9f6b2e6a1a11",
            "timestamp": "2026-09-07T12:00:00Z",
            "session_id": "8a2c1d3e-4f5a-4b6c-9d7e-1a2b3c4d5e6f",
            "user_id": "1",
            "event_type": "backoffice_section_viewed",
            "schema_version": "1.0.0",
            "request_id": None,
            "tags": {"route": "/suppliers"},
        }
