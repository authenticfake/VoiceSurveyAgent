"""Create campaigns table.

Revision ID: V0004
Revises: V0003
Create Date: 2025-01-01 00:00:03.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0004"
down_revision: Union[str, None] = "V0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "scheduled", "running", "paused", "completed", "cancelled",
                name="campaign_status", create_type=False
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "language",
            postgresql.ENUM("en", "it", name="language_code", create_type=False),
            nullable=False,
            server_default="en",
        ),
        sa.Column("intro_script", sa.Text, nullable=False),
        sa.Column("question_1_text", sa.Text, nullable=False),
        sa.Column(
            "question_1_type",
            postgresql.ENUM("free_text", "numeric", "scale", name="question_type", create_type=False),
            nullable=False,
        ),
        sa.Column("question_2_text", sa.Text, nullable=False),
        sa.Column(
            "question_2_type",
            postgresql.ENUM("free_text", "numeric", "scale", name="question_type", create_type=False),
            nullable=False,
        ),
        sa.Column("question_3_text", sa.Text, nullable=False),
        sa.Column(
            "question_3_type",
            postgresql.ENUM("free_text", "numeric", "scale", name="question_type", create_type=False),
            nullable=False,
        ),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("retry_interval_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("allowed_call_start_local", sa.Time, nullable=False, server_default="09:00:00"),
        sa.Column("allowed_call_end_local", sa.Time, nullable=False, server_default="20:00:00"),
        sa.Column(
            "email_completed_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "email_refused_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "email_not_reached_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("max_attempts >= 1 AND max_attempts <= 5", name="ck_campaigns_max_attempts"),
    )
    
    op.create_index("idx_campaigns_name", "campaigns", ["name"])
    op.create_index("idx_campaigns_status", "campaigns", ["status"])
    op.create_index("idx_campaigns_created_by", "campaigns", ["created_by_user_id"])
    op.create_index("idx_campaigns_email_completed", "campaigns", ["email_completed_template_id"])
    op.create_index("idx_campaigns_email_refused", "campaigns", ["email_refused_template_id"])
    op.create_index("idx_campaigns_email_not_reached", "campaigns", ["email_not_reached_template_id"])

def downgrade() -> None:
    op.drop_index("idx_campaigns_email_not_reached", table_name="campaigns")
    op.drop_index("idx_campaigns_email_refused", table_name="campaigns")
    op.drop_index("idx_campaigns_email_completed", table_name="campaigns")
    op.drop_index("idx_campaigns_created_by", table_name="campaigns")
    op.drop_index("idx_campaigns_status", table_name="campaigns")
    op.drop_index("idx_campaigns_name", table_name="campaigns")
    op.drop_table("campaigns")