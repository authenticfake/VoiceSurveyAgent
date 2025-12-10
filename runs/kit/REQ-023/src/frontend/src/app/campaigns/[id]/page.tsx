/**
 * Campaign detail page.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import { MainLayout } from '@/components/layout';
import { CampaignDetail } from '@/components/campaigns';

interface CampaignPageProps {
  params: {
    id: string;
  };
}

export default function CampaignPage({ params }: CampaignPageProps) {
  return (
    <MainLayout>
      <CampaignDetail campaignId={params.id} />
    </MainLayout>
  );
}