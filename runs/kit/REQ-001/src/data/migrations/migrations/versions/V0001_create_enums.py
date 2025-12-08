"""Create enum types for all status and type fields.

Revision ID: V0001
Revises: None
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "V0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # User role enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('admin', 'campaign_manager', 'viewer');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Campaign status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE campaign_status AS ENUM (
                'draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Language enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE language_code AS ENUM ('en', 'it');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Question type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE question_type AS ENUM ('free_text', 'numeric', 'scale');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Contact state enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contact_state AS ENUM (
                'pending', 'in_progress', 'completed', 'refused', 'not_reached', 'excluded'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Contact language enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contact_language AS ENUM ('en', 'it', 'auto');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Call outcome enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE call_outcome AS ENUM ('completed', 'refused', 'no_answer', 'busy', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Exclusion source enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE exclusion_source AS ENUM ('import', 'api', 'manual');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Event type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE event_type AS ENUM ('survey.completed', 'survey.refused', 'survey.not_reached');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Email status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE email_status AS ENUM ('pending', 'sent', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Email template type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE email_template_type AS ENUM ('completed', 'refused', 'not_reached');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Provider type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE provider_type AS ENUM ('telephony_api', 'voice_ai_platform');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # LLM provider enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE llm_provider AS ENUM ('openai', 'anthropic', 'azure-openai', 'google');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS llm_provider CASCADE;")
    op.execute("DROP TYPE IF EXISTS provider_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS email_template_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS email_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS event_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS exclusion_source CASCADE;")
    op.execute("DROP TYPE IF EXISTS call_outcome CASCADE;")
    op.execute("DROP TYPE IF EXISTS contact_language CASCADE;")
    op.execute("DROP TYPE IF EXISTS contact_state CASCADE;")
    op.execute("DROP TYPE IF EXISTS question_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS language_code CASCADE;")
    op.execute("DROP TYPE IF EXISTS campaign_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS user_role CASCADE;")