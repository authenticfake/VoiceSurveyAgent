"""Create provider_configs table.

Revision ID: V0011
Revises: V0010
Create Date: 2025-01-01 00:00:10.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0011"
down_revision: Union[str, None] = "V0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_type",
            postgresql.ENUM("telephony_api", "voice_ai_platform", name="provider_type", create_type=False),
            nullable=False,
        ),
        sa.Column("provider_name", sa.String(100), nullable=False),
        sa.Column("outbound_number", sa.String(20), nullable=True),
        sa.Column("max_concurrent_calls", sa.Integer, nullable=False, server_default="5"),
        sa.Column(
            "llm_provider",
            postgresql.ENUM("openai", "anthropic", "azure-openai", "google", name="llm_provider", create_type=False),
            nullable=False,
        ),
        sa.Column("llm_model", sa.String(100), nullable=False),
        sa.Column("recording_retention_days", sa.Integer, nullable=False, server_default="180"),
        sa.Column("transcript_retention_days", sa.Integer, nullable=False, server_default="180"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table("provider_configs")