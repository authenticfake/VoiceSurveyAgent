/**
 * Campaign list component.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, RefreshCw } from 'lucide-react';
import { Button, Card, CardContent, Spinner, StatusBadge, Alert } from '@/components/ui';
import { useCampaignStore } from '@/store/campaign-store';
import { formatDate } from '@/lib/utils';
import { CampaignStatus } from '@/types/campaign';

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'running', label: 'Running' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export function CampaignList() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  
  const {
    campaigns,
    pagination,
    isLoadingList,
    listError,
    fetchCampaigns,
  } = useCampaignStore();

  useEffect(() => {
    fetchCampaigns({
      page: currentPage,
      page_size: 10,
      status: statusFilter || undefined,
    });
  }, [fetchCampaigns, currentPage, statusFilter]);

  const handleRefresh = () => {
    fetchCampaigns({
      page: currentPage,
      page_size: 10,
      status: statusFilter || undefined,
    });
  };

  const handleCreateCampaign = () => {
    router.push('/campaigns/new');
  };

  const handleViewCampaign = (id: string) => {
    router.push(`/campaigns/${id}`);
  };

  if (isLoadingList && campaigns.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your survey campaigns
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoadingList}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoadingList ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={handleCreateCampaign}>
            <Plus className="h-4 w-4 mr-2" />
            New Campaign
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setCurrentPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Error state */}
      {listError && (
        <Alert variant="error" title="Error loading campaigns">
          {listError}
        </Alert>
      )}

      {/* Empty state */}
      {!isLoadingList && campaigns.length === 0 && !listError && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-500 mb-4">No campaigns found</p>
            <Button onClick={handleCreateCampaign}>
              <Plus className="h-4 w-4 mr-2" />
              Create your first campaign
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Campaign list */}
      {campaigns.length > 0 && (
        <div className="space-y-4">
          {campaigns.map((campaign) => (
            <Card
              key={campaign.id}
              className="hover:border-primary-300 cursor-pointer transition-colors"
              onClick={() => handleViewCampaign(campaign.id)}
            >
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-medium text-gray-900 truncate">
                        {campaign.name}
                      </h3>
                      <StatusBadge status={campaign.status} />
                    </div>
                    <div className="mt-1 flex items-center gap-4 text-sm text-gray-500">
                      <span>Language: {campaign.language.toUpperCase()}</span>
                      {campaign.contact_count !== undefined && (
                        <span>{campaign.contact_count} contacts</span>
                      )}
                      <span>Created: {formatDate(campaign.created_at)}</span>
                    </div>
                  </div>
                  <div className="ml-4">
                    <Button variant="ghost" size="sm">
                      View Details →
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-200 pt-4">
          <p className="text-sm text-gray-500">
            Showing {(pagination.page - 1) * pagination.page_size + 1} to{' '}
            {Math.min(pagination.page * pagination.page_size, pagination.total_items)} of{' '}
            {pagination.total_items} campaigns
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!pagination.has_previous}
              onClick={() => setCurrentPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="text-sm text-gray-700">
              Page {pagination.page} of {pagination.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={!pagination.has_next}
              onClick={() => setCurrentPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}