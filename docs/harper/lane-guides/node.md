## Lane Guide — node

### Pre-Requirements
- Node.js 20+ LTS installed
- npm 10+ or pnpm 8+ for package management
- TypeScript 5.4+ for type safety

### Tools

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| tests | vitest | ≥1.6 | Unit and component testing |
| tests | @testing-library/react | ≥15.0 | React component testing |
| tests | playwright | ≥1.44 | E2E testing |
| lint | eslint | ≥9.0 | JavaScript/TypeScript linter |
| lint | prettier | ≥3.2 | Code formatting |
| types | typescript | ≥5.4 | Static type checking |
| security | npm audit | built-in | Dependency vulnerability check |
| security | snyk | ≥1.1200 | Advanced security scanning |
| build | next | ≥14.2 | React framework with SSR |
| build | docker | ≥24.0 | Container builds |

### CLI Examples

**Local Development:**
```bash
# Install dependencies
npm install

# Run tests with coverage
npm run test -- --coverage --coverage.thresholds.lines=75

# Type checking
npm run typecheck

# Linting
npm run lint
npm run format:check

# Security scan
npm audit --audit-level=high
npx snyk test

# Build
npm run build

# Start development server
npm run dev
```

**Containerized:**
```bash
# Build image
docker build -t voicesurvey-ui:dev -f Dockerfile.ui .

# Run tests in container
docker run --rm voicesurvey-ui:dev npm run test -- --coverage

# Run with docker-compose
docker-compose -f docker-compose.dev.yml up -d frontend

# E2E tests
docker-compose exec frontend npx playwright test
```

### Default Gate Policy

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| coverage_min | 75% | Block merge if below |
| max_critical_vulns | 0 | Block merge if any |
| lint_must_be_clean | true | Block merge if errors |
| type_check_strict | true | Block merge if errors |
| bundle_size_limit | 500KB | Warn if exceeded |

**Gate Check Script:**
```bash
#!/bin/bash
set -e

echo "Running gate checks..."

# Tests with coverage
npm run test -- --coverage --coverage.thresholds.lines=75

# Type checking
npm run typecheck

# Linting
npm run lint
npm run format:check

# Security
npm audit --audit-level=high

# Build check
npm run build

echo "All gates passed!"
```

### Enterprise Runner Notes

**SonarQube Integration:**
```properties
# sonar-project.properties
sonar.projectKey=voicesurvey-ui
sonar.sources=src
sonar.tests=src
sonar.test.inclusions=**/*.test.ts,**/*.test.tsx
sonar.typescript.lcov.reportPaths=coverage/lcov.info
sonar.exclusions=**/node_modules/**,**/*.config.*
```

**Jenkins Pipeline:**
```groovy
pipeline {
    agent { label 'node-20' }
    stages {
        stage('Install') {
            steps {
                sh 'npm ci'
            }
        }
        stage('Test') {
            steps {
                sh 'npm run test -- --coverage --reporter=junit --outputFile=test-results.xml'
            }
            post {
                always {
                    junit 'test-results.xml'
                    publishCoverage adapters: [istanbulCoberturaAdapter('coverage/cobertura-coverage.xml')]
                }
            }
        }
        stage('Quality') {
            parallel {
                stage('Lint') {
                    steps { sh 'npm run lint' }
                }
                stage('Types') {
                    steps { sh 'npm run typecheck' }
                }
                stage('Security') {
                    steps { sh 'npm audit --audit-level=high' }
                }
            }
        }
        stage('Build') {
            steps {
                sh 'npm run build'
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
name: Frontend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test -- --coverage --coverage.thresholds.lines=75
      - run: npm run typecheck
      - run: npm run lint
      - run: npm audit --audit-level=high
      - run: npm run build
```

### TECH_CONSTRAINTS Integration

**Air-Gap Considerations:**
- Use internal npm registry: `npm config set registry https://npm.internal.corp`
- Pre-download packages for offline installation
- Container base images from internal registry

**Internal Registries:**
```ini
# .npmrc
registry=https://npm.internal.corp
@company:registry=https://npm.internal.corp
//npm.internal.corp/:_authToken=${NPM_TOKEN}
```

**Environment Configuration:**
```typescript
// src/config/env.ts
export const config = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  oidcAuthority: process.env.NEXT_PUBLIC_OIDC_AUTHORITY,
  oidcClientId: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID,
};
```

**Allowed External Endpoints:**
- API calls only to internal backend
- No direct external API calls from frontend

### Next.js Project Structure

```
src/
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page
│   ├── campaigns/
│   │   ├── page.tsx         # Campaign list
│   │   ├── [id]/
│   │   │   ├── page.tsx     # Campaign detail
│   │   │   └── edit/
│   │   │       └── page.tsx # Campaign edit
│   │   └── new/
│   │       └── page.tsx     # Create campaign
│   ├── dashboard/
│   │   └── [id]/
│   │       └── page.tsx     # Campaign dashboard
│   └── admin/
│       └── page.tsx         # Admin settings
├── components/
│   ├── ui/                  # Shared UI components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Table.tsx
│   │   └── ...
│   ├── campaigns/           # Campaign-specific components
│   │   ├── CampaignForm.tsx
│   │   ├── CampaignList.tsx
│   │   └── CSVUpload.tsx
│   └── dashboard/           # Dashboard components
│       ├── StatsCard.tsx
│       ├── TimeSeriesChart.tsx
│       └── ContactTable.tsx
├── hooks/
│   ├── useCampaigns.ts
│   ├── useContacts.ts
│   └── useAuth.ts
├── lib/
│   ├── api.ts               # API client
│   ├── auth.ts              # Auth utilities
│   └── utils.ts             # Shared utilities
├── types/
│   ├── campaign.ts
│   ├── contact.ts
│   └── api.ts
└── config/
    └── env.ts               # Environment config