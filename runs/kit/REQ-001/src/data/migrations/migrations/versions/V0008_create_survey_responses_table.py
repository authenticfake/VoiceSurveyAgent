"""Create survey_responses table.

Revision ID: V0008
Revises: V0007
Create Date: 2025-01-01 00:00:07.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0008"
down_revision: Union[str, None] = "V0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "survey_responses",
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
        sa.Column(
            "call_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("q1_answer", sa.Text, nullable=True),
        sa.Column("q2_answer", sa.Text, nullable=True),
        sa.Column("q3_answer", sa.Text, nullable=True),
        sa.Column("q1_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("q2_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("q3_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    
    # Unique constraint: one response per contact per campaign
    op.create_unique_constraint(
        "uq_survey_responses_contact_campaign",
        "survey_responses",
        ["contact_id", "campaign_id"],
    )
    
    # Indexes for common queries
    op.create_index("ix_survey_responses_contact_id", "survey_responses", ["contact_id"])
    op.create_index("ix_survey_responses_campaign_id", "survey_responses", ["campaign_id"])
    op.create_index("ix_survey_responses_call_attempt_id", "survey_responses", ["call_attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_survey_responses_call_attempt_id", table_name="survey_responses")
    op.drop_index("ix_survey_responses_campaign_id", table_name="survey_responses")
    op.drop_index("ix_survey_responses_contact_id", table_name="survey_responses")
    op.drop_constraint("uq_survey_responses_contact_campaign", "survey_responses", type_="unique")
    op.drop_table("survey_responses")