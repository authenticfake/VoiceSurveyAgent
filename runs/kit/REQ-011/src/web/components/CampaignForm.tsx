"use client";

import { useState } from "react";
import type { CampaignFormErrors, CampaignFormValues } from "@/lib/forms/campaign";
import { defaultCampaignFormValues, toCampaignPayload, validateCampaignForm } from "@/lib/forms/campaign";
import { apiClient } from "@/lib/api/client";
import { useRouter } from "next/navigation";
import { RbacGuard } from "@/components/RbacGuard";

interface CampaignFormProps {
  mode: "create" | "edit";
  campaignId?: string;
  initialValues?: Partial<CampaignFormValues>;
}

export function CampaignForm({ mode, campaignId, initialValues = {} }: CampaignFormProps) {
  const router = useRouter();
  const [values, setValues] = useState<CampaignFormValues>({ ...defaultCampaignFormValues, ...initialValues });
  const [errors, setErrors] = useState<CampaignFormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string>();

  const handleChange = (field: keyof CampaignFormValues) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setValues((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const validation = validateCampaignForm(values);
    setErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    setSubmitting(true);
    setServerError(undefined);
    try {
      const payload = toCampaignPayload(values);
      if (mode === "create") {
        await apiClient.createCampaign(payload);
      } else if (campaignId) {
        await apiClient.updateCampaign(campaignId, payload);
      }
      router.push("/campaigns");
      router.refresh();
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Unable to save campaign");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RbacGuard allowed={["admin", "campaign_manager"]} fallback={<p className="text-sm text-red-600">You do not have access to modify campaigns.</p>}>
      <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-slate-200 bg-white p-6 shadow">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            {mode === "create" ? "Create campaign" : "Edit campaign"}
          </h1>
          <p className="text-sm text-slate-600">Configure survey metadata, script, questions, and retry policy.</p>
        </div>

        {serverError ? (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{serverError}</div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Name" error={errors.name}>
            <input className="input" value={values.name} onChange={handleChange("name")} required />
          </Field>
          <Field label="Language" error={errors.language}>
            <select className="input" value={values.language} onChange={handleChange("language")}>
              <option value="en">English</option>
              <option value="it">Italian</option>
            </select>
          </Field>
        </div>

        <Field label="Description">
          <textarea className="input" value={values.description ?? ""} onChange={handleChange("description")} rows={2} />
        </Field>

        <Field label="Intro script" error={errors.intro_script}>
          <textarea className="input" value={values.intro_script} onChange={handleChange("intro_script")} rows={4} required />
        </Field>

        {[1, 2, 3].map((index) => (
          <div key={index} className="grid gap-4 md:grid-cols-2">
            <Field label={`Question ${index}`} error={errors[`question_${index}_text` as keyof CampaignFormErrors]}>
              <textarea
                className="input"
                value={values[`question_${index}_text` as keyof CampaignFormValues] as string}
                onChange={handleChange(`question_${index}_text` as keyof CampaignFormValues)}
                rows={2}
              />
            </Field>
            <Field label="Answer type" error={errors[`question_${index}_type` as keyof CampaignFormErrors]}>
              <select
                className="input"
                value={values[`question_${index}_type` as keyof CampaignFormValues] as string}
                onChange={handleChange(`question_${index}_type` as keyof CampaignFormValues)}
              >
                <option value="free_text">Free text</option>
                <option value="numeric">Numeric</option>
                <option value="scale">Scale</option>
              </select>
            </Field>
          </div>
        ))}

        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Max attempts" error={errors.max_attempts}>
            <input type="number" min={1} max={5} className="input" value={values.max_attempts} onChange={handleChange("max_attempts")} />
          </Field>
          <Field label="Retry interval (minutes)" error={errors.retry_interval_minutes}>
            <input type="number" min={1} className="input" value={values.retry_interval_minutes} onChange={handleChange("retry_interval_minutes")} />
          </Field>
          <Field label="Status">
            <select className="input" value={values.status} onChange={handleChange("status")}>
              <option value="draft">Draft</option>
              <option value="scheduled">Scheduled</option>
              <option value="running">Running</option>
              <option value="paused">Paused</option>
            </select>
          </Field>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Allowed call start (local)" error={errors.allowed_call_start_local}>
            <input type="time" className="input" value={values.allowed_call_start_local} onChange={handleChange("allowed_call_start_local")} />
          </Field>
          <Field label="Allowed call end (local)" error={errors.allowed_call_end_local}>
            <input type="time" className="input" value={values.allowed_call_end_local} onChange={handleChange("allowed_call_end_local")} />
          </Field>
        </div>

        <div className="flex gap-3">
          <button type="submit" disabled={submitting} className="rounded-md bg-brand-500 px-4 py-2 text-white hover:bg-brand-700">
            {submitting ? "Saving..." : mode === "create" ? "Create campaign" : "Save changes"}
          </button>
          {mode === "edit" && campaignId ? (
            <button
              type="button"
              className="rounded-md border border-slate-300 px-4 py-2 text-slate-700"
              onClick={async () => {
                await apiClient.activateCampaign(campaignId);
                router.refresh();
              }}
            >
              Activate
            </button>
          ) : null}
        </div>
      </form>
    </RbacGuard>
  );
}

function Field({
  label,
  children,
  error
}: {
  label: string;
  children: React.ReactNode;
  error?: string;
}) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      <span>{label}</span>
      <div className="mt-1">{children}</div>
      {error ? <p className="mt-1 text-xs text-red-600">{error}</p> : null}
    </label>
  );
}