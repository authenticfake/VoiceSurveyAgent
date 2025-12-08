"""Create updated_at triggers.

Revision ID: V0013
Revises: V0012
Create Date: 2025-01-01 00:00:12.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "V0013"
down_revision: Union[str, None] = "V0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Apply triggers to tables with updated_at column
    tables_with_updated_at = [
        "users",
        "campaigns",
        "contacts",
        "email_templates",
        "email_notifications",
        "provider_configs",
    ]
    
    for table in tables_with_updated_at:
        op.execute(f"""
            DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)

def downgrade() -> None:
    tables_with_updated_at = [
        "users",
        "campaigns",
        "contacts",
        "email_templates",
        "email_notifications",
        "provider_configs",
    ]
    
    for table in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")