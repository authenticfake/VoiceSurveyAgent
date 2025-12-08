"use client";

import { useState } from "react";
import type { UploadSummary } from "@/lib/api/types";
import { apiClient } from "@/lib/api/client";
import { RbacGuard } from "@/components/RbacGuard";

interface Props {
  campaignId: string;
}

export function CsvUploadForm({ campaignId }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState<UploadSummary>();
  const [error, setError] = useState<string>();

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(undefined);
    try {
      const response = await apiClient.uploadContacts(campaignId, file);
      setSummary(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <RbacGuard allowed={["admin", "campaign_manager"]} fallback={<p className="text-sm text-slate-500">Only campaign managers can upload contacts.</p>}>
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold">Upload contacts CSV</h3>
        <p className="text-sm text-slate-600">CSV must include phone_number and optional metadata columns.</p>
        <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center">
          <input
            type="file"
            accept=".csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="text-sm text-slate-600"
          />
          <button
            type="button"
            disabled={!file || uploading}
            onClick={handleUpload}
            className="rounded-md bg-brand-500 px-4 py-2 text-sm text-white hover:bg-brand-700"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
        {summary ? (
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="font-semibold text-slate-700">Accepted</dt>
              <dd>{summary.accepted}</dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-700">Rejected</dt>
              <dd>{summary.rejected}</dd>
            </div>
            {summary.sample_errors.length > 0 ? (
              <div className="col-span-2">
                <dt className="font-semibold text-slate-700">Sample errors</dt>
                <dd className="text-xs text-slate-600">
                  {summary.sample_errors.map((err) => `Row ${err.row}: ${err.reason}`).join("; ")}
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </div>
    </RbacGuard>
  );
}