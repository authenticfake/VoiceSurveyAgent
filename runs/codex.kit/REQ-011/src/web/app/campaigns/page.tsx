import { CampaignList } from "@/components/CampaignList";
import { ApiClient } from "@/lib/api/client";

export default async function CampaignsPage() {
  const client = new ApiClient();
  const campaigns = await client.listCampaigns({ page: 1, page_size: 20 });

  return <CampaignList campaigns={campaigns} />;
}