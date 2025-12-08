import { CsvUploadForm } from "@/components/CsvUploadForm";
import { DashboardStats } from "@/components/DashboardStats";
import { ContactTable } from "@/components/ContactTable";
import { ExportButton } from "@/components/ExportButton";
import { ApiClient } from "@/lib/api/client";

interface Props {
  params: { campaignId: string };
}

export default async function CampaignDashboardPage({ params }: Props) {
  const client = new ApiClient();
  const dashboard = await client.fetchDashboard(params.campaignId, { page: 1, page_size: 25 });

  return (
    <div className="space-y-6">
      <DashboardStats stats={dashboard.stats} />
      <div className="grid gap-6 md:grid-cols-2">
        <CsvUploadForm campaignId={params.campaignId} />
        <ExportButton campaignId={params.campaignId} />
      </div>
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Contacts</h3>
        <ContactTable contacts={dashboard.contacts.data} />
      </section>
    </div>
  );
}