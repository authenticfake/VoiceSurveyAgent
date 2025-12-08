# REQ-001: Database Schema and Migrations — Execution Guide

## Prerequisites

### Required Software
- Python 3.12+
- PostgreSQL 15+
- pip or Poetry for dependency management

### Environment Setup

1. **Create and activate virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

2. **Install dependencies:**
```bash
pip install -r runs/kit/REQ-001/requirements.txt
```

3. **Set environment variables:**
```bash
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=voicesurveyagent_test
```

Or create a `.env` file:
```
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=voicesurveyagent_test
```

### Database Setup

1. **Create test database:**
```bash
createdb voicesurveyagent_test
```

Or via psql:
```sql
CREATE DATABASE voicesurveyagent_test;
```

## Running Tests

### All Tests
```bash
pytest runs/kit/REQ-001/test -v
```

### Unit Tests Only (Models)
```bash
pytest runs/kit/REQ-001/test/test_models.py -v
```

### Migration Tests Only
```bash
pytest runs/kit/REQ-001/test/test_migrations.py -v
```

### With Coverage
```bash
pytest runs/kit/REQ-001/test --cov=runs/kit/REQ-001/src --cov-report=term-missing
```

## Running Migrations

### Set PYTHONPATH
```bash
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-001/src"
```

### Upgrade to Latest
```bash
cd runs/kit/REQ-001/src/data/migrations
alembic upgrade head
```

### Downgrade One Version
```bash
alembic downgrade -1
```

### Downgrade to Base
```bash
alembic downgrade base
```

### Check Current Version
```bash
alembic current
```

### View Migration History
```bash
alembic history
```

## Linting and Type Checking

### Ruff Linting
```bash
ruff check runs/kit/REQ-001/src runs/kit/REQ-001/test
```

### Ruff Auto-fix
```bash
ruff check runs/kit/REQ-001/src runs/kit/REQ-001/test --fix
```

### MyPy Type Checking
```bash
mypy runs/kit/REQ-001/src --ignore-missing-imports
```

## Docker-based Testing

### Using Docker Compose for PostgreSQL
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: voicesurveyagent_test
    ports:
      - "5432:5432"
```

```bash
docker-compose -f docker-compose.test.yml up -d
pytest runs/kit/REQ-001/test -v
docker-compose -f docker-compose.test.yml down
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure PYTHONPATH includes the src directory:
```bash
export PYTHONPATH="${PYTHONPATH}:runs/kit/REQ-001/src"
```

### Database Connection Issues
1. Verify PostgreSQL is running
2. Check environment variables are set correctly
3. Ensure the test database exists

### Migration Conflicts
If migrations fail due to existing objects:
```bash
# Reset the database
dropdb voicesurveyagent_test
createdb voicesurveyagent_test
alembic upgrade head
```

## CI/CD Integration

### GitHub Actions
The LTC.json file defines test cases that can be executed in CI:
```yaml
- name: Run Tests
  run: |
    pip install -r runs/kit/REQ-001/requirements.txt
    pytest runs/kit/REQ-001/test -v --junitxml=reports/junit.xml
```

### Jenkins
```groovy
stage('Test REQ-001') {
    steps {
        sh 'pip install -r runs/kit/REQ-001/requirements.txt'
        sh 'pytest runs/kit/REQ-001/test -v --junitxml=reports/junit.xml'
    }
}
```

## Artifacts

- **Migrations**: `runs/kit/REQ-001/src/data/migrations/migrations/versions/`
- **Models**: `runs/kit/REQ-001/src/app/shared/models/`
- **Tests**: `runs/kit/REQ-001/test/`
- **Reports**: `reports/` (generated during test runs)