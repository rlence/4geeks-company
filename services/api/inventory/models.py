from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, DateTime, Numeric, text
from sqlmodel import SQLModel, Field

class Ingredient(SQLModel, table=True):
    __tablename__ = 'ingredients'
    __table_args__ = {'schema': 'inventory'}
    id: int | None = Field(default=None, primary_key=True)
    name: str
    sku: str
    unit: str
    category: str
    country: str

class Movement(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key='inventory.ingredients.id')
    quantity: Decimal = Field(sa_type=Numeric(18, 6), nullable=False)
    location_id: int
    user_uuid: str
    created_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True), nullable=False, sa_column_kwargs={'server_default': text('now()')})

class IngredientEntry(Movement, table=True):
    __tablename__ = 'entries'
    __table_args__ = {'schema': 'inventory'}
    supplier_name: str

class IngredientExit(Movement, table=True):
    __tablename__ = 'exits'
    __table_args__ = {'schema': 'inventory'}
    reason: str
