"""Create email_notifications table.

Revision ID: V0010
Revises: V0009
Create Date: 2025-01-01 00:00:09.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0010"
down_revision: Union[str, None] = "V0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "sent", "failed", name="email_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    
    # Indexes for common queries
    op.create_index("ix_email_notifications_event_id", "email_notifications", ["event_id"])
    op.create_index("ix_email_notifications_contact_id", "email_notifications", ["contact_id"])
    op.create_index("ix_email_notifications_campaign_id", "email_notifications", ["campaign_id"])
    op.create_index("ix_email_notifications_status", "email_notifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_email_notifications_status", table_name="email_notifications")
    op.drop_index("ix_email_notifications_campaign_id", table_name="email_notifications")
    op.drop_index("ix_email_notifications_contact_id", table_name="email_notifications")
    op.drop_index("ix_email_notifications_event_id", table_name="email_notifications")
    op.drop_table("email_notifications")