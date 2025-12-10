/**
 * CampaignList component tests.
 * REQ-023: Frontend campaign management UI
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CampaignList } from '@/components/campaigns/campaign-list';
import { useCampaignStore } from '@/store/campaign-store';

// Mock the store
jest.mock('@/store/campaign-store');

const mockUseCampaignStore = useCampaignStore as jest.MockedFunction<typeof useCampaignStore>;

const mockCampaigns = [
  {
    id: '1',
    name: 'Test Campaign 1',
    status: 'draft' as const,
    language: 'en' as const,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    contact_count: 100,
  },
  {
    id: '2',
    name: 'Test Campaign 2',
    status: 'running' as const,
    language: 'it' as const,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    contact_count: 200,
  },
];

const mockPagination = {
  page: 1,
  page_size: 10,
  total_items: 2,
  total_pages: 1,
  has_next: false,
  has_previous: false,
};

describe('CampaignList', () => {
  const mockFetchCampaigns = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseCampaignStore.mockReturnValue({
      campaigns: mockCampaigns,
      pagination: mockPagination,
      isLoadingList: false,
      listError: null,
      fetchCampaigns: mockFetchCampaigns,
      currentCampaign: null,
      isLoadingDetail: false,
      detailError: null,
      validationResult: null,
      isValidating: false,
      uploadProgress: { status: 'idle', progress: 0, message: '' },
      uploadResult: null,
      fetchCampaign: jest.fn(),
      createCampaign: jest.fn(),
      updateCampaign: jest.fn(),
      deleteCampaign: jest.fn(),
      activateCampaign: jest.fn(),
      pauseCampaign: jest.fn(),
      validateCampaign: jest.fn(),
      uploadContacts: jest.fn(),
      resetUploadState: jest.fn(),
      clearCurrentCampaign: jest.fn(),
    });
  });

  it('renders campaign list', () => {
    render(<CampaignList />);
    expect(screen.getByText('Test Campaign 1')).toBeInTheDocument();
    expect(screen.getByText('Test Campaign 2')).toBeInTheDocument();
  });

  it('displays status badges', () => {
    render(<CampaignList />);
    expect(screen.getByText('Draft')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('displays contact counts', () => {
    render(<CampaignList />);
    expect(screen.getByText('100 contacts')).toBeInTheDocument();
    expect(screen.getByText('200 contacts')).toBeInTheDocument();
  });

  it('shows loading spinner when loading', () => {
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      campaigns: [],
      isLoadingList: true,
    });
    render(<CampaignList />);
    expect(screen.getByLabelText('Loading')).toBeInTheDocument();
  });

  it('shows error message when there is an error', () => {
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      listError: 'Failed to load campaigns',
    });
    render(<CampaignList />);
    expect(screen.getByText('Failed to load campaigns')).toBeInTheDocument();
  });

  it('shows empty state when no campaigns', () => {
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      campaigns: [],
      pagination: null,
    });
    render(<CampaignList />);
    expect(screen.getByText('No campaigns found')).toBeInTheDocument();
  });

  it('calls fetchCampaigns on mount', () => {
    render(<CampaignList />);
    expect(mockFetchCampaigns).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      status: undefined,
    });
  });

  it('filters by status', () => {
    render(<CampaignList />);
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'running' } });
    expect(mockFetchCampaigns).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      status: 'running',
    });
  });

  it('refreshes list when refresh button clicked', () => {
    render(<CampaignList />);
    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);
    expect(mockFetchCampaigns).toHaveBeenCalled();
  });
});