from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.providers.triage.base import Category, Priority


class ComplaintCreate(BaseModel):
    text: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = Field(default=None, max_length=200)


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
