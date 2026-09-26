"""create complaints table"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_complaints"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    category = sa.Enum("water", "electricity", "sanitation", "roads", "streetlights", "other", name="category")
    priority = sa.Enum("high", "normal", "low", name="priority")
    status = sa.Enum("open", "in_progress", "resolved", "rejected", name="status")
    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("reporter_contact", sa.String(length=200), nullable=True),
        sa.Column("category", category, nullable=False),
        sa.Column("priority", priority, nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("ai_summary", sa.String(length=140), nullable=True),
        sa.Column("triaged_by", sa.String(length=40), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(text) >= 10 AND char_length(text) <= 2000", name="ck_complaints_text_length"),
        sa.CheckConstraint("char_length(location) >= 3 AND char_length(location) <= 200", name="ck_complaints_location_length"),
    )
    op.create_index("ix_complaints_status_priority", "complaints", ["status", "priority"])
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_complaints_created_at", table_name="complaints")
    op.drop_index("ix_complaints_status_priority", table_name="complaints")
    op.drop_table("complaints")
    for enum_name in ("status", "priority", "category"):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
