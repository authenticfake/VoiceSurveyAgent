/**
 * Campaign detail component.
 * REQ-023: Frontend campaign management UI
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Edit, Play, Pause, Upload, Trash2 } from 'lucide-react';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Spinner,
  StatusBadge,
  Alert,
  Modal,
} from '@/components/ui';
import { CSVUploadDropzone } from './csv-upload-dropzone';
import { useCampaignStore } from '@/store/campaign-store';
import { formatDate, formatTime } from '@/lib/utils';

interface CampaignDetailProps {
  campaignId: string;
}

export function CampaignDetail({ campaignId }: CampaignDetailProps) {
  const router = useRouter();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isPerformingAction, setIsPerformingAction] = useState(false);

  const {
    currentCampaign,
    isLoadingDetail,
    detailError,
    validationResult,
    isValidating,
    fetchCampaign,
    activateCampaign,
    pauseCampaign,
    validateCampaign,
    deleteCampaign,
    clearCurrentCampaign,
  } = useCampaignStore();

  useEffect(() => {
    fetchCampaign(campaignId);
    return () => clearCurrentCampaign();
  }, [campaignId, fetchCampaign, clearCurrentCampaign]);

  const handleBack = () => {
    router.push('/campaigns');
  };

  const handleEdit = () => {
    router.push(`/campaigns/${campaignId}/edit`);
  };

  const handleActivate = async () => {
    setActionError(null);
    setIsPerformingAction(true);
    try {
      // First validate
      const validation = await validateCampaign(campaignId);
      if (!validation.is_valid) {
        setActionError(
          `Cannot activate: ${validation.errors.map((e) => e.message).join(', ')}`
        );
        return;
      }
      await activateCampaign(campaignId);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to activate campaign');
    } finally {
      setIsPerformingAction(false);
    }
  };

  const handlePause = async () => {
    setActionError(null);
    setIsPerformingAction(true);
    try {
      await pauseCampaign(campaignId);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to pause campaign');
    } finally {
      setIsPerformingAction(false);
    }
  };

  const handleDelete = async () => {
    setActionError(null);
    setIsPerformingAction(true);
    try {
      await deleteCampaign(campaignId);
      router.push('/campaigns');
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to delete campaign');
      setShowDeleteModal(false);
    } finally {
      setIsPerformingAction(false);
    }
  };

  const handleValidate = async () => {
    setActionError(null);
    try {
      await validateCampaign(campaignId);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to validate campaign');
    }
  };

  if (isLoadingDetail) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (detailError) {
    return (
      <Alert variant="error" title="Error loading campaign">
        {detailError}
      </Alert>
    );
  }

  if (!currentCampaign) {
    return (
      <Alert variant="error" title="Campaign not found">
        The requested campaign could not be found.
      </Alert>
    );
  }

  const campaign = currentCampaign;
  const canEdit = campaign.status === 'draft';
  const canActivate = campaign.status === 'draft' || campaign.status === 'paused';
  const canPause = campaign.status === 'running';
  const canDelete = campaign.status === 'draft' || campaign.status === 'cancelled';
  const canUpload = campaign.status === 'draft';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
              <StatusBadge status={campaign.status} />
            </div>
            {campaign.description && (
              <p className="mt-1 text-sm text-gray-500">{campaign.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {canEdit && (
            <Button variant="outline" onClick={handleEdit}>
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
          )}
          {canUpload && (
            <Button variant="outline" onClick={() => setShowUploadModal(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Upload Contacts
            </Button>
          )}
          {canActivate && (
            <Button
              onClick={handleActivate}
              isLoading={isPerformingAction || isValidating}
            >
              <Play className="h-4 w-4 mr-2" />
              Activate
            </Button>
          )}
          {canPause && (
            <Button
              variant="secondary"
              onClick={handlePause}
              isLoading={isPerformingAction}
            >
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
          )}
          {canDelete && (
            <Button
              variant="danger"
              onClick={() => setShowDeleteModal(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Action Error */}
      {actionError && (
        <Alert variant="error" title="Action failed" onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}

      {/* Validation Result */}
      {validationResult && !validationResult.is_valid && (
        <Alert variant="warning" title="Validation Issues">
          <ul className="list-disc list-inside">
            {validationResult.errors.map((error, index) => (
              <li key={index}>
                <strong>{error.field}:</strong> {error.message}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {validationResult && validationResult.is_valid && (
        <Alert variant="success" title="Validation Passed">
          Campaign is ready to be activated.
        </Alert>
      )}

      {/* Campaign Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500">Language</dt>
                <dd className="text-sm text-gray-900">{campaign.language.toUpperCase()}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="text-sm text-gray-900">{formatDate(campaign.created_at)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                <dd className="text-sm text-gray-900">{formatDate(campaign.updated_at)}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* Call Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Call Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500">Max Attempts</dt>
                <dd className="text-sm text-gray-900">{campaign.max_attempts}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Retry Interval</dt>
                <dd className="text-sm text-gray-900">{campaign.retry_interval_minutes} minutes</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Call Window</dt>
                <dd className="text-sm text-gray-900">
                  {formatTime(campaign.allowed_call_start_local)} - {formatTime(campaign.allowed_call_end_local)}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* Introduction Script */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Introduction Script</CardTitle>
          </CardHeader>
          <CardContent>
            {campaign.intro_script ? (
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{campaign.intro_script}</p>
            ) : (
              <p className="text-sm text-gray-500 italic">No introduction script configured</p>
            )}
          </CardContent>
        </Card>

        {/* Questions */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Survey Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3].map((num) => {
                const text = campaign[`question_${num}_text` as keyof typeof campaign] as string | null;
                const type = campaign[`question_${num}_type` as keyof typeof campaign] as string | null;
                return (
                  <div key={num} className="border-b border-gray-200 pb-4 last:border-0 last:pb-0">
                    <h4 className="font-medium text-gray-700 mb-2">Question {num}</h4>
                    {text ? (
                      <>
                        <p className="text-sm text-gray-900">{text}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          Answer type: {type?.replace('_', ' ')}
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-gray-500 italic">Not configured</p>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Validate Button for Draft */}
      {campaign.status === 'draft' && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={handleValidate} isLoading={isValidating}>
            Validate Campaign Configuration
          </Button>
        </div>
      )}

      {/* Upload Modal */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title="Upload Contacts"
        size="lg"
      >
        <CSVUploadDropzone
          campaignId={campaignId}
          onComplete={() => {
            setShowUploadModal(false);
            fetchCampaign(campaignId);
          }}
        />
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Campaign"
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            Are you sure you want to delete this campaign? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDelete}
              isLoading={isPerformingAction}
            >
              Delete Campaign
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}