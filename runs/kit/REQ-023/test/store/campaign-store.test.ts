/**
 * Campaign store tests.
 * REQ-023: Frontend campaign management UI
 */

import { act, renderHook } from '@testing-library/react';
import { useCampaignStore } from '@/store/campaign-store';
import * as campaignApi from '@/lib/api/campaigns';

// Mock the API module
jest.mock('@/lib/api/campaigns');

const mockCampaignApi = campaignApi as jest.Mocked<typeof campaignApi>;

const mockCampaign = {
  id: '1',
  name: 'Test Campaign',
  description: 'Test description',
  status: 'draft' as const,
  language: 'en' as const,
  intro_script: null,
  question_1_text: null,
  question_1_type: null,
  question_2_text: null,
  question_2_type: null,
  question_3_text: null,
  question_3_type: null,
  max_attempts: 3,
  retry_interval_minutes: 60,
  allowed_call_start_local: '09:00',
  allowed_call_end_local: '20:00',
  email_completed_template_id: null,
  email_refused_template_id: null,
  email_not_reached_template_id: null,
  created_by_user_id: 'user-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('useCampaignStore', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset store state
    const { result } = renderHook(() => useCampaignStore());
    act(() => {
      result.current.clearCurrentCampaign();
    });
  });

  describe('fetchCampaigns', () => {
    it('fetches campaigns successfully', async () => {
      const mockResponse = {
        items: [{ ...mockCampaign, contact_count: 100 }],
        pagination: {
          page: 1,
          page_size: 10,
          total_items: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      };
      mockCampaignApi.getCampaigns.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useCampaignStore());

      await act(async () => {
        await result.current.fetchCampaigns();
      });

      expect(result.current.campaigns).toHaveLength(1);
      expect(result.current.campaigns[0].name).toBe('Test Campaign');
      expect(result.current.isLoadingList).toBe(false);
      expect(result.current.listError).toBeNull();
    });

    it('handles fetch error', async () => {
      mockCampaignApi.getCampaigns.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useCampaignStore());

      await act(async () => {
        await result.current.fetchCampaigns();
      });

      expect(result.current.campaigns).toHaveLength(0);
      expect(result.current.listError).toBe('Network error');
    });
  });

  describe('fetchCampaign', () => {
    it('fetches single campaign successfully', async () => {
      mockCampaignApi.getCampaign.mockResolvedValue(mockCampaign);

      const { result } = renderHook(() => useCampaignStore());

      await act(async () => {
        await result.current.fetchCampaign('1');
      });

      expect(result.current.currentCampaign).toEqual(mockCampaign);
      expect(result.current.isLoadingDetail).toBe(false);
    });
  });

  describe('createCampaign', () => {
    it('creates campaign and refreshes list', async () => {
      mockCampaignApi.createCampaign.mockResolvedValue(mockCampaign);
      mockCampaignApi.getCampaigns.mockResolvedValue({
        items: [{ ...mockCampaign, contact_count: 0 }],
        pagination: {
          page: 1,
          page_size: 10,
          total_items: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      });

      const { result } = renderHook(() => useCampaignStore());

      let createdCampaign;
      await act(async () => {
        createdCampaign = await result.current.createCampaign({ name: 'New Campaign' });
      });

      expect(createdCampaign).toEqual(mockCampaign);
      expect(mockCampaignApi.getCampaigns).toHaveBeenCalled();
    });
  });

  describe('activateCampaign', () => {
    it('activates campaign and updates state', async () => {
      const activatedCampaign = { ...mockCampaign, status: 'running' as const };
      mockCampaignApi.activateCampaign.mockResolvedValue(activatedCampaign);
      mockCampaignApi.getCampaigns.mockResolvedValue({
        items: [],
        pagination: {
          page: 1,
          page_size: 10,
          total_items: 0,
          total_pages: 0,
          has_next: false,
          has_previous: false,
        },
      });

      const { result } = renderHook(() => useCampaignStore());

      await act(async () => {
        await result.current.activateCampaign('1');
      });

      expect(result.current.currentCampaign?.status).toBe('running');
    });
  });

  describe('uploadContacts', () => {
    it('uploads contacts and updates progress', async () => {
      const mockUploadResult = {
        campaign_id: '1',
        total_rows: 100,
        accepted_rows: 95,
        rejected_rows: 5,
        acceptance_rate: 0.95,
        errors: [],
      };
      mockCampaignApi.uploadContacts.mockResolvedValue(mockUploadResult);
      mockCampaignApi.getCampaign.mockResolvedValue(mockCampaign);

      const { result } = renderHook(() => useCampaignStore());

      const file = new File(['phone_number\n+1234567890'], 'contacts.csv', { type: 'text/csv' });

      await act(async () => {
        await result.current.uploadContacts('1', file);
      });

      expect(result.current.uploadResult).toEqual(mockUploadResult);
      expect(result.current.uploadProgress.status).toBe('complete');
    });

    it('handles upload error', async () => {
      mockCampaignApi.uploadContacts.mockRejectedValue(new Error('Upload failed'));

      const { result } = renderHook(() => useCampaignStore());

      const file = new File(['invalid'], 'contacts.csv', { type: 'text/csv' });

      await act(async () => {
        try {
          await result.current.uploadContacts('1', file);
        } catch (e) {
          // Expected error
        }
      });

      expect(result.current.uploadProgress.status).toBe('error');
      expect(result.current.uploadProgress.message).toBe('Upload failed');
    });
  });

  describe('resetUploadState', () => {
    it('resets upload state to initial values', () => {
      const { result } = renderHook(() => useCampaignStore());

      act(() => {
        result.current.resetUploadState();
      });

      expect(result.current.uploadProgress).toEqual({
        status: 'idle',
        progress: 0,
        message: '',
      });
      expect(result.current.uploadResult).toBeNull();
    });
  });
});

Now let me create the documentation and CI files: