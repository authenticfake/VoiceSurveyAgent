# REQ-024: Frontend Dashboard and Export UI - Execution Guide

## Overview

This REQ implements the frontend dashboard and export UI for the VoiceSurvey Agent application. It provides:
- Dashboard with completion/refusal/not_reached percentages
- Time-series chart for call activity
- Contact table with pagination and outcome filter
- Export button that triggers async job
- Auto-refresh functionality (every 60 seconds)
- Error states with retry options

## Prerequisites

### Required Tools
- Node.js 20+ (LTS recommended)
- npm 10+

### Environment Variables
bash
export NODE_ENV=test
export NEXT_PUBLIC_API_URL=http://localhost:8000

## Local Development Setup

### 1. Install Dependencies
bash
cd runs/kit/REQ-024/src/frontend
npm ci

### 2. Run Development Server
bash
npm run dev

The application will be available at http://localhost:3000

### 3. Run Tests
bash
# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watch

# Run specific test file
npm test -- stats-cards.test.tsx

### 4. Run Linting
bash
npm run lint

### 5. Run Type Checking
bash
npm run type-check

### 6. Build for Production
bash
npm run build

## Test Structure

runs/kit/REQ-024/test/
├── components/
│   ├── stats-cards.test.tsx      # Stats cards component tests
│   ├── time-series-chart.test.tsx # Chart component tests
│   ├── export-button.test.tsx    # Export button tests
│   ├── contact-table.test.tsx    # Contact table tests
│   └── dashboard-view.test.tsx   # Main dashboard view tests
├── store/
│   └── dashboard-store.test.ts   # Zustand store tests
└── setup.ts                      # Test setup and mocks

## Component Architecture

### Dashboard Components
- `DashboardView` - Main container component with auto-refresh logic
- `StatsCards` - Grid of metric cards showing key statistics
- `TimeSeriesChart` - Recharts-based line chart for call activity
- `ExportButton` - Export trigger with status polling
- `ContactTable` - Paginated table with filtering

### State Management
- `useDashboardStore` - Zustand store for dashboard state
- Handles stats, time series, export job state
- Auto-refresh toggle and last refreshed timestamp

### API Integration
- `dashboard.ts` - API functions for stats, time series, and export
- Uses shared `apiClient` from REQ-023

## CI/CD Integration

### GitHub Actions
The LTC.json defines the test cases for CI:
1. `install_dependencies` - npm ci
2. `lint` - ESLint check
3. `type_check` - TypeScript compilation
4. `tests` - Jest with coverage
5. `build` - Next.js production build

### Quality Gates
- Tests must pass
- Coverage minimum: 75%
- No high severity npm audit issues

## Troubleshooting

### Common Issues

#### 1. Module Resolution Errors
Ensure `tsconfig.json` has correct path aliases:
json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}

#### 2. Test Failures with Recharts
Recharts requires mocking in tests due to canvas dependencies:
typescript
jest.mock('recharts', () => ({
  LineChart: ({ children }) => <div>{children}</div>,
  // ... other mocks
}));

#### 3. API Client Not Found
Ensure the API client from REQ-023 is available:
typescript
import { apiClient } from '@/lib/api/client';

#### 4. Store State Persistence Between Tests
Reset store state in beforeEach:
typescript
beforeEach(() => {
  useDashboardStore.setState(initialState);
});

### Environment Issues

#### Node Version
bash
node --version  # Should be 20+

#### npm Cache Issues
bash
npm cache clean --force
rm -rf node_modules
npm ci

## Dependencies

### Production
- react, react-dom (18.x)
- next (14.x)
- recharts (2.x) - Charts
- zustand (4.x) - State management
- axios (1.x) - HTTP client
- lucide-react - Icons
- tailwindcss - Styling

### Development
- typescript (5.x)
- jest, @testing-library/react
- eslint, prettier

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/campaigns/{id}/stats` | GET | Campaign statistics |
| `/api/campaigns/{id}/stats/timeseries` | GET | Time series data |
| `/api/campaigns/{id}/contacts` | GET | Paginated contacts |
| `/api/campaigns/{id}/export` | POST | Initiate export |
| `/api/exports/{jobId}` | GET | Export job status |

## Related REQs

- REQ-017: Campaign dashboard stats API (backend)
- REQ-018: Campaign CSV export (backend)
- REQ-023: Frontend campaign management UI (shared components)