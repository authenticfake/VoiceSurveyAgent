"""Create transcript_snippets table.

Revision ID: V0012
Revises: V0011
Create Date: 2025-01-01 00:00:11.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "V0012"
down_revision: Union[str, None] = "V0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "transcript_snippets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "call_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("transcript_text", sa.Text, nullable=False),
        sa.Column(
            "language",
            postgresql.ENUM("en", "it", name="language_code", create_type=False),
            nullable=False,
            server_default="en",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    op.create_index("idx_transcript_snippets_call_attempt_id", "transcript_snippets", ["call_attempt_id"])

def downgrade() -> None:
    op.drop_index("idx_transcript_snippets_call_attempt_id", table_name="transcript_snippets")
    op.drop_table("transcript_snippets")