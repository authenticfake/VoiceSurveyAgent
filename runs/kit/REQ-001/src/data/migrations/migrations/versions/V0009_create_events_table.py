"""Create events table.

Revision ID: V0009
Revises: V0008
Create Date: 2025-01-01 00:00:08.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0009"
down_revision: Union[str, None] = "V0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_type",
            postgresql.ENUM(
                "survey.completed", "survey.refused", "survey.not_reached",
                name="event_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "call_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payload", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    op.create_index("idx_events_event_type", "events", ["event_type"])
    op.create_index("idx_events_campaign_id", "events", ["campaign_id"])
    op.create_index("idx_events_contact_id", "events", ["contact_id"])
    op.create_index("idx_events_call_attempt_id", "events", ["call_attempt_id"])
    op.create_index("idx_events_created_at", "events", ["created_at"])

def downgrade() -> None:
    op.drop_index("idx_events_created_at", table_name="events")
    op.drop_index("idx_events_call_attempt_id", table_name="events")
    op.drop_index("idx_events_contact_id", table_name="events")
    op.drop_index("idx_events_campaign_id", table_name="events")
    op.drop_index("idx_events_event_type", table_name="events")
    op.drop_table("events")