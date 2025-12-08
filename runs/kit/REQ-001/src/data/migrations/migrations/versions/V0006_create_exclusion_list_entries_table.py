"""Create exclusion_list_entries table.

Revision ID: V0006
Revises: V0005
Create Date: 2025-01-01 00:00:05.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0006"
down_revision: Union[str, None] = "V0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exclusion_list_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(20), nullable=False, unique=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM("import", "api", "manual", name="exclusion_source", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    
    # Index for phone number lookups
    op.create_index("ix_exclusion_list_entries_phone_number", "exclusion_list_entries", ["phone_number"])


def downgrade() -> None:
    op.drop_index("ix_exclusion_list_entries_phone_number", table_name="exclusion_list_entries")
    op.drop_table("exclusion_list_entries")