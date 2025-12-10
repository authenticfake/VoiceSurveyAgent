/**
 * CSVUploadDropzone component tests.
 * REQ-023: Frontend campaign management UI
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CSVUploadDropzone } from '@/components/campaigns/csv-upload-dropzone';
import { useCampaignStore } from '@/store/campaign-store';

// Mock the store
jest.mock('@/store/campaign-store');

const mockUseCampaignStore = useCampaignStore as jest.MockedFunction<typeof useCampaignStore>;

describe('CSVUploadDropzone', () => {
  const mockUploadContacts = jest.fn();
  const mockResetUploadState = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseCampaignStore.mockReturnValue({
      campaigns: [],
      pagination: null,
      isLoadingList: false,
      listError: null,
      fetchCampaigns: jest.fn(),
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
      uploadContacts: mockUploadContacts,
      resetUploadState: mockResetUploadState,
      clearCurrentCampaign: jest.fn(),
    });
  });

  it('renders dropzone with instructions', () => {
    render(<CSVUploadDropzone campaignId="1" />);
    expect(screen.getByText(/Drag and drop a CSV file here/)).toBeInTheDocument();
    expect(screen.getByText('Maximum file size: 10MB')).toBeInTheDocument();
  });

  it('shows CSV format help', () => {
    render(<CSVUploadDropzone campaignId="1" />);
    expect(screen.getByText('Expected CSV format:')).toBeInTheDocument();
    expect(screen.getByText(/Required columns: phone_number/)).toBeInTheDocument();
  });

  it('shows upload progress', () => {
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      uploadProgress: { status: 'uploading', progress: 50, message: 'Uploading: 50%' },
    });
    
    render(<CSVUploadDropzone campaignId="1" />);
    expect(screen.getByText('Uploading: 50%')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('shows success result', () => {
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      uploadProgress: { status: 'complete', progress: 100, message: 'Upload complete!' },
      uploadResult: {
        campaign_id: '1',
        total_rows: 100,
        accepted_rows: 95,
        rejected_rows: 5,
        acceptance_rate: 0.95,
        errors: [],
      },
    });
    
    render(<CSVUploadDropzone campaignId="1" />);
    expect(screen.getByText(/95.*of.*100.*contacts imported successfully/)).toBeInTheDocument();
  });

  it('shows error details when there are rejected rows', () => {
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      uploadProgress: { status: 'complete', progress: 100, message: 'Upload complete!' },
      uploadResult: {
        campaign_id: '1',
        total_rows: 100,
        accepted_rows: 95,
        rejected_rows: 5,
        acceptance_rate: 0.95,
        errors: [
          { line_number: 2, field: 'phone_number', error: 'Invalid format', value: 'abc' },
        ],
      },
    });
    
    render(<CSVUploadDropzone campaignId="1" />);
    expect(screen.getByText('Upload completed with warnings')).toBeInTheDocument();
    expect(screen.getByText('Invalid format')).toBeInTheDocument();
  });

  it('shows error state', () => {
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      uploadProgress: { status: 'error', progress: 0, message: 'Network error' },
    });
    
    render(<CSVUploadDropzone campaignId="1" />);
    expect(screen.getByText('Upload failed')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('calls onComplete when done button clicked', async () => {
    const onComplete = jest.fn();
    mockUseCampaignStore.mockReturnValue({
      ...mockUseCampaignStore(),
      uploadProgress: { status: 'complete', progress: 100, message: 'Upload complete!' },
      uploadResult: {
        campaign_id: '1',
        total_rows: 100,
        accepted_rows: 100,
        rejected_rows: 0,
        acceptance_rate: 1.0,
        errors: [],
      },
    });
    
    render(<CSVUploadDropzone campaignId="1" onComplete={onComplete} />);
    fireEvent.click(screen.getByText('Done'));
    expect(onComplete).toHaveBeenCalled();
  });
});