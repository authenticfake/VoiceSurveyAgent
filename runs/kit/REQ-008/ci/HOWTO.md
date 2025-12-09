# REQ-008: Call Scheduler Service - Execution Guide

## Overview

This document provides instructions for running and testing the call scheduler service implementation for REQ-008.

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+ (running and accessible)
- pip or poetry for dependency management

### Environment Setup

1. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

2. **Set environment variables:**
   ```bash
   export ENVIRONMENT=test
   export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test"
   export OIDC_ISSUER_URL="https://test-idp.example.com"
   export OIDC_CLIENT_ID="test-client-id"
   export OIDC_CLIENT_SECRET="test-client-secret"
   export JWT_SECRET_KEY="test-secret-key-for-jwt-signing-min-32-chars"
   ```

3. **Set PYTHONPATH to include all dependent REQ modules:**
   ```bash
   export PYTHONPATH=runs/kit/REQ-008/src:runs/kit/REQ-007/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
   ```

### Database Setup

1. **Create test database:**
   ```bash
   createdb voicesurvey_test
   ```

2. **Run migrations (from REQ-001):**
   ```bash
   psql -d voicesurvey_test -f runs/kit/REQ-001/src/storage/sql/V0001.up.sql
   ```

## Installation

Install dependencies:
```bash
pip install -r runs/kit/REQ-008/requirements.txt
```

## Running Tests

### Full Test Suite
```bash
pytest runs/kit/REQ-008/test -v --tb=short
```

### With Coverage
```bash
pytest runs/kit/REQ-008/test -v --cov=runs/kit/REQ-008/src --cov-report=term-missing
```

### Specific Test Class
```bash
pytest runs/kit/REQ-008/test/test_scheduler.py::TestCallScheduler -v
```

### Specific Test
```bash
pytest runs/kit/REQ-008/test/test_scheduler.py::TestCallScheduler::test_scheduler_selects_pending_contacts -v
```

## Code Quality Checks

### Linting
```bash
ruff check runs/kit/REQ-008/src runs/kit/REQ-008/test
```

### Type Checking
```bash
mypy runs/kit/REQ-008/src --ignore-missing-imports
```

### Security Scan
```bash
bandit -r runs/kit/REQ-008/src
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure PYTHONPATH includes all dependent modules:
```bash
export PYTHONPATH=runs/kit/REQ-008/src:runs/kit/REQ-007/src:runs/kit/REQ-006/src:runs/kit/REQ-005/src:runs/kit/REQ-004/src:runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
```

### Database Connection Issues
1. Verify PostgreSQL is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Check database exists:
   ```bash
   psql -l | grep voicesurvey_test
   ```

3. Verify connection string format:
   ```
   postgresql+asyncpg://user:password@host:port/database
   ```

### Test Skipping
Tests will skip if DATABASE_URL is not set. This is intentional for CI environments without database access.

## Architecture Notes

### Call Scheduler Flow
1. Scheduler runs every 60 seconds (configurable)
2. Queries for running campaigns
3. For each campaign:
   - Checks if current time is within allowed call window
   - Selects eligible contacts (pending/not_reached, attempts < max)
   - Creates CallAttempt records
   - Updates contact state to in_progress
   - Initiates calls via telephony provider

### Key Components
- `CallScheduler`: Main scheduler service
- `CallAttemptRepository`: Database operations for call attempts
- `TelephonyProviderProtocol`: Interface for telephony providers

### Dependencies
- REQ-001: Database schema (call_attempts table)
- REQ-004: Campaign models
- REQ-005: Contact models
- REQ-006: Contact repository
- REQ-007: Exclusion list (do_not_call flag)

## CI/CD Integration

The LTC.json file defines the test contract for CI runners:
- Install dependencies
- Run linting
- Run type checking
- Run tests

All cases must pass with exit code 0 for the build to succeed.