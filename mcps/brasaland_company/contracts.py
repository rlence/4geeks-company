"""Contratos públicos que FastMCP publica en el discovery de herramientas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Status = Literal["open", "in_progress", "resolved"]
Category = Literal["operations", "technical", "other"]
Country = Literal["CO", "US"]


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Incident(Output):
    id: int = Field(gt=0)
    title: str
    description: str
    category: Category
    status: Status
    origin: Literal["api", "backoffice"]
    created_by: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    version: int = Field(gt=0)


class IncidentList(Output):
    items: list[Incident]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class Ingredient(Output):
    id: int = Field(gt=0)
    name: str
    sku: str
    unit: str
    category: Literal["meat", "produce", "sauce", "beverage", "packaging", "cleaning"]
    country: Country
    current_stock: float


class InventoryOrder(Output):
    id: int = Field(gt=0)
    type: Literal["inbound", "outbound"]
    ingredient_id: int = Field(gt=0)
    ingredient_name: str
    quantity: float
    unit: str
    location_id: int = Field(ge=1, le=14)
    user_uuid: str
    created_at: datetime
    supplier_name: str | None = None
    reason: Literal["consumption", "waste"] | None = None


class InventoryResult(Output):
    operation: Literal["read"] = "read"
    resource: Literal["products", "orders"]
    items: list[Ingredient | InventoryOrder]
