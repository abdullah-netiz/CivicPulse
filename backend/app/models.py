from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.providers.triage.base import Category, Priority


class Status(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Base(DeclarativeBase):
    pass


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (Index("ix_complaints_status_priority", "status", "priority"), Index("ix_complaints_created_at", "created_at"))

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    reporter_contact: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[Category] = mapped_column(Enum(Category, name="category", values_callable=lambda enum: [item.value for item in enum]), nullable=False)
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="priority", values_callable=lambda enum: [item.value for item in enum]), nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status, name="status", values_callable=lambda enum: [item.value for item in enum]), default=Status.OPEN, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(String(140))
    triaged_by: Mapped[str] = mapped_column(String(40), nullable=False)
    triage_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
