## Lane Guide — sql

### Tools

- tests: Database integration tests using pytest with a temporary Postgres instance or container.
- lint: SQLFluff or similar for raw SQL if used in migrations or views.
- types: SQLAlchemy type hints validated via mypy plugins where applicable.
- security: Ensure least-privilege database roles and parameterized queries through ORM to prevent injection.
- build: Alembic migrations managed through CLI, executed in CI and deployment pipelines.

### CLI Examples

- Local:
  - Run migrations: `alembic upgrade head`
  - Downgrade: `alembic downgrade -1`
  - Generate migration: `alembic revision --autogenerate -m "init schema"`
- Containerized:
  - Use docker-compose or Kubernetes Job to run migrations against dev or staging Postgres.
  - Example: `docker run voicesurveyagent-api alembic upgrade head`

### Default Gate Policy

- min coverage: schema-related code paths and migrations exercised in tests where practical.
- max criticals: no critical database misconfigurations such as missing encryption or public write access.
- required checks: migrations must apply cleanly on empty and existing databases, and rollbacks tested for non-production.

### Enterprise Runner Notes

- SonarQube: not typically applied to migration scripts; focus on application code.
- Jenkins or GitHub Actions: dedicated migration job before deploying new application versions.
- Artifacts: store migration logs and database schema snapshots for auditing and rollback planning.

### TECH_CONSTRAINTS integration

- air-gap: Postgres runs within private subnets; migration jobs must execute from trusted networks only.
- registries: container images for database tooling sourced from internal registries when required.
- secrets: database credentials retrieved from AWS Secrets Manager or injected via environment, not stored in migration configs.