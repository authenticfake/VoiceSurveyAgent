/**
 * Dashboard types for stats and export functionality.
 * REQ-024: Frontend dashboard and export UI
 */

export interface CampaignStats {
  campaign_id: string;
  total_contacts: number;
  completed: number;
  refused: number;
  not_reached: number;
  pending: number;
  in_progress: number;
  excluded: number;
  completion_rate: number;
  refusal_rate: number;
  not_reached_rate: number;
  average_call_duration_seconds: number | null;
  p95_latency_ms: number | null;
  last_updated: string;
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  hour?: number;
  day?: string;
  calls_attempted: number;
  calls_completed: number;
  calls_refused: number;
  calls_not_reached: number;
}

export interface TimeSeriesData {
  campaign_id: string;
  granularity: 'hourly' | 'daily';
  data_points: TimeSeriesDataPoint[];
  start_date: string;
  end_date: string;
}

export interface ExportJob {
  id: string;
  campaign_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  download_url: string | null;
  expires_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExportRequest {
  campaign_id: string;
}

export interface ExportResponse {
  job_id: string;
  status: ExportJob['status'];
  message: string;
}