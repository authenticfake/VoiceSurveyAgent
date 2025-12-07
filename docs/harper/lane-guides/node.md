## Lane Guide — node

### Tools

- tests: Jest or Vitest for unit and integration tests of React and Next.js components.
- lint: ESLint with TypeScript support and organization presets, integrated with Prettier for formatting.
- types: TypeScript strict mode enabled, using `tsc --noEmit` in CI for type checking.
- security: npm or pnpm audit in CI, plus Trivy or Snyk scans on built images.
- build: Next.js build or React build using `next build` or `npm run build` with environment-specific configuration.

### CLI Examples

- Local:
  - Install: `npm install` or `pnpm install`
  - Run dev server: `npm run dev`
  - Tests: `npm test` or `npm run test`
  - Lint: `npm run lint`
- Containerized:
  - Build: `docker build -f Dockerfile.web -t voicesurveyagent-web .`
  - Run: `docker run -p 3000:3000 voicesurveyagent-web`
  - Tests in container: `docker run voicesurveyagent-web npm test`

### Default Gate Policy

- min coverage: 75% line coverage for frontend components and pages.
- max criticals: 0 critical vulnerabilities from npm audit or container scans.
- required checks: tests, lint, type-check, and build must pass before merge or deployment.

### Enterprise Runner Notes

- SonarQube: disabled by default but can be added for JS/TS quality tracking later.
- Jenkins or GitLab: can mirror GitHub Actions workflow steps, focusing on `test`, `lint`, `type-check`, `build` jobs.
- Artifacts: store production build artifacts and coverage reports in artifact storage for traceability.

### TECH_CONSTRAINTS integration

- air-gap: configure Node.js registries to use internal mirrors for npm packages when direct internet access is unavailable.
- registries: npm registry may be overridden to corporate proxy; lockfiles should be committed for reproducible installs.
- secrets: frontend uses runtime configuration injected from environment at build or via server-side rendering components; no secrets in client bundle.