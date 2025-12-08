"""Create contacts table.

Revision ID: V0005
Revises: V0004
Create Date: 2025-01-01 00:00:04.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0005"
down_revision: Union[str, None] = "V0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_contact_id", sa.String(255), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column(
            "preferred_language",
            postgresql.ENUM("en", "it", "auto", name="contact_language", create_type=False),
            nullable=False,
            server_default="auto",
        ),
        sa.Column("has_prior_consent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("do_not_call", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "state",
            postgresql.ENUM(
                "pending", "in_progress", "completed", "refused", "not_reached", "excluded",
                name="contact_state", create_type=False
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempts_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_outcome",
            postgresql.ENUM(
                "completed", "refused", "no_answer", "busy", "failed",
                name="call_outcome", create_type=False
            ),
            nullable=True,
        ),
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
    op.create_index("ix_contacts_campaign_id", "contacts", ["campaign_id"])
    op.create_index("ix_contacts_phone_number", "contacts", ["phone_number"])
    op.create_index("ix_contacts_state", "contacts", ["state"])
    # Composite index for scheduler queries
    op.create_index(
        "ix_contacts_scheduler_lookup",
        "contacts",
        ["campaign_id", "state", "attempts_count", "do_not_call"],
    )


def downgrade() -> None:
    op.drop_index("ix_contacts_scheduler_lookup", table_name="contacts")
    op.drop_index("ix_contacts_state", table_name="contacts")
    op.drop_index("ix_contacts_phone_number", table_name="contacts")
    op.drop_index("ix_contacts_campaign_id", table_name="contacts")
    op.drop_table("contacts")