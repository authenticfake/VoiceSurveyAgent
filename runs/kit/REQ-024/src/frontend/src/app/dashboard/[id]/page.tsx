/**
 * Campaign dashboard page.
 * REQ-024: Frontend dashboard and export UI
 */

'use client';

import { MainLayout } from '@/components/layout';
import { DashboardView } from '@/components/dashboard';

interface DashboardPageProps {
  params: {
    id: string;
  };
}

export default function DashboardPage({ params }: DashboardPageProps) {
  return (
    <MainLayout>
      <DashboardView campaignId={params.id} />
    </MainLayout>
  );
}