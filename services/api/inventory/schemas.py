from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

Category = Literal['meat', 'produce', 'sauce', 'beverage', 'packaging', 'cleaning']
Country = Literal['CO', 'US']
Reason = Literal['consumption', 'waste']
Identifier = Annotated[int, Field(strict=True, gt=0, le=9007199254740991)]
# Decimal en el cálculo, número JSON en el contrato de la interfaz existente.
Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6, allow_inf_nan=False),
                     PlainSerializer(float, return_type=float, when_used='json')]
Balance = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used='json')]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class IngredientCreate(Input):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=40)
    category: Category
    country: Country

class IngredientRead(IngredientCreate):
    id: Identifier
    current_stock: Balance

class MovementCreate(Input):
    ingredient_id: Identifier
    quantity: Quantity
    location_id: int = Field(strict=True, ge=1, le=14)
    user_uuid: str = Field(min_length=1, max_length=80)

class EntryCreate(MovementCreate):
    supplier_name: str = Field(min_length=1, max_length=160)

class ExitCreate(MovementCreate):
    reason: Reason

class EntryRead(EntryCreate):
    id: Identifier
    created_at: datetime

class ExitRead(ExitCreate):
    id: Identifier
    created_at: datetime

class OrderRead(MovementCreate):
    id: Identifier
    type: Literal['inbound', 'outbound']
    ingredient_name: str
    unit: str
    created_at: datetime
    supplier_name: str | None = None
    reason: Reason | None = None
