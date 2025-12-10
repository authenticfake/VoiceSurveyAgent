/**
 * Campaigns list page.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import { MainLayout } from '@/components/layout';
import { CampaignList } from '@/components/campaigns';

export default function CampaignsPage() {
  return (
    <MainLayout>
      <CampaignList />
    </MainLayout>
  );
}