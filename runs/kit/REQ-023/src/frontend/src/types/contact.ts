/**
 * Contact types matching backend API schemas.
 * REQ-023: Frontend campaign management UI
 */

export type ContactState = 
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'refused'
  | 'not_reached'
  | 'excluded';

export type ContactLanguage = 'en' | 'it' | 'auto';

export interface Contact {
  id: string;
  campaign_id: string;
  external_contact_id: string | null;
  phone_number: string;
  email: string | null;
  preferred_language: ContactLanguage;
  has_prior_consent: boolean;
  do_not_call: boolean;
  state: ContactState;
  attempts_count: number;
  last_attempt_at: string | null;
  last_outcome: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactListResponse {
  items: Contact[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export interface CSVRowError {
  line_number: number;
  field: string;
  error: string;
  value: string | null;
}

export interface CSVUploadResponse {
  campaign_id: string;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  acceptance_rate: number;
  errors: CSVRowError[];
}

export interface CSVUploadProgress {
  status: 'idle' | 'uploading' | 'processing' | 'complete' | 'error';
  progress: number;
  message: string;
}