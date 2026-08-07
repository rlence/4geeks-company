from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Country(str, Enum):
    COLOMBIA = "Colombia"
    USA = "USA"


class Currency(str, Enum):
    COP = "COP"
    USD = "USD"


class Category(str, Enum):
    CARNE = "carne"
    VERDURAS_Y_HORTALIZAS = "verduras_y_hortalizas"
    SALSAS_Y_CONDIMENTOS = "salsas_y_condimentos"
    BEBIDAS = "bebidas"
    PACKAGING = "packaging"
    PRODUCTOS_LIMPIEZA = "productos_limpieza"
    LACTEOS = "lacteos"
    CARBON_Y_COMBUSTIBLE = "carbon_y_combustible"


class SupplierStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


COUNTRY_CURRENCY: dict[Country, Currency] = {
    Country.COLOMBIA: Currency.COP,
    Country.USA: Currency.USD,
}


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1)
    country: Country
    categories: list[Category] = Field(min_length=1)
    rate_per_unit: float = Field(gt=0)
    currency: Currency
    status: SupplierStatus = SupplierStatus.ACTIVE
    contact_email: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def check_currency_matches_country(self) -> "SupplierCreate":
        expected = COUNTRY_CURRENCY[self.country]
        if self.currency != expected:
            raise ValueError(
                f"currency debe ser '{expected.value}' para country='{self.country.value}'"
            )
        return self


class SupplierOut(SupplierCreate):
    id: int
    updated_at: datetime


class SupplierRateUpdate(BaseModel):
    rate_per_unit: float = Field(gt=0)


class SupplierStatusUpdate(BaseModel):
    status: SupplierStatus
