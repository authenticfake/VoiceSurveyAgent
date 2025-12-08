"""Create email_templates table.

Revision ID: V0003
Revises: V0002
Create Date: 2025-01-01 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0003"
down_revision: Union[str, None] = "V0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("completed", "refused", "not_reached", name="email_template_type", create_type=False),
            nullable=False,
        ),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text, nullable=False),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column(
            "locale",
            postgresql.ENUM("en", "it", name="language_code", create_type=False),
            nullable=False,
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
    
    # Index for template lookups by type and locale
    op.create_index("ix_email_templates_type_locale", "email_templates", ["type", "locale"])


def downgrade() -> None:
    op.drop_index("ix_email_templates_type_locale", table_name="email_templates")
    op.drop_table("email_templates")