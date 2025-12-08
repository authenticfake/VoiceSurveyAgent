## Lane Guide — ci

### Tools

- tests: Execute backend and frontend test suites as CI jobs using GitHub Actions runners.
- lint: Run ruff, ESLint, and other linters as separate jobs or stages.
- types: mypy and TypeScript compilers run as dedicated type-check jobs.
- security: Trivy or Snyk scans of dependencies and built images as part of CI.
- build: Docker builds for API and frontend, pushing to container registry on successful checks.

### CLI Examples

- Local:
  - Simulate CI steps with `make ci` or equivalent script that runs tests, lint, and type checks.
- Containerized:
  - Use CI runners with Docker-in-Docker or BuildKit to build and scan images.

### Default Gate Policy

- min coverage: 80% for backend, 75% for frontend per TECH_CONSTRAINTS.
- max criticals: 0 critical vulnerabilities allowed; builds fail when exceeded.
- required checks: tests, lint, type-checks, security scans, and build steps must succeed before merging to protected branches.

### Enterprise Runner Notes

- SonarQube: configured as disabled currently; can be plugged in later with project keys.
- Jenkins: alternative CI system; pipelines should mirror GitHub Actions workflow for organizations using Jenkins.
- Artifacts: coverage reports, security scan outputs, and build logs uploaded as CI artifacts and optionally forwarded to observability platforms.

### TECH_CONSTRAINTS integration

- air-gap: CI runners must have controlled egress, caching dependencies locally or via mirrored registries.
- registries: pushes to internal container registry must be authenticated via CI secrets or service principals.
- secrets: CI secrets managed through GitHub Actions secrets or equivalent, never hard-coded in workflows.