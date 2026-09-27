from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import Status
from app.providers.triage.base import Category, Priority


class ComplaintCreate(BaseModel):
    text: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = Field(default=None, max_length=200)


class ComplaintListResponse(BaseModel):
    items: list["ComplaintResponse"]
    total: int
    page: int
    page_size: int


class StatusUpdateRequest(BaseModel):
    status: Status


class TriageOutcome(BaseModel):
    provider: str
    latency_ms: int
    fallback: bool
    timestamp: datetime


class ProvidersMetaResponse(BaseModel):
    active_provider: str
    recent_outcomes: list[TriageOutcome]


class StatsResponse(BaseModel):
    total: int
    by_category: dict[str, int]
    by_priority: dict[str, int]


class ComplaintResponse(BaseModel):
    id: UUID
    text: str
    location: str
    reporter_contact: str | None
    category: Category
    priority: Priority
    status: str
    ai_summary: str | None
    triaged_by: str
    triage_latency_ms: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
