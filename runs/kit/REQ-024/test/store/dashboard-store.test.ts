/**
 * Tests for dashboard store.
 * REQ-024: Frontend dashboard and export UI
 */

import { useDashboardStore } from '@/store/dashboard-store';
import * as dashboardApi from '@/lib/api/dashboard';

// Mock the API module
jest.mock('@/lib/api/dashboard');

const mockDashboardApi = dashboardApi as jest.Mocked<typeof dashboardApi>;

describe('useDashboardStore', () => {
  beforeEach(() => {
    // Reset store state
    useDashboardStore.setState({
      stats: null,
      isLoadingStats: false,
      statsError: null,
      timeSeries: null,
      isLoadingTimeSeries: false,
      timeSeriesError: null,
      currentExport: null,
      isExporting: false,
      exportError: null,
      autoRefreshEnabled: true,
      lastRefreshed: null,
    });
    jest.clearAllMocks();
  });

  describe('fetchStats', () => {
    it('fetches stats successfully', async () => {
      const mockStats = {
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
      };
      
      mockDashboardApi.getCampaignStats.mockResolvedValue(mockStats);
      
      await useDashboardStore.getState().fetchStats('test-campaign');
      
      const state = useDashboardStore.getState();
      expect(state.stats).toEqual(mockStats);
      expect(state.isLoadingStats).toBe(false);
      expect(state.statsError).toBeNull();
      expect(state.lastRefreshed).toBeInstanceOf(Date);
    });

    it('handles fetch stats error', async () => {
      mockDashboardApi.getCampaignStats.mockRejectedValue(new Error('Network error'));
      
      await useDashboardStore.getState().fetchStats('test-campaign');
      
      const state = useDashboardStore.getState();
      expect(state.stats).toBeNull();
      expect(state.isLoadingStats).toBe(false);
      expect(state.statsError).toBe('Network error');
    });
  });

  describe('fetchTimeSeries', () => {
    it('fetches time series successfully', async () => {
      const mockTimeSeries = {
        campaign_id: 'test-campaign',
        granularity: 'hourly' as const,
        data_points: [
          {
            timestamp: '2024-01-15T09:00:00Z',
            hour: 9,
            calls_attempted: 50,
            calls_completed: 25,
            calls_refused: 5,
            calls_not_reached: 10,
          },
        ],
        start_date: '2024-01-15',
        end_date: '2024-01-15',
      };
      
      mockDashboardApi.getTimeSeriesData.mockResolvedValue(mockTimeSeries);
      
      await useDashboardStore.getState().fetchTimeSeries('test-campaign', { granularity: 'hourly' });
      
      const state = useDashboardStore.getState();
      expect(state.timeSeries).toEqual(mockTimeSeries);
      expect(state.isLoadingTimeSeries).toBe(false);
      expect(state.timeSeriesError).toBeNull();
    });

    it('handles fetch time series error', async () => {
      mockDashboardApi.getTimeSeriesData.mockRejectedValue(new Error('Failed to fetch'));
      
      await useDashboardStore.getState().fetchTimeSeries('test-campaign');
      
      const state = useDashboardStore.getState();
      expect(state.timeSeries).toBeNull();
      expect(state.isLoadingTimeSeries).toBe(false);
      expect(state.timeSeriesError).toBe('Failed to fetch');
    });
  });

  describe('initiateExport', () => {
    it('initiates export successfully', async () => {
      mockDashboardApi.initiateExport.mockResolvedValue({
        job_id: 'job-123',
        status: 'pending',
        message: 'Export started',
      });
      
      const jobId = await useDashboardStore.getState().initiateExport('test-campaign');
      
      expect(jobId).toBe('job-123');
      const state = useDashboardStore.getState();
      expect(state.isExporting).toBe(false);
      expect(state.exportError).toBeNull();
    });

    it('handles export initiation error', async () => {
      mockDashboardApi.initiateExport.mockRejectedValue(new Error('Export failed'));
      
      await expect(
        useDashboardStore.getState().initiateExport('test-campaign')
      ).rejects.toThrow('Export failed');
      
      const state = useDashboardStore.getState();
      expect(state.isExporting).toBe(false);
      expect(state.exportError).toBe('Export failed');
    });
  });

  describe('pollExportStatus', () => {
    it('polls export status and updates state', async () => {
      const mockExportJob = {
        id: 'job-123',
        campaign_id: 'test-campaign',
        status: 'completed' as const,
        download_url: 'https://example.com/download',
        expires_at: '2024-01-16T10:00:00Z',
        error_message: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:05:00Z',
      };
      
      mockDashboardApi.getExportStatus.mockResolvedValue(mockExportJob);
      
      const result = await useDashboardStore.getState().pollExportStatus('job-123');
      
      expect(result).toEqual(mockExportJob);
      expect(useDashboardStore.getState().currentExport).toEqual(mockExportJob);
    });
  });

  describe('setAutoRefresh', () => {
    it('toggles auto refresh', () => {
      expect(useDashboardStore.getState().autoRefreshEnabled).toBe(true);
      
      useDashboardStore.getState().setAutoRefresh(false);
      expect(useDashboardStore.getState().autoRefreshEnabled).toBe(false);
      
      useDashboardStore.getState().setAutoRefresh(true);
      expect(useDashboardStore.getState().autoRefreshEnabled).toBe(true);
    });
  });

  describe('clearDashboard', () => {
    it('clears all dashboard state', async () => {
      // Set some state first
      mockDashboardApi.getCampaignStats.mockResolvedValue({
        campaign_id: 'test',
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
      });
      
      await useDashboardStore.getState().fetchStats('test');
      
      // Clear
      useDashboardStore.getState().clearDashboard();
      
      const state = useDashboardStore.getState();
      expect(state.stats).toBeNull();
      expect(state.timeSeries).toBeNull();
      expect(state.currentExport).toBeNull();
      expect(state.lastRefreshed).toBeNull();
    });
  });
});