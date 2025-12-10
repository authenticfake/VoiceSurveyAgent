/**
 * Create new campaign page.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import { MainLayout } from '@/components/layout';
import { CampaignForm } from '@/components/campaigns';

export default function NewCampaignPage() {
  return (
    <MainLayout>
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Campaign</h1>
        <CampaignForm mode="create" />
      </div>
    </MainLayout>
  );
}