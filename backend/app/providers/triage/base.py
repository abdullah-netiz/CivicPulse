from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class Category(StrEnum):
    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    ROADS = "roads"
    STREETLIGHTS = "streetlights"
    OTHER = "other"


class Priority(StrEnum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TriageResult(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(min_length=1, max_length=140)
    confidence: float = Field(ge=0, le=1)


class TriageProvider(Protocol):
    name: str

    async def triage(self, text: str, location: str) -> TriageResult: ...
