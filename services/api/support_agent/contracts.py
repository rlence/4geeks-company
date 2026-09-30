from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from incidents.schemas import Status, Category

class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    source: Literal['rag', 'incidents', 'both', 'clarify', 'readonly', 'unavailable']
    ticket_id: int | None = Field(default=None, gt=0, le=9007199254740991)
    status: Status | None = None
    category: Category | None = None
    rag_question: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def sufficient_reference(self):
        if self.source in ('incidents', 'both') and not (self.ticket_id or self.status or self.category):
            self.source = 'clarify'
        if self.source == 'both' and not self.rag_question.strip():
            self.source = 'clarify'
        return self
