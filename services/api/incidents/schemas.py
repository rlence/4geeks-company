from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Status = Literal['open', 'in_progress', 'resolved']
Category = Literal['operations', 'technical', 'other']

class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=10, max_length=4000)
    category: Category

class Incident(IncidentCreate):
    id: int = Field(gt=0, le=9007199254740991)
    status: Status
    origin: Literal['api', 'backoffice']
    created_by: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    version: int = Field(gt=0)

class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    status: Status
    expected_version: int = Field(gt=0)

class IncidentList(BaseModel):
    items: list[Incident]
    total: int
    limit: int
    offset: int
