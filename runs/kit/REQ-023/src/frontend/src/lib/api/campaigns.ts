/**
 * Campaign API functions.
 * REQ-023: Frontend campaign management UI
 */

import { apiClient } from './client';
import {
  Campaign,
  CampaignCreateRequest,
  CampaignListResponse,
  CampaignUpdateRequest,
  CampaignValidationResult,
  StatusTransitionRequest,
} from '@/types/campaign';
import { CSVUploadResponse } from '@/types/contact';

export interface CampaignListParams {
  page?: number;
  page_size?: number;
  status?: string;
}

export async function getCampaigns(params: CampaignListParams = {}): Promise<CampaignListResponse> {
  const response = await apiClient.get<CampaignListResponse>('/api/campaigns', { params });
  return response.data;
}

export async function getCampaign(id: string): Promise<Campaign> {
  const response = await apiClient.get<Campaign>(`/api/campaigns/${id}`);
  return response.data;
}

export async function createCampaign(data: CampaignCreateRequest): Promise<Campaign> {
  const response = await apiClient.post<Campaign>('/api/campaigns', data);
  return response.data;
}

export async function updateCampaign(id: string, data: CampaignUpdateRequest): Promise<Campaign> {
  const response = await apiClient.put<Campaign>(`/api/campaigns/${id}`, data);
  return response.data;
}

export async function deleteCampaign(id: string): Promise<void> {
  await apiClient.delete(`/api/campaigns/${id}`);
}

export async function transitionCampaignStatus(
  id: string,
  data: StatusTransitionRequest
): Promise<Campaign> {
  const response = await apiClient.post<Campaign>(`/api/campaigns/${id}/status`, data);
  return response.data;
}

export async function activateCampaign(id: string): Promise<Campaign> {
  const response = await apiClient.post<Campaign>(`/api/campaigns/${id}/activate`);
  return response.data;
}

export async function pauseCampaign(id: string): Promise<Campaign> {
  const response = await apiClient.post<Campaign>(`/api/campaigns/${id}/pause`);
  return response.data;
}

export async function validateCampaign(id: string): Promise<CampaignValidationResult> {
  const response = await apiClient.get<CampaignValidationResult>(`/api/campaigns/${id}/validate`);
  return response.data;
}

export async function uploadContacts(
  campaignId: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<CSVUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<CSVUploadResponse>(
    `/api/campaigns/${campaignId}/contacts/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    }
  );

  return response.data;
}