"""Genera volumen realista para medir el caching. No forma parte del seeder oficial (seed.py)."""

import random
from datetime import datetime, timezone

from database import suppliers_table
from models import COUNTRY_CURRENCY, Category, Country

random.seed(42)

NAME_PREFIXES = ["Distribuidora", "Comercializadora", "Proveedora", "Importadora", "Cooperativa"]
NAME_SUFFIXES = [
    "del Valle", "La Cosecha", "El Sabor", "Andina", "Pacífico", "del Norte",
    "San José", "La Frontera", "Continental", "del Caribe", "Los Andes", "Real",
]
TARGET_COUNT = 3000


def _random_rate(currency_value: str) -> float:
    return round(random.uniform(1500, 45000) if currency_value == "COP" else random.uniform(2, 120), 2)


def _build_supplier(i: int) -> dict:
    country = random.choice(list(Country))
    currency = COUNTRY_CURRENCY[country]
    categories = random.sample(list(Category), k=random.randint(1, 3))
    name = f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_SUFFIXES)} {i}"
    return {
        "name": name,
        "country": country.value,
        "categories": [c.value for c in categories],
        "rate_per_unit": _random_rate(currency.value),
        "currency": currency.value,
        "status": "active" if random.random() > 0.08 else "suspended",
        "contact_email": f"contacto{i}@{name.split()[0].lower()}.com",
        "notes": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    if len(suppliers_table) > 500:
        print(f"Ya hay {len(suppliers_table)} proveedores, omito para no duplicar.")
    else:
        suppliers_table.insert_multiple(_build_supplier(i) for i in range(TARGET_COUNT))
        print(f"{TARGET_COUNT} proveedores insertados. Total: {len(suppliers_table)}")
