## Lane Guide — python

### Tools

- tests: pytest, pytest-asyncio for async FastAPI endpoints, httpx or starlette test client for API-level tests.
- lint: ruff for linting and import sorting, optionally flake8 or pylint if organization prefers.
- types: mypy with strict mode for core domains, pydantic v2 type hints respected.
- security: bandit for static analysis, dependency scanning via Trivy or Snyk in CI.
- build: Docker images built with multi-stage builds, uv or pip for dependency installation.

### CLI Examples

- Local:
  - Run tests: `pytest`
  - Lint: `ruff check app`
  - Type-check: `mypy app`
  - Run API: `uvicorn app.main:app --reload`
- Containerized:
  - Build: `docker build -t voicesurveyagent-api .`
  - Run: `docker run -p 8000:8000 voicesurveyagent-api`
  - Tests in container: `docker run voicesurveyagent-api pytest`

### Default Gate Policy

- min coverage: 80% line coverage for backend modules under `app`.
- max criticals: 0 critical or high vulnerabilities from scanners blocking merge.
- required checks: tests, lint, types, basic security scan, and image build must succeed before main branch merges.

### Enterprise Runner Notes

- SonarQube: currently disabled per TECH_CONSTRAINTS, can be enabled later with project-specific config.
- Jenkins: not primary CI; GitHub Actions is default, but Jenkins can run the same commands in corporate environments.
- Artifacts: test reports, coverage reports, and security scan results should be uploaded to central storage or CI artifacts for auditing.

### TECH_CONSTRAINTS integration

- air-gap: outbound egress restricted to whitelisted LLM and telephony endpoints; HTTP clients must be configurable via environment.
- registries: use internal container registry for images where required; mirror Python packages if internet access is constrained.
- secrets: integrate with AWS Secrets Manager via environment-injected ARNs or IAM roles, never hard-code credentials.