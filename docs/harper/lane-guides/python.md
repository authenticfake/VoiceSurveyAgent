## Lane Guide — python

### Pre-Requirements
- Python 3.12+ installed
- Poetry or pip for dependency management
- PostgreSQL 15+ for database
- Redis 7+ for caching
- AWS CLI configured for SQS/Secrets Manager access

### Tools

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| tests | pytest | ≥8.0 | Unit and integration testing |
| tests | pytest-asyncio | ≥0.23 | Async test support |
| tests | pytest-cov | ≥4.1 | Coverage reporting |
| tests | httpx | ≥0.27 | Async HTTP client for API tests |
| lint | ruff | ≥0.4 | Fast Python linter |
| types | mypy | ≥1.10 | Static type checking |
| types | pydantic | ≥2.7 | Runtime validation with type hints |
| security | bandit | ≥1.7 | Security vulnerability scanner |
| security | safety | ≥3.0 | Dependency vulnerability check |
| build | docker | ≥24.0 | Container builds |
| build | poetry | ≥1.8 | Dependency management |

### CLI Examples

**Local Development:**
```bash
# Install dependencies
poetry install

# Run tests with coverage
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Type checking
poetry run mypy app --strict

# Linting
poetry run ruff check app tests
poetry run ruff format --check app tests

# Security scan
poetry run bandit -r app -ll
poetry run safety check

# Run migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload --port 8000
```

**Containerized:**
```bash
# Build image
docker build -t voicesurvey-api:dev -f Dockerfile.api .

# Run tests in container
docker run --rm voicesurvey-api:dev pytest --cov=app --cov-fail-under=80

# Run with docker-compose
docker-compose -f docker-compose.dev.yml up -d

# Run migrations in container
docker-compose exec api alembic upgrade head
```

### Default Gate Policy

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| coverage_min | 80% | Block merge if below |
| max_critical_vulns | 0 | Block merge if any |
| lint_must_be_clean | true | Block merge if errors |
| type_check_strict | true | Block merge if errors |
| bandit_severity | medium | Block on medium+ findings |

**Gate Check Script:**
```bash
#!/bin/bash
set -e

echo "Running gate checks..."

# Tests with coverage
pytest --cov=app --cov-report=xml --cov-fail-under=80

# Type checking
mypy app --strict

# Linting
ruff check app tests
ruff format --check app tests

# Security
bandit -r app -ll -f json -o bandit-report.json
safety check --json > safety-report.json

echo "All gates passed!"
```

### Enterprise Runner Notes

**SonarQube Integration:**
```yaml
# sonar-project.properties
sonar.projectKey=voicesurvey-api
sonar.sources=app
sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.bandit.reportPaths=bandit-report.json
sonar.exclusions=**/migrations/**,**/__pycache__/**
```

**Jenkins Pipeline:**
```groovy
pipeline {
    agent { label 'python-3.12' }
    stages {
        stage('Install') {
            steps {
                sh 'poetry install'
            }
        }
        stage('Test') {
            steps {
                sh 'poetry run pytest --cov=app --cov-report=xml --junitxml=test-results.xml'
            }
            post {
                always {
                    junit 'test-results.xml'
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]
                }
            }
        }
        stage('Quality') {
            parallel {
                stage('Lint') {
                    steps { sh 'poetry run ruff check app tests' }
                }
                stage('Types') {
                    steps { sh 'poetry run mypy app --strict' }
                }
                stage('Security') {
                    steps { sh 'poetry run bandit -r app -ll' }
                }
            }
        }
        stage('SonarQube') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh 'sonar-scanner'
                }
            }
        }
    }
}
```

**GitHub Actions:**
```yaml
name: Python CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install poetry
      - run: poetry install
      - run: poetry run pytest --cov=app --cov-report=xml --cov-fail-under=80
      - run: poetry run mypy app --strict
      - run: poetry run ruff check app tests
      - run: poetry run bandit -r app -ll
```

### TECH_CONSTRAINTS Integration

**Air-Gap Considerations:**
- Use internal PyPI mirror: `poetry config repositories.internal https://pypi.internal.corp/simple`
- Pre-download wheels for offline installation
- Container base images from internal registry

**Internal Registries:**
```toml
# pyproject.toml
[[tool.poetry.source]]
name = "internal"
url = "https://pypi.internal.corp/simple"
priority = "primary"

[[tool.poetry.source]]
name = "PyPI"
url = "https://pypi.org/simple"
priority = "supplemental"
```

**Secrets Management:**
```python
# app/config.py
import boto3
from functools import lru_cache

@lru_cache
def get_secret(secret_name: str) -> dict:
    client = boto3.client('secretsmanager', region_name='eu-central-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
db_creds = get_secret('voicesurvey/db-credentials')
```

**Allowed External Endpoints:**
```python
# app/config.py
ALLOWED_EGRESS = [
    "https://api.openai.com",
    "https://api.anthropic.com",
    "https://api.twilio.com",
]
```

### FastAPI Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI app entry point
├── config.py            # Settings and configuration
├── auth/
│   ├── __init__.py
│   ├── router.py        # Auth endpoints
│   ├── service.py       # OIDC/JWT logic
│   ├── middleware.py    # Auth middleware
│   └── rbac.py          # Role-based access
├── campaigns/
│   ├── __init__.py
│   ├── router.py        # Campaign endpoints
│   ├── service.py       # Business logic
│   ├── repository.py    # Database operations
│   ├── models.py        # SQLAlchemy models
│   └── schemas.py       # Pydantic schemas
├── contacts/
│   └── ...
├── calls/
│   └── ...
├── telephony/
│   └── ...
├── dialogue/
│   └── ...
├── events/
│   └── ...
├── email/
│   └── ...
├── dashboard/
│   └── ...
├── admin/
│   └── ...
└── shared/
    ├── database.py      # DB session management
    ├── exceptions.py    # Custom exceptions
    └── logging.py       # Structured logging