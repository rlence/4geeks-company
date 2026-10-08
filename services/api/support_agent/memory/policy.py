"""Política de memoria de Brasaland: alcance y datos excluidos."""
import re
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Category = Literal[
    "schedule", "supplier_delivery", "local_exception",
    "resolved_escalation", "communication_preference",
]

LIFETIME = {
    "schedule": timedelta(days=90),
    "supplier_delivery": timedelta(days=90),
    "local_exception": timedelta(days=90),
    "resolved_escalation": timedelta(days=30),
    "communication_preference": timedelta(days=180),
}

# Un falso positivo se descarta, nunca se guarda por defecto.
FORBIDDEN = re.compile(
    r"brasa\s*points|\b(?:cliente|client|customer|huésped|guest)\b|"
    r"\b(?:nómina|nomina|payroll|salario|salary|sueldo|wage|compensaci[oó]n|bonus)\b|"
    r"\b(?:dni|cédula|cedula|pasaporte|passport|tel[eé]fono|phone|email|correo)\b|"
    r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\+?\d{9,15}\b",
    re.IGNORECASE,
)


class MemoryProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    category: Category
    location_id: int | None = Field(default=None, ge=1, le=14)
    subject_key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    fact: str = Field(min_length=12, max_length=400)
    source_quote: str = Field(min_length=8, max_length=300)
    reason: str = Field(min_length=8, max_length=160)
    language: Literal["es", "en"] = "es"

    @field_validator("location_id", mode="before")
    @classmethod
    def numeric_location(cls, value):
        return int(value) if isinstance(value, str) and value.isdecimal() else value

    @model_validator(mode="after")
    def valid_scope(self):
        if self.category == "communication_preference" and self.location_id is not None:
            raise ValueError("La preferencia de comunicación es personal")
        if self.category != "communication_preference" and self.location_id is None:
            raise ValueError("Se requiere un local confirmado")
        if any(FORBIDDEN.search(value) for value in
               (self.fact, self.source_quote, self.reason, self.subject_key)):
            raise ValueError("Contenido no memorizable")
        return self


def validate_proposal(candidate: MemoryProposal, question: str) -> MemoryProposal:
    if FORBIDDEN.search(question):
        raise ValueError("La pregunta contiene datos excluidos")
    if candidate.source_quote.casefold() not in question.casefold():
        raise ValueError("La evidencia no procede del mensaje del usuario")
    if candidate.location_id is not None and not re.search(
        rf"\b(?:local|location|sede)\s*#?\s*{candidate.location_id}\b", question, re.IGNORECASE
    ):
        raise ValueError("El ID del local no fue confirmado por el usuario")
    return candidate


def validate_edited_fact(fact: str) -> str:
    fact = " ".join(fact.split())
    if not 12 <= len(fact) <= 400 or FORBIDDEN.search(fact):
        raise ValueError("Edición no memorizable")
    return fact
