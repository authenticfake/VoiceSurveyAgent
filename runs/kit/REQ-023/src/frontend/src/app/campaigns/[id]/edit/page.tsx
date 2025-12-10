/**
 * Edit campaign page.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import { useEffect } from 'react';
import { MainLayout } from '@/components/layout';
import { CampaignForm } from '@/components/campaigns';
import { Spinner, Alert } from '@/components/ui';
import { useCampaignStore } from '@/store/campaign-store';

interface EditCampaignPageProps {
  params: {
    id: string;
  };
}

export default function EditCampaignPage({ params }: EditCampaignPageProps) {
  const { currentCampaign, isLoadingDetail, detailError, fetchCampaign, clearCurrentCampaign } = useCampaignStore();

  useEffect(() => {
    fetchCampaign(params.id);
    return () => clearCurrentCampaign();
  }, [params.id, fetchCampaign, clearCurrentCampaign]);

  if (isLoadingDetail) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      </MainLayout>
    );
  }

  if (detailError) {
    return (
      <MainLayout>
        <Alert variant="error" title="Error loading campaign">
          {detailError}
        </Alert>
      </MainLayout>
    );
  }

  if (!currentCampaign) {
    return (
      <MainLayout>
        <Alert variant="error" title="Campaign not found">
          The requested campaign could not be found.
        </Alert>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Edit Campaign</h1>
        <CampaignForm campaign={currentCampaign} mode="edit" />
      </div>
    </MainLayout>
  );
}