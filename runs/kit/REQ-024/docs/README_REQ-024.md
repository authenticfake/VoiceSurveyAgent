# REQ-024: Frontend Dashboard and Export UI

## Quick Start

bash
cd runs/kit/REQ-024/src/frontend
npm ci
npm run dev

## Test Commands

bash
npm test                    # Run all tests
npm test -- --coverage      # With coverage
npm run lint               # Lint check
npm run type-check         # Type check
npm run build              # Production build

## Key Components

| Component | Purpose |
|-----------|---------|
| `DashboardView` | Main dashboard container with auto-refresh |
| `StatsCards` | Metrics grid (6 cards) |
| `TimeSeriesChart` | Call activity line chart |
| `ExportButton` | CSV export with status tracking |
| `ContactTable` | Paginated contact list |

## API Endpoints

- `GET /api/campaigns/{id}/stats` - Statistics
- `GET /api/campaigns/{id}/stats/timeseries` - Time series
- `GET /api/campaigns/{id}/contacts` - Contacts
- `POST /api/campaigns/{id}/export` - Start export
- `GET /api/exports/{jobId}` - Export status

## Features

- ✅ Completion/refusal/not_reached percentages
- ✅ Time-series chart for call activity
- ✅ Export button with async job
- ✅ 60-second auto-refresh
- ✅ Error states with retry

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-024**: Frontend dashboard and export UI

### Rationale
REQ-024 is the next open REQ in the plan. It depends on REQ-017 (Campaign dashboard stats API) and REQ-018 (Campaign CSV export), which are marked as in_progress. This REQ implements the frontend visualization layer for the dashboard functionality.

### In Scope
- Dashboard view component with auto-refresh (60 seconds)
- Stats cards showing completion/refusal/not_reached percentages
- Time-series chart for call activity using Recharts
- Export button with async job status polling
- Contact table with pagination and outcome filtering
- Error states with retry options
- Zustand store for dashboard state management
- API integration functions
- Comprehensive test suite

### Out of Scope
- Backend API implementation (covered by REQ-017, REQ-018)
- Real-time WebSocket updates
- Advanced chart customization
- Export format options beyond CSV

### How to Run Tests

bash
# Navigate to frontend directory
cd runs/kit/REQ-024/src/frontend

# Install dependencies
npm ci

# Run tests with coverage
npm test -- --coverage

# Run linting
npm run lint

# Run type checking
npm run type-check

# Build for production
npm run build

### Prerequisites
- Node.js 20+
- npm 10+
- Backend API running at http://localhost:8000 (for integration testing)

### Dependencies and Mocks
- **Recharts**: Mocked in tests to avoid canvas rendering issues
- **API Client**: Mocked using Jest for isolated component testing
- **Zustand Store**: Mocked for component tests, tested directly for store tests
- **ResizeObserver**: Mocked globally for chart container tests

### Product Owner Notes
- Auto-refresh interval set to 60 seconds as per acceptance criteria
- Export polling interval set to 2 seconds for responsive UX
- Contact table supports filtering by all outcome states
- Stats cards show both absolute numbers and percentages
- Time series chart supports hourly granularity (daily can be added)

### RAG Citations
- `runs/kit/REQ-023/src/frontend/src/types/campaign.ts` - Reused campaign types
- `runs/kit/REQ-023/src/frontend/src/types/contact.ts` - Reused contact types
- `runs/kit/REQ-023/src/frontend/src/components/ui/` - Reused UI components
- `runs/kit/REQ-023/src/frontend/src/lib/api/client.ts` - Reused API client
- `runs/kit/REQ-023/src/frontend/src/lib/utils.ts` - Reused utility functions
- `runs/kit/REQ-023/src/frontend/src/store/campaign-store.ts` - Pattern for Zustand store
- `runs/kit/REQ-023/src/frontend/src/components/layout/` - Reused layout components

### Index

json
{
  "index": [
    {
      "req": "REQ-024",
      "src": [
        "runs/kit/REQ-024/src/frontend/src/types/dashboard.ts",
        "runs/kit/REQ-024/src/frontend/src/lib/api/dashboard.ts",
        "runs/kit/REQ-024/src/frontend/src/store/dashboard-store.ts",
        "runs/kit/REQ-024/src/frontend/src/components/dashboard/stats-cards.tsx",
        "runs/kit/REQ-024/src/frontend/src/components/dashboard/time-series-chart.tsx",
        "runs/kit/REQ-024/src/frontend/src/components/dashboard/export-button.tsx",
        "runs/kit/REQ-024/src/frontend/src/components/dashboard/contact-table.tsx",
        "runs/kit/REQ-024/src/frontend/src/components/dashboard/dashboard-view.tsx",
        "runs/kit/REQ-024/src/frontend/src/components/dashboard/index.ts",
        "runs/kit/REQ-024/src/frontend/src/app/dashboard/[id]/page.tsx"
      ],
      "tests": [
        "runs/kit/REQ-024/test/components/stats-cards.test.tsx",
        "runs/kit/REQ-024/test/components/time-series-chart.test.tsx",
        "runs/kit/REQ-024/test/components/export-button.test.tsx",
        "runs/kit/REQ-024/test/components/contact-table.test.tsx",
        "runs/kit/REQ-024/test/components/dashboard-view.test.tsx",
        "runs/kit/REQ-024/test/store/dashboard-store.test.ts",
        "runs/kit/REQ-024/test/setup.ts"
      ]
    }
  ]
}