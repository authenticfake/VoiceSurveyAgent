export type Role = "admin" | "campaign_manager" | "viewer";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface PaginatedResult<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface Campaign {
  id: string;
  name: string;
  description?: string | null;
  status: "draft" | "scheduled" | "running" | "paused" | "completed" | "cancelled";
  language: "en" | "it";
  intro_script: string;
  question_1_text: string;
  question_1_type: "free_text" | "numeric" | "scale";
  question_2_text: string;
  question_2_type: "free_text" | "numeric" | "scale";
  question_3_text: string;
  question_3_type: "free_text" | "numeric" | "scale";
  max_attempts: number;
  retry_interval_minutes: number;
  allowed_call_start_local: string;
  allowed_call_end_local: string;
  created_at: string;
  updated_at: string;
}

export interface CampaignListQuery {
  status?: Campaign["status"];
  page?: number;
  page_size?: number;
  search?: string;
}

export interface CampaignPayload
  extends Omit<
    Campaign,
    "id" | "created_at" | "updated_at" | "status"
  > {
  status?: Campaign["status"];
}

export interface UploadSummary {
  total_rows: number;
  accepted: number;
  rejected: number;
  sample_errors: Array<{ row: number; reason: string }>;
}

export interface CampaignStats {
  campaign_id: string;
  totals: {
    contacts: number;
    completed: number;
    refused: number;
    not_reached: number;
  };
  attempts_avg: number;
  completion_rate: number;
  refusal_rate: number;
}

export interface ContactListItem {
  id: string;
  external_contact_id?: string | null;
  phone_number: string;
  email?: string | null;
  state: "pending" | "in_progress" | "completed" | "refused" | "not_reached" | "excluded";
  attempts_count: number;
  last_outcome?: string | null;
  last_attempt_at?: string | null;
}

export interface DashboardResponse {
  stats: CampaignStats;
  contacts: PaginatedResult<ContactListItem>;
}