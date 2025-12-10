/**
 * Main dashboard view component.
 * REQ-024: Frontend dashboard and export UI
 */

'use client';

import React, { useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, RefreshCw, Settings } from 'lucide-react';
import { Button, Spinner, Alert, Card, CardContent } from '@/components/ui';
import { StatsCards } from './stats-cards';
import { TimeSeriesChart } from './time-series-chart';
import { ExportButton } from './export-button';
import { ContactTable } from './contact-table';
import { useDashboardStore } from '@/store/dashboard-store';
import { useCampaignStore } from '@/store/campaign-store';
import { formatDateTime } from '@/lib/utils';

interface DashboardViewProps {
  campaignId: string;
}

const AUTO_REFRESH_INTERVAL = 60000; // 60 seconds

export function DashboardView({ campaignId }: DashboardViewProps) {
  const router = useRouter();
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const {
    stats,
    isLoadingStats,
    statsError,
    timeSeries,
    isLoadingTimeSeries,
    timeSeriesError,
    autoRefreshEnabled,
    lastRefreshed,
    fetchStats,
    fetchTimeSeries,
    setAutoRefresh,
    clearDashboard,
  } = useDashboardStore();

  const { currentCampaign, fetchCampaign, isLoadingDetail } = useCampaignStore();

  // Fetch initial data
  useEffect(() => {
    fetchCampaign(campaignId);
    fetchStats(campaignId);
    fetchTimeSeries(campaignId, { granularity: 'hourly' });

    return () => {
      clearDashboard();
    };
  }, [campaignId, fetchCampaign, fetchStats, fetchTimeSeries, clearDashboard]);

  // Auto-refresh setup
  useEffect(() => {
    if (autoRefreshEnabled) {
      refreshIntervalRef.current = setInterval(() => {
        fetchStats(campaignId);
        fetchTimeSeries(campaignId, { granularity: 'hourly' });
      }, AUTO_REFRESH_INTERVAL);
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [autoRefreshEnabled, campaignId, fetchStats, fetchTimeSeries]);

  const handleManualRefresh = useCallback(() => {
    fetchStats(campaignId);
    fetchTimeSeries(campaignId, { granularity: 'hourly' });
  }, [campaignId, fetchStats, fetchTimeSeries]);

  const handleRetryStats = useCallback(() => {
    fetchStats(campaignId);
  }, [campaignId, fetchStats]);

  const handleRetryTimeSeries = useCallback(() => {
    fetchTimeSeries(campaignId, { granularity: 'hourly' });
  }, [campaignId, fetchTimeSeries]);

  const toggleAutoRefresh = useCallback(() => {
    setAutoRefresh(!autoRefreshEnabled);
  }, [autoRefreshEnabled, setAutoRefresh]);

  if (isLoadingDetail && !currentCampaign) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push('/campaigns')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Campaigns
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {currentCampaign?.name || 'Campaign Dashboard'}
            </h1>
            {lastRefreshed && (
              <p className="text-sm text-gray-500">
                Last updated: {formatDateTime(lastRefreshed)}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={autoRefreshEnabled ? 'primary' : 'secondary'}
            size="sm"
            onClick={toggleAutoRefresh}
          >
            <Settings className="h-4 w-4 mr-2" />
            Auto-refresh: {autoRefreshEnabled ? 'On' : 'Off'}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleManualRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {currentCampaign && (
            <ExportButton
              campaignId={campaignId}
              campaignName={currentCampaign.name}
            />
          )}
        </div>
      </div>

      {/* Stats Error */}
      {statsError && (
        <Alert variant="error" title="Failed to load statistics">
          {statsError}
          <button
            onClick={handleRetryStats}
            className="ml-2 text-sm underline hover:no-underline"
          >
            Retry
          </button>
        </Alert>
      )}

      {/* Stats Cards */}
      <StatsCards stats={stats} isLoading={isLoadingStats} />

      {/* Time Series Chart */}
      <TimeSeriesChart
        data={timeSeries}
        isLoading={isLoadingTimeSeries}
        error={timeSeriesError}
        onRetry={handleRetryTimeSeries}
      />

      {/* Contact Table */}
      <ContactTable campaignId={campaignId} />
    </div>
  );
}