"""Create users table.

Revision ID: V0002
Revises: V0001
Create Date: 2025-01-01 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0002"
down_revision: Union[str, None] = "V0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("oidc_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "campaign_manager", "viewer", name="user_role", create_type=False),
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
    
    # Indexes for common queries
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_oidc_sub", "users", ["oidc_sub"])


def downgrade() -> None:
    op.drop_index("ix_users_oidc_sub", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")