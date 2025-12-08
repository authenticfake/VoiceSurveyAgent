import { CampaignForm } from "@/components/CampaignForm";
import { ApiClient } from "@/lib/api/client";

interface Props {
  params: { campaignId: string };
}

export default async function EditCampaignPage({ params }: Props) {
  const client = new ApiClient();
  const campaign = await client.getCampaign(params.campaignId);

  return <CampaignForm mode="edit" campaignId={campaign.id} initialValues={campaign} />;
}