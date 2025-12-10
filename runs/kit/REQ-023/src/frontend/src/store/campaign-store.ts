/**
 * Campaign state management using Zustand.
 * REQ-023: Frontend campaign management UI
 */

import { create } from 'zustand';
import {
  Campaign,
  CampaignCreateRequest,
  CampaignListItem,
  CampaignListResponse,
  CampaignUpdateRequest,
  CampaignValidationResult,
} from '@/types/campaign';
import { CSVUploadResponse, CSVUploadProgress } from '@/types/contact';
import * as campaignApi from '@/lib/api/campaigns';

interface CampaignState {
  // List state
  campaigns: CampaignListItem[];
  pagination: CampaignListResponse['pagination'] | null;
  isLoadingList: boolean;
  listError: string | null;

  // Detail state
  currentCampaign: Campaign | null;
  isLoadingDetail: boolean;
  detailError: string | null;

  // Validation state
  validationResult: CampaignValidationResult | null;
  isValidating: boolean;

  // Upload state
  uploadProgress: CSVUploadProgress;
  uploadResult: CSVUploadResponse | null;

  // Actions
  fetchCampaigns: (params?: campaignApi.CampaignListParams) => Promise<void>;
  fetchCampaign: (id: string) => Promise<void>;
  createCampaign: (data: CampaignCreateRequest) => Promise<Campaign>;
  updateCampaign: (id: string, data: CampaignUpdateRequest) => Promise<Campaign>;
  deleteCampaign: (id: string) => Promise<void>;
  activateCampaign: (id: string) => Promise<Campaign>;
  pauseCampaign: (id: string) => Promise<Campaign>;
  validateCampaign: (id: string) => Promise<CampaignValidationResult>;
  uploadContacts: (campaignId: string, file: File) => Promise<CSVUploadResponse>;
  resetUploadState: () => void;
  clearCurrentCampaign: () => void;
}

const initialUploadProgress: CSVUploadProgress = {
  status: 'idle',
  progress: 0,
  message: '',
};

export const useCampaignStore = create<CampaignState>((set, get) => ({
  // Initial state
  campaigns: [],
  pagination: null,
  isLoadingList: false,
  listError: null,
  currentCampaign: null,
  isLoadingDetail: false,
  detailError: null,
  validationResult: null,
  isValidating: false,
  uploadProgress: initialUploadProgress,
  uploadResult: null,

  // Actions
  fetchCampaigns: async (params = {}) => {
    set({ isLoadingList: true, listError: null });
    try {
      const response = await campaignApi.getCampaigns(params);
      set({
        campaigns: response.items,
        pagination: response.pagination,
        isLoadingList: false,
      });
    } catch (error) {
      set({
        isLoadingList: false,
        listError: error instanceof Error ? error.message : 'Failed to fetch campaigns',
      });
    }
  },

  fetchCampaign: async (id: string) => {
    set({ isLoadingDetail: true, detailError: null });
    try {
      const campaign = await campaignApi.getCampaign(id);
      set({ currentCampaign: campaign, isLoadingDetail: false });
    } catch (error) {
      set({
        isLoadingDetail: false,
        detailError: error instanceof Error ? error.message : 'Failed to fetch campaign',
      });
    }
  },

  createCampaign: async (data: CampaignCreateRequest) => {
    const campaign = await campaignApi.createCampaign(data);
    // Refresh list after creation
    await get().fetchCampaigns();
    return campaign;
  },

  updateCampaign: async (id: string, data: CampaignUpdateRequest) => {
    const campaign = await campaignApi.updateCampaign(id, data);
    set({ currentCampaign: campaign });
    // Refresh list after update
    await get().fetchCampaigns();
    return campaign;
  },

  deleteCampaign: async (id: string) => {
    await campaignApi.deleteCampaign(id);
    // Refresh list after deletion
    await get().fetchCampaigns();
  },

  activateCampaign: async (id: string) => {
    const campaign = await campaignApi.activateCampaign(id);
    set({ currentCampaign: campaign });
    // Refresh list after activation
    await get().fetchCampaigns();
    return campaign;
  },

  pauseCampaign: async (id: string) => {
    const campaign = await campaignApi.pauseCampaign(id);
    set({ currentCampaign: campaign });
    // Refresh list after pause
    await get().fetchCampaigns();
    return campaign;
  },

  validateCampaign: async (id: string) => {
    set({ isValidating: true });
    try {
      const result = await campaignApi.validateCampaign(id);
      set({ validationResult: result, isValidating: false });
      return result;
    } catch (error) {
      set({ isValidating: false });
      throw error;
    }
  },

  uploadContacts: async (campaignId: string, file: File) => {
    set({
      uploadProgress: { status: 'uploading', progress: 0, message: 'Uploading file...' },
      uploadResult: null,
    });

    try {
      const result = await campaignApi.uploadContacts(campaignId, file, (progress) => {
        set({
          uploadProgress: {
            status: progress < 100 ? 'uploading' : 'processing',
            progress,
            message: progress < 100 ? `Uploading: ${progress}%` : 'Processing contacts...',
          },
        });
      });

      set({
        uploadProgress: { status: 'complete', progress: 100, message: 'Upload complete!' },
        uploadResult: result,
      });

      // Refresh campaign to get updated contact count
      await get().fetchCampaign(campaignId);

      return result;
    } catch (error) {
      set({
        uploadProgress: {
          status: 'error',
          progress: 0,
          message: error instanceof Error ? error.message : 'Upload failed',
        },
      });
      throw error;
    }
  },

  resetUploadState: () => {
    set({
      uploadProgress: initialUploadProgress,
      uploadResult: null,
    });
  },

  clearCurrentCampaign: () => {
    set({
      currentCampaign: null,
      validationResult: null,
      uploadResult: null,
      uploadProgress: initialUploadProgress,
    });
  },
}));