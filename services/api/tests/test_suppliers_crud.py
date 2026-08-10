"""
routes/suppliers.py — grupo CRUD/listado (create, list, get, delete).

`suppliers` es el único dominio de recursos del backoffice hoy (ver
TESTING.md); se divide en dos módulos de test por concern en lugar de por
"dominio de negocio" distinto, ya que no existe un segundo dominio real.
"""


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


class TestCreateSupplier:
    def test_valid_payload_creates_a_supplier(self, client):
        response = client.post("/suppliers", json=_valid_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Proveedor de Prueba"
        assert body["status"] == "active"
        assert "id" in body and "updated_at" in body

    def test_duplicate_categories_are_accepted_as_sent(self, client):
        # Documenta el comportamiento actual: no hay deduplicación de
        # categorías, ni validación que la exija.
        response = client.post(
            "/suppliers", json=_valid_payload(categories=["carne", "carne"])
        )

        assert response.status_code == 201
        assert response.json()["categories"] == ["carne", "carne"]

    def test_optional_fields_can_be_omitted(self, client):
        response = client.post("/suppliers", json=_valid_payload())

        assert response.status_code == 201
        assert response.json()["contact_email"] is None
        assert response.json()["notes"] is None

    def test_currency_not_matching_country_is_rejected(self, client):
        response = client.post(
            "/suppliers", json=_valid_payload(country="Colombia", currency="USD")
        )

        assert response.status_code == 422

    def test_non_positive_rate_is_rejected(self, client):
        response = client.post("/suppliers", json=_valid_payload(rate_per_unit=0))

        assert response.status_code == 422

    def test_empty_categories_list_is_rejected(self, client):
        response = client.post("/suppliers", json=_valid_payload(categories=[]))

        assert response.status_code == 422


class TestListSuppliers:
    def test_no_filters_returns_every_supplier(self, client):
        client.post("/suppliers", json=_valid_payload(name="A"))
        client.post("/suppliers", json=_valid_payload(name="B"))

        response = client.get("/suppliers")

        assert response.status_code == 200
        assert {s["name"] for s in response.json()} == {"A", "B"}

    def test_combined_country_and_category_filters_narrow_the_results(self, client):
        client.post(
            "/suppliers",
            json=_valid_payload(name="Carnes CO", country="Colombia", currency="COP", categories=["carne"]),
        )
        client.post(
            "/suppliers",
            json=_valid_payload(
                name="Verduras CO", country="Colombia", currency="COP", categories=["verduras_y_hortalizas"]
            ),
        )
        client.post(
            "/suppliers",
            json=_valid_payload(name="Carnes US", country="USA", currency="USD", categories=["carne"]),
        )

        response = client.get("/suppliers", params={"country": "Colombia", "category": "carne"})

        assert response.status_code == 200
        assert [s["name"] for s in response.json()] == ["Carnes CO"]

    def test_category_with_no_matches_returns_an_empty_list_not_an_error(self, client):
        client.post("/suppliers", json=_valid_payload(categories=["carne"]))

        response = client.get("/suppliers", params={"category": "packaging"})

        assert response.status_code == 200
        assert response.json() == []

    def test_invalid_country_query_value_is_rejected(self, client):
        response = client.get("/suppliers", params={"country": "Brazil"})

        assert response.status_code == 422


class TestGetAndDeleteSupplier:
    def test_get_existing_supplier_returns_it(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()

        response = client.get(f"/suppliers/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_nonexistent_supplier_returns_404(self, client):
        response = client.get("/suppliers/999999")

        assert response.status_code == 404

    def test_delete_existing_supplier_removes_it(self, client):
        created = client.post("/suppliers", json=_valid_payload()).json()

        delete_response = client.delete(f"/suppliers/{created['id']}")
        get_response = client.get(f"/suppliers/{created['id']}")

        assert delete_response.status_code == 204
        assert get_response.status_code == 404

    def test_delete_nonexistent_supplier_returns_404(self, client):
        response = client.delete("/suppliers/999999")

        assert response.status_code == 404
