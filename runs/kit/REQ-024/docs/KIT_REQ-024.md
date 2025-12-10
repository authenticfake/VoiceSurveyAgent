# KIT Documentation - REQ-024: Frontend Dashboard and Export UI

## Summary

REQ-024 implements the frontend dashboard and export UI for the VoiceSurvey Agent application. This includes visualization of campaign statistics, time-series charts for call activity, contact tables with filtering, and CSV export functionality with async job handling.

## Acceptance Criteria Coverage

| Criterion | Implementation | Status |
|-----------|---------------|--------|
| Dashboard shows completion/refusal/not_reached percentages | `StatsCards` component displays all metrics with percentages | ✅ |
| Time-series chart for call activity | `TimeSeriesChart` using Recharts with hourly/daily granularity | ✅ |
| Export button triggers async job | `ExportButton` with job initiation and status polling | ✅ |
| Stats refresh automatically every 60 seconds | `DashboardView` with auto-refresh interval | ✅ |
| Error states with retry options | All components have error handling with retry buttons | ✅ |

## Architecture

### Component Hierarchy

DashboardView
├── StatsCards
│   └── StatCard (x6)
├── TimeSeriesChart
│   └── Recharts LineChart
├── ExportButton
└── ContactTable
    └── Pagination controls

### State Management

typescript
// Dashboard Store (Zustand)
interface DashboardState {
  stats: CampaignStats | null;
  timeSeries: TimeSeriesData | null;
  currentExport: ExportJob | null;
  autoRefreshEnabled: boolean;
  lastRefreshed: Date | null;
  // ... loading and error states
}

### API Integration

typescript
// Dashboard API functions
getCampaignStats(campaignId: string): Promise<CampaignStats>
getTimeSeriesData(campaignId: string, params?: TimeSeriesParams): Promise<TimeSeriesData>
initiateExport(campaignId: string): Promise<ExportResponse>
getExportStatus(jobId: string): Promise<ExportJob>
downloadExport(downloadUrl: string): Promise<Blob>

## Key Features

### 1. Statistics Dashboard
- Total contacts with pending/in-progress breakdown
- Completed, refused, not_reached counts with percentages
- Average call duration and P95 latency metrics
- Loading skeletons during data fetch

### 2. Time Series Visualization
- Line chart with 4 metrics (attempted, completed, refused, not_reached)
- Hourly or daily granularity
- Responsive container
- Empty state handling

### 3. Export Functionality
- Async job initiation
- Status polling every 2 seconds
- Download trigger with filename generation
- Error handling with retry

### 4. Contact Table
- Paginated display (10/25/50 per page)
- Outcome filtering
- Manual refresh
- Responsive design

### 5. Auto-Refresh
- 60-second interval
- Toggle control
- Last updated timestamp
- Cleanup on unmount

## File Structure

runs/kit/REQ-024/
├── src/frontend/src/
│   ├── types/
│   │   └── dashboard.ts           # Type definitions
│   ├── lib/api/
│   │   └── dashboard.ts           # API functions
│   ├── store/
│   │   └── dashboard-store.ts     # Zustand store
│   ├── components/dashboard/
│   │   ├── index.ts               # Exports
│   │   ├── dashboard-view.tsx     # Main container
│   │   ├── stats-cards.tsx        # Metrics grid
│   │   ├── time-series-chart.tsx  # Line chart
│   │   ├── export-button.tsx      # Export control
│   │   └── contact-table.tsx      # Data table
│   └── app/dashboard/[id]/
│       └── page.tsx               # Route page
├── test/
│   ├── components/                # Component tests
│   ├── store/                     # Store tests
│   └── setup.ts                   # Test configuration
├── ci/
│   ├── LTC.json                   # Test contract
│   └── HOWTO.md                   # Execution guide
└── docs/
    ├── KIT_REQ-024.md             # This file
    └── README_REQ-024.md          # Quick reference

## Dependencies

### From REQ-023 (Shared)
- UI components (Card, Button, Alert, Badge, Spinner, Select)
- API client configuration
- Utility functions (formatDate, formatDateTime, formatPercentage)
- Campaign store and types
- Layout components

### New Dependencies
- recharts (2.x) - Chart visualization
- Additional Lucide icons

## Testing Strategy

### Unit Tests
- Component rendering with various states
- Store actions and state updates
- API function mocking

### Integration Tests
- Data flow from API to components
- User interactions (filtering, pagination, export)
- Auto-refresh behavior

### Test Coverage
- Target: 75% minimum
- Focus on business logic and user interactions

## Performance Considerations

1. **Stats Caching**: 60-second TTL aligns with auto-refresh
2. **Pagination**: Server-side for contact table
3. **Chart Optimization**: Memoized data transformation
4. **Cleanup**: Proper interval and subscription cleanup

## Security

- RBAC enforcement via backend API
- No sensitive data in client state
- Secure download URL handling

## Future Enhancements

1. Date range selector for time series
2. Additional chart types (bar, pie)
3. Real-time WebSocket updates
4. Export format options (Excel, PDF)
5. Dashboard customization/widgets