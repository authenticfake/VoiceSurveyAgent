"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api/client";
import { RbacGuard } from "@/components/RbacGuard";

interface Props {
  campaignId: string;
}

export function ExportButton({ campaignId }: Props) {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string>();

  const triggerExport = async () => {
    setExporting(true);
    setError(undefined);
    try {
      const blob = await apiClient.exportContacts(campaignId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `campaign-${campaignId}-export.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <RbacGuard allowed={["admin", "campaign_manager"]} fallback={<p className="text-sm text-slate-500">Exports allowed for campaign managers.</p>}>
      <div className="space-y-2">
        <button
          type="button"
          onClick={triggerExport}
          disabled={exporting}
          className="rounded-md bg-brand-500 px-4 py-2 text-sm text-white hover:bg-brand-700"
        >
          {exporting ? "Preparing export..." : "Download CSV export"}
        </button>
        {error ? <p className="text-xs text-red-600">{error}</p> : null}
      </div>
    </RbacGuard>
  );
}