import type { CampaignPayload } from "@/lib/api/types";

export interface CampaignFormValues extends Omit<CampaignPayload, "status"> {
  status: CampaignPayload["status"];
}

export type CampaignFormErrors = Partial<Record<keyof CampaignFormValues, string>>;

export const defaultCampaignFormValues: CampaignFormValues = {
  name: "",
  description: "",
  language: "en",
  intro_script: "",
  question_1_text: "",
  question_1_type: "free_text",
  question_2_text: "",
  question_2_type: "free_text",
  question_3_text: "",
  question_3_type: "free_text",
  max_attempts: 3,
  retry_interval_minutes: 15,
  allowed_call_start_local: "09:00",
  allowed_call_end_local: "20:00",
  status: "draft"
};

const QUESTION_TYPES = new Set<CampaignFormValues["question_1_type"]>(["free_text", "numeric", "scale"]);
const LANGUAGES = new Set<CampaignFormValues["language"]>(["en", "it"]);

export function validateCampaignForm(values: CampaignFormValues): CampaignFormErrors {
  const errors: CampaignFormErrors = {};

  if (!values.name.trim()) {
    errors.name = "Name is required.";
  }

  if (!LANGUAGES.has(values.language)) {
    errors.language = "Unsupported language.";
  }

  if (!values.intro_script.trim()) {
    errors.intro_script = "Intro script is required.";
  }

  (["question_1_text", "question_2_text", "question_3_text"] as const).forEach((field) => {
    if (!values[field].trim()) {
      errors[field] = "Question text is required.";
    }
  });

  (["question_1_type", "question_2_type", "question_3_type"] as const).forEach((field) => {
    if (!QUESTION_TYPES.has(values[field])) {
      errors[field] = "Invalid question type.";
    }
  });

  if (values.max_attempts < 1 || values.max_attempts > 5) {
    errors.max_attempts = "Attempts must be between 1 and 5.";
  }

  if (values.retry_interval_minutes < 1) {
    errors.retry_interval_minutes = "Retry interval must be positive.";
  }

  if (values.allowed_call_start_local >= values.allowed_call_end_local) {
    errors.allowed_call_end_local = "End time must be after start time.";
  }

  return errors;
}

export function toCampaignPayload(values: CampaignFormValues): CampaignPayload {
  const { status, ...rest } = values;
  return {
    ...rest,
    status
  };
}