/**
 * Dashboard API functions.
 * REQ-024: Frontend dashboard and export UI
 */

import { apiClient } from './client';
import {
  CampaignStats,
  TimeSeriesData,
  ExportJob,
  ExportResponse,
} from '@/types/dashboard';

export interface TimeSeriesParams {
  granularity?: 'hourly' | 'daily';
  start_date?: string;
  end_date?: string;
}

export async function getCampaignStats(campaignId: string): Promise<CampaignStats> {
  const response = await apiClient.get<CampaignStats>(`/api/campaigns/${campaignId}/stats`);
  return response.data;
}

export async function getTimeSeriesData(
  campaignId: string,
  params: TimeSeriesParams = {}
): Promise<TimeSeriesData> {
  const response = await apiClient.get<TimeSeriesData>(
    `/api/campaigns/${campaignId}/stats/timeseries`,
    { params }
  );
  return response.data;
}

export async function initiateExport(campaignId: string): Promise<ExportResponse> {
  const response = await apiClient.post<ExportResponse>(
    `/api/campaigns/${campaignId}/export`
  );
  return response.data;
}

export async function getExportStatus(jobId: string): Promise<ExportJob> {
  const response = await apiClient.get<ExportJob>(`/api/exports/${jobId}`);
  return response.data;
}

export async function downloadExport(downloadUrl: string): Promise<Blob> {
  const response = await apiClient.get(downloadUrl, {
    responseType: 'blob',
  });
  return response.data;
}