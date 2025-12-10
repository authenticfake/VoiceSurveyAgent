/**
 * Tests for ContactTable component.
 * REQ-024: Frontend dashboard and export UI
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ContactTable } from '@/components/dashboard/contact-table';
import { apiClient } from '@/lib/api/client';

// Mock the API client
jest.mock('@/lib/api/client', () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

const mockContactsResponse = {
  data: {
    items: [
      {
        id: 'contact-1',
        campaign_id: 'campaign-1',
        external_contact_id: 'EXT-001',
        phone_number: '+1234567890',
        email: 'test@example.com',
        preferred_language: 'en',
        has_prior_consent: true,
        do_not_call: false,
        state: 'completed',
        attempts_count: 2,
        last_attempt_at: '2024-01-15T10:30:00Z',
        last_outcome: 'completed',
        created_at: '2024-01-14T09:00:00Z',
        updated_at: '2024-01-15T10:30:00Z',
      },
      {
        id: 'contact-2',
        campaign_id: 'campaign-1',
        external_contact_id: null,
        phone_number: '+0987654321',
        email: null,
        preferred_language: 'it',
        has_prior_consent: false,
        do_not_call: false,
        state: 'pending',
        attempts_count: 0,
        last_attempt_at: null,
        last_outcome: null,
        created_at: '2024-01-14T09:00:00Z',
        updated_at: '2024-01-14T09:00:00Z',
      },
    ],
    pagination: {
      page: 1,
      page_size: 10,
      total_items: 2,
      total_pages: 1,
      has_next: false,
      has_previous: false,
    },
  },
};

describe('ContactTable', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiClient.get.mockResolvedValue(mockContactsResponse);
  });

  it('renders loading state initially', () => {
    render(<ContactTable campaignId="campaign-1" />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders contacts after loading', async () => {
    render(<ContactTable campaignId="campaign-1" />);
    
    await waitFor(() => {
      expect(screen.getByText('+1234567890')).toBeInTheDocument();
    });
    
    expect(screen.getByText('+0987654321')).toBeInTheDocument();
    expect(screen.getByText('EXT-001')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    mockApiClient.get.mockRejectedValue(new Error('Network error'));
    
    render(<ContactTable campaignId="campaign-1" />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load contacts')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('filters contacts by outcome', async () => {
    render(<ContactTable campaignId="campaign-1" />);
    
    await waitFor(() => {
      expect(screen.getByText('+1234567890')).toBeInTheDocument();
    });
    
    // Change filter
    const filterSelect = screen.getByDisplayValue('All Outcomes');
    fireEvent.change(filterSelect, { target: { value: 'completed' } });
    
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/campaigns/campaign-1/contacts',
        expect.objectContaining({
          params: expect.objectContaining({ state: 'completed' }),
        })
      );
    });
  });

  it('handles pagination', async () => {
    const paginatedResponse = {
      data: {
        ...mockContactsResponse.data,
        pagination: {
          ...mockContactsResponse.data.pagination,
          total_items: 25,
          total_pages: 3,
          has_next: true,
        },
      },
    };
    mockApiClient.get.mockResolvedValue(paginatedResponse);
    
    render(<ContactTable campaignId="campaign-1" />);
    
    await waitFor(() => {
      expect(screen.getByText('Showing 1 to 10 of 25 contacts')).toBeInTheDocument();
    });
    
    // Click next page
    fireEvent.click(screen.getByText('Next'));
    
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/campaigns/campaign-1/contacts',
        expect.objectContaining({
          params: expect.objectContaining({ page: 2 }),
        })
      );
    });
  });

  it('changes page size', async () => {
    render(<ContactTable campaignId="campaign-1" />);
    
    await waitFor(() => {
      expect(screen.getByText('+1234567890')).toBeInTheDocument();
    });
    
    // Change page size
    const pageSizeSelect = screen.getByDisplayValue('10 per page');
    fireEvent.change(pageSizeSelect, { target: { value: '25' } });
    
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/campaigns/campaign-1/contacts',
        expect.objectContaining({
          params: expect.objectContaining({ page_size: 25 }),
        })
      );
    });
  });

  it('refreshes data when refresh button is clicked', async () => {
    render(<ContactTable campaignId="campaign-1" />);
    
    await waitFor(() => {
      expect(screen.getByText('+1234567890')).toBeInTheDocument();
    });
    
    // Clear mock calls
    mockApiClient.get.mockClear();
    
    // Click refresh
    const refreshButton = screen.getByRole('button', { name: '' }); // RefreshCw icon button
    fireEvent.click(refreshButton);
    
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalled();
    });
  });
});