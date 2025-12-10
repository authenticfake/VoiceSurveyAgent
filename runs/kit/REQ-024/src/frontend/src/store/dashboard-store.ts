/**
 * Dashboard state management using Zustand.
 * REQ-024: Frontend dashboard and export UI
 */

import { create } from 'zustand';
import * as dashboardApi from '@/lib/api/dashboard';
import { CampaignStats, TimeSeriesData, ExportJob } from '@/types/dashboard';

interface DashboardState {
  // Stats state
  stats: CampaignStats | null;
  isLoadingStats: boolean;
  statsError: string | null;
  
  // Time series state
  timeSeries: TimeSeriesData | null;
  isLoadingTimeSeries: boolean;
  timeSeriesError: string | null;
  
  // Export state
  currentExport: ExportJob | null;
  isExporting: boolean;
  exportError: string | null;
  
  // Auto-refresh
  autoRefreshEnabled: boolean;
  lastRefreshed: Date | null;
  
  // Actions
  fetchStats: (campaignId: string) => Promise<void>;
  fetchTimeSeries: (campaignId: string, params?: dashboardApi.TimeSeriesParams) => Promise<void>;
  initiateExport: (campaignId: string) => Promise<string>;
  pollExportStatus: (jobId: string) => Promise<ExportJob>;
  downloadExport: (downloadUrl: string, filename: string) => Promise<void>;
  setAutoRefresh: (enabled: boolean) => void;
  clearDashboard: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // Initial state
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

  fetchStats: async (campaignId: string) => {
    set({ isLoadingStats: true, statsError: null });
    try {
      const stats = await dashboardApi.getCampaignStats(campaignId);
      set({ 
        stats, 
        isLoadingStats: false,
        lastRefreshed: new Date(),
      });
    } catch (error) {
      set({
        isLoadingStats: false,
        statsError: error instanceof Error ? error.message : 'Failed to fetch stats',
      });
    }
  },

  fetchTimeSeries: async (campaignId: string, params?: dashboardApi.TimeSeriesParams) => {
    set({ isLoadingTimeSeries: true, timeSeriesError: null });
    try {
      const timeSeries = await dashboardApi.getTimeSeriesData(campaignId, params);
      set({ timeSeries, isLoadingTimeSeries: false });
    } catch (error) {
      set({
        isLoadingTimeSeries: false,
        timeSeriesError: error instanceof Error ? error.message : 'Failed to fetch time series',
      });
    }
  },

  initiateExport: async (campaignId: string) => {
    set({ isExporting: true, exportError: null, currentExport: null });
    try {
      const response = await dashboardApi.initiateExport(campaignId);
      set({ isExporting: false });
      return response.job_id;
    } catch (error) {
      set({
        isExporting: false,
        exportError: error instanceof Error ? error.message : 'Failed to initiate export',
      });
      throw error;
    }
  },

  pollExportStatus: async (jobId: string) => {
    const exportJob = await dashboardApi.getExportStatus(jobId);
    set({ currentExport: exportJob });
    return exportJob;
  },

  downloadExport: async (downloadUrl: string, filename: string) => {
    try {
      const blob = await dashboardApi.downloadExport(downloadUrl);
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      set({
        exportError: error instanceof Error ? error.message : 'Failed to download export',
      });
      throw error;
    }
  },

  setAutoRefresh: (enabled: boolean) => {
    set({ autoRefreshEnabled: enabled });
  },

  clearDashboard: () => {
    set({
      stats: null,
      isLoadingStats: false,
      statsError: null,
      timeSeries: null,
      isLoadingTimeSeries: false,
      timeSeriesError: null,
      currentExport: null,
      isExporting: false,
      exportError: null,
      lastRefreshed: null,
    });
  },
}));