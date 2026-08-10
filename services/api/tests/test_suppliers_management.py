"""routes/suppliers.py — grupo de gestión operativa (tarifa y estado)."""


def _valid_payload(**overrides) -> dict:
    payload = {
        "name": "Proveedor de Prueba",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 1000.0,
        "currency": "COP",
    }
    payload.update(overrides)
    return payload


class TestUpdateRate:
    def test_valid_new_rate_updates_the_supplier(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()

        response = client.patch(f"/suppliers/{created['id']}/rate", json={"rate_per_unit": 2500.0})

        assert response.status_code == 200
        body = response.json()
        assert body["rate_per_unit"] == 2500.0
        assert body["updated_at"] != created["updated_at"]

    def test_rate_right_above_the_lower_boundary_is_accepted(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()

        response = client.patch(f"/suppliers/{created['id']}/rate", json={"rate_per_unit": 0.01})

        assert response.status_code == 200
        assert response.json()["rate_per_unit"] == 0.01

    def test_non_positive_rate_is_rejected(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()

        response = client.patch(f"/suppliers/{created['id']}/rate", json={"rate_per_unit": 0})

        assert response.status_code == 422

    def test_updating_rate_of_nonexistent_supplier_returns_404(self, client):
        response = client.patch("/suppliers/999999/rate", json={"rate_per_unit": 100.0})

        assert response.status_code == 404


class TestUpdateStatus:
    def test_valid_transition_updates_the_status(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()
        assert created["status"] == "active"

        response = client.patch(f"/suppliers/{created['id']}/status", json={"status": "suspended"})

        assert response.status_code == 200
        assert response.json()["status"] == "suspended"

    def test_setting_the_same_status_again_is_idempotent(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()

        response = client.patch(f"/suppliers/{created['id']}/status", json={"status": "active"})

        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_status_outside_the_enum_is_rejected(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()

        response = client.patch(f"/suppliers/{created['id']}/status", json={"status": "archived"})

        assert response.status_code == 422

    def test_updating_status_of_nonexistent_supplier_returns_404(self, client):
        response = client.patch("/suppliers/999999/status", json={"status": "active"})

        assert response.status_code == 404
