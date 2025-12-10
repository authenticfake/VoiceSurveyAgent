/**
 * Campaign types matching backend API schemas.
 * REQ-023: Frontend campaign management UI
 */

export type CampaignStatus = 
  | 'draft'
  | 'scheduled'
  | 'running'
  | 'paused'
  | 'completed'
  | 'cancelled';

export type CampaignLanguage = 'en' | 'it';

export type QuestionType = 'free_text' | 'numeric' | 'scale';

export interface Campaign {
  id: string;
  name: string;
  description: string | null;
  status: CampaignStatus;
  language: CampaignLanguage;
  intro_script: string | null;
  question_1_text: string | null;
  question_1_type: QuestionType | null;
  question_2_text: string | null;
  question_2_type: QuestionType | null;
  question_3_text: string | null;
  question_3_type: QuestionType | null;
  max_attempts: number;
  retry_interval_minutes: number;
  allowed_call_start_local: string | null;
  allowed_call_end_local: string | null;
  email_completed_template_id: string | null;
  email_refused_template_id: string | null;
  email_not_reached_template_id: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface CampaignListItem {
  id: string;
  name: string;
  status: CampaignStatus;
  language: CampaignLanguage;
  created_at: string;
  updated_at: string;
  contact_count?: number;
}

export interface CampaignListResponse {
  items: CampaignListItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export interface CampaignCreateRequest {
  name: string;
  description?: string | null;
  language?: CampaignLanguage;
  intro_script?: string | null;
  question_1_text?: string | null;
  question_1_type?: QuestionType | null;
  question_2_text?: string | null;
  question_2_type?: QuestionType | null;
  question_3_text?: string | null;
  question_3_type?: QuestionType | null;
  max_attempts?: number;
  retry_interval_minutes?: number;
  allowed_call_start_local?: string | null;
  allowed_call_end_local?: string | null;
}

export interface CampaignUpdateRequest {
  name?: string;
  description?: string | null;
  language?: CampaignLanguage;
  intro_script?: string | null;
  question_1_text?: string | null;
  question_1_type?: QuestionType | null;
  question_2_text?: string | null;
  question_2_type?: QuestionType | null;
  question_3_text?: string | null;
  question_3_type?: QuestionType | null;
  max_attempts?: number;
  retry_interval_minutes?: number;
  allowed_call_start_local?: string | null;
  allowed_call_end_local?: string | null;
}

export interface StatusTransitionRequest {
  target_status: CampaignStatus;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface CampaignValidationResult {
  is_valid: boolean;
  errors: ValidationError[];
}