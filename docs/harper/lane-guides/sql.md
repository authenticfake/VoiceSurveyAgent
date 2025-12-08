## Lane Guide — sql

### Pre-Requirements
- PostgreSQL 15+ installed or accessible
- Alembic for migrations (Python-based)
- psql CLI for direct database access

### Tools

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| migrations | alembic | ≥1.13 | Schema migrations |
| lint | sqlfluff | ≥3.0 | SQL linting |
| tests | pytest | ≥8.0 | Migration tests |
| security | pg_audit | ≥1.7 | Audit logging extension |
| build | docker | ≥24.0 | Container builds |

### CLI Examples

**Local Development:**
```bash
# Create new migration
alembic revision --autogenerate -m "add_campaign_table"

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history

# SQL linting
sqlfluff lint migrations/versions/*.py --dialect postgres

# Direct database access
psql -h localhost -U voicesurvey -d voicesurvey_dev
```

**Containerized:**
```bash
# Run migrations in container
docker-compose exec api alembic upgrade head

# Access database in container
docker-compose exec postgres psql -U voicesurvey -d voicesurvey

# Backup database
docker-compose exec postgres pg_dump -U voicesurvey voicesurvey > backup.sql

# Restore database
docker-compose exec -T postgres psql -U voicesurvey voicesurvey < backup.sql
```

### Default Gate Policy

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| migration_reversible | true | Block if no downgrade |
| foreign_keys_indexed | true | Warn if missing |
| naming_convention | snake_case | Block if violated |
| no_raw_sql_in_code | true | Block if found |

**Gate Check Script:**
```bash
#!/bin/bash
set -e

echo "Running SQL gate checks..."

# Check all migrations have downgrade
for file in migrations/versions/*.py; do
    if ! grep -q "def downgrade" "$file"; then
        echo "ERROR: $file missing downgrade function"
        exit 1
    fi
done

# SQL linting
sqlfluff lint migrations/versions/*.py --dialect postgres

# Test migrations up and down
alembic upgrade head
alembic downgrade base
alembic upgrade head

echo "All SQL gates passed!"
```

### Enterprise Runner Notes

**Database Naming Conventions:**
```python
# migrations/env.py
from sqlalchemy import MetaData

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=naming_convention)
```

**RDS Configuration:**
```yaml
# terraform/rds.tf (reference)
resource "aws_db_instance" "voicesurvey" {
  identifier           = "voicesurvey-db"
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  storage_encrypted    = true
  
  db_name              = "voicesurvey"
  username             = "voicesurvey_admin"
  
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  deletion_protection    = true
  skip_final_snapshot    = false
  
  performance_insights_enabled = true
  
  tags = {
    Environment = "production"
    Project     = "voicesurvey"
  }
}
```

### TECH_CONSTRAINTS Integration

**Connection Pooling:**
```python
# app/shared/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

**Encryption at Rest:**
- RDS encryption enabled via AWS KMS
- Backup encryption automatic with RDS encryption

**Audit Logging:**
```sql
-- Enable pg_audit extension
CREATE EXTENSION IF NOT EXISTS pgaudit;

-- Configure audit logging
ALTER SYSTEM SET pgaudit.log = 'write, ddl';
ALTER SYSTEM SET pgaudit.log_catalog = off;
SELECT pg_reload_conf();
```

### Schema Overview

```sql
-- Core tables (from SPEC data model)
-- Users, Campaigns, Contacts, ExclusionListEntry
-- CallAttempt, SurveyResponse, Event
-- EmailNotification, EmailTemplate, ProviderConfig
-- TranscriptSnippet (optional)

-- Key indexes
CREATE INDEX ix_contacts_campaign_state ON contacts(campaign_id, state);
CREATE INDEX ix_contacts_phone ON contacts(phone_number);
CREATE INDEX ix_call_attempts_contact ON call_attempts(contact_id);
CREATE INDEX ix_call_attempts_campaign ON call_attempts(campaign_id);
CREATE INDEX ix_events_campaign ON events(campaign_id);
CREATE INDEX ix_events_created ON events(created_at);