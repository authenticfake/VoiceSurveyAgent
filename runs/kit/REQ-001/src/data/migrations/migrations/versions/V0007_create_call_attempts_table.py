"""Create call_attempts table.

Revision ID: V0007
Revises: V0006
Create Date: 2025-01-01 00:00:06.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0007"
down_revision: Union[str, None] = "V0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer, nullable=False),
        sa.Column("call_id", sa.String(100), nullable=False, unique=True),
        sa.Column("provider_call_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "outcome",
            postgresql.ENUM(
                "completed", "refused", "no_answer", "busy", "failed",
                name="call_outcome", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("provider_raw_status", sa.String(255), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )
    
    # Indexes for common queries
    op.create_index("ix_call_attempts_contact_id", "call_attempts", ["contact_id"])
    op.create_index("ix_call_attempts_campaign_id", "call_attempts", ["campaign_id"])
    op.create_index("ix_call_attempts_call_id", "call_attempts", ["call_id"])
    op.create_index("ix_call_attempts_started_at", "call_attempts", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_call_attempts_started_at", table_name="call_attempts")
    op.drop_index("ix_call_attempts_call_id", table_name="call_attempts")
    op.drop_index("ix_call_attempts_campaign_id", table_name="call_attempts")
    op.drop_index("ix_call_attempts_contact_id", table_name="call_attempts")
    op.drop_table("call_attempts")