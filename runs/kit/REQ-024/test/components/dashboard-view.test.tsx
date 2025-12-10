/**
 * Tests for DashboardView component.
 * REQ-024: Frontend dashboard and export UI
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DashboardView } from '@/components/dashboard/dashboard-view';
import { useDashboardStore } from '@/store/dashboard-store';
import { useCampaignStore } from '@/store/campaign-store';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock the stores
jest.mock('@/store/dashboard-store');
jest.mock('@/store/campaign-store');

// Mock recharts
jest.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Mock API client for ContactTable
jest.mock('@/lib/api/client', () => ({
  apiClient: {
    get: jest.fn().mockResolvedValue({
      data: {
        items: [],
        pagination: {
          page: 1,
          page_size: 10,
          total_items: 0,
          total_pages: 0,
          has_next: false,
          has_previous: false,
        },
      },
    }),
  },
}));

const mockUseDashboardStore = useDashboardStore as jest.MockedFunction<typeof useDashboardStore>;
const mockUseCampaignStore = useCampaignStore as jest.MockedFunction<typeof useCampaignStore>;

describe('DashboardView', () => {
  const defaultDashboardState = {
    stats: {
      campaign_id: 'test-campaign',
      total_contacts: 100,
      completed: 50,
      refused: 10,
      not_reached: 20,
      pending: 15,
      in_progress: 5,
      excluded: 0,
      completion_rate: 0.5,
      refusal_rate: 0.1,
      not_reached_rate: 0.2,
      average_call_duration_seconds: 90,
      p95_latency_ms: 1100,
      last_updated: '2024-01-15T10:00:00Z',
    },
    isLoadingStats: false,
    statsError: null,
    timeSeries: {
      campaign_id: 'test-campaign',
      granularity: 'hourly' as const,
      data_points: [],
      start_date: '2024-01-15',
      end_date: '2024-01-15',
    },
    isLoadingTimeSeries: false,
    timeSeriesError: null,
    currentExport: null,
    isExporting: false,
    exportError: null,
    autoRefreshEnabled: true,
    lastRefreshed: new Date('2024-01-15T10:00:00Z'),
    fetchStats: jest.fn(),
    fetchTimeSeries: jest.fn(),
    initiateExport: jest.fn(),
    pollExportStatus: jest.fn(),
    downloadExport: jest.fn(),
    setAutoRefresh: jest.fn(),
    clearDashboard: jest.fn(),
  };

  const defaultCampaignState = {
    currentCampaign: {
      id: 'test-campaign',
      name: 'Test Campaign',
      description: 'Test description',
      status: 'running' as const,
      language: 'en' as const,
      intro_script: 'Hello',
      question_1_text: 'Q1',
      question_1_type: 'free_text' as const,
      question_2_text: 'Q2',
      question_2_type: 'numeric' as const,
      question_3_text: 'Q3',
      question_3_type: 'scale' as const,
      max_attempts: 3,
      retry_interval_minutes: 60,
      allowed_call_start_local: '09:00',
      allowed_call_end_local: '18:00',
      email_completed_template_id: null,
      email_refused_template_id: null,
      email_not_reached_template_id: null,
      created_by_user_id: 'user-1',
      created_at: '2024-01-14T09:00:00Z',
      updated_at: '2024-01-15T10:00:00Z',
    },
    isLoadingDetail: false,
    fetchCampaign: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseDashboardStore.mockReturnValue(defaultDashboardState);
    mockUseCampaignStore.mockReturnValue(defaultCampaignState);
  });

  it('renders campaign name and stats', async () => {
    render(<DashboardView campaignId="test-campaign" />);
    
    expect(screen.getByText('Test Campaign')).toBeInTheDocument();
    expect(screen.getByText('Total Contacts')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('shows loading state when campaign is loading', () => {
    mockUseCampaignStore.mockReturnValue({
      ...defaultCampaignState,
      currentCampaign: null,
      isLoadingDetail: true,
    });
    
    render(<DashboardView campaignId="test-campaign" />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('fetches data on mount', () => {
    render(<DashboardView campaignId="test-campaign" />);
    
    expect(defaultCampaignState.fetchCampaign).toHaveBeenCalledWith('test-campaign');
    expect(defaultDashboardState.fetchStats).toHaveBeenCalledWith('test-campaign');
    expect(defaultDashboardState.fetchTimeSeries).toHaveBeenCalledWith('test-campaign', { granularity: 'hourly' });
  });

  it('clears dashboard on unmount', () => {
    const { unmount } = render(<DashboardView campaignId="test-campaign" />);
    
    unmount();
    
    expect(defaultDashboardState.clearDashboard).toHaveBeenCalled();
  });

  it('toggles auto-refresh', () => {
    render(<DashboardView campaignId="test-campaign" />);
    
    const autoRefreshButton = screen.getByText('Auto-refresh: On');
    fireEvent.click(autoRefreshButton);
    
    expect(defaultDashboardState.setAutoRefresh).toHaveBeenCalledWith(false);
  });

  it('triggers manual refresh', () => {
    render(<DashboardView campaignId="test-campaign" />);
    
    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);
    
    expect(defaultDashboardState.fetchStats).toHaveBeenCalledWith('test-campaign');
    expect(defaultDashboardState.fetchTimeSeries).toHaveBeenCalledWith('test-campaign', { granularity: 'hourly' });
  });

  it('shows stats error with retry option', () => {
    mockUseDashboardStore.mockReturnValue({
      ...defaultDashboardState,
      statsError: 'Failed to load stats',
    });
    
    render(<DashboardView campaignId="test-campaign" />);
    
    expect(screen.getByText('Failed to load statistics')).toBeInTheDocument();
    expect(screen.getByText('Failed to load stats')).toBeInTheDocument();
    
    fireEvent.click(screen.getByText('Retry'));
    expect(defaultDashboardState.fetchStats).toHaveBeenCalled();
  });

  it('renders export button', () => {
    render(<DashboardView campaignId="test-campaign" />);
    
    expect(screen.getByText('Export CSV')).toBeInTheDocument();
  });
});