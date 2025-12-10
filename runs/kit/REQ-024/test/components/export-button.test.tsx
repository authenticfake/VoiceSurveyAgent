/**
 * Tests for ExportButton component.
 * REQ-024: Frontend dashboard and export UI
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExportButton } from '@/components/dashboard/export-button';
import { useDashboardStore } from '@/store/dashboard-store';

// Mock the store
jest.mock('@/store/dashboard-store');

const mockUseDashboardStore = useDashboardStore as jest.MockedFunction<typeof useDashboardStore>;

describe('ExportButton', () => {
  const defaultStoreState = {
    currentExport: null,
    isExporting: false,
    exportError: null,
    initiateExport: jest.fn(),
    pollExportStatus: jest.fn(),
    downloadExport: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseDashboardStore.mockReturnValue(defaultStoreState);
  });

  it('renders export button in initial state', () => {
    render(<ExportButton campaignId="test-id" campaignName="Test Campaign" />);
    
    expect(screen.getByText('Export CSV')).toBeInTheDocument();
  });

  it('shows loading state when exporting', () => {
    mockUseDashboardStore.mockReturnValue({
      ...defaultStoreState,
      isExporting: true,
    });
    
    render(<ExportButton campaignId="test-id" campaignName="Test Campaign" />);
    
    expect(screen.getByText('Starting...')).toBeInTheDocument();
  });

  it('shows processing state when export is pending', () => {
    mockUseDashboardStore.mockReturnValue({
      ...defaultStoreState,
      currentExport: {
        id: 'job-1',
        campaign_id: 'test-id',
        status: 'processing',
        download_url: null,
        expires_at: null,
        error_message: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
      },
    });
    
    render(<ExportButton campaignId="test-id" campaignName="Test Campaign" />);
    
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('shows download button when export is complete', () => {
    mockUseDashboardStore.mockReturnValue({
      ...defaultStoreState,
      currentExport: {
        id: 'job-1',
        campaign_id: 'test-id',
        status: 'completed',
        download_url: 'https://example.com/download',
        expires_at: '2024-01-16T10:00:00Z',
        error_message: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
      },
    });
    
    render(<ExportButton campaignId="test-id" campaignName="Test Campaign" />);
    
    expect(screen.getByText('Download CSV')).toBeInTheDocument();
    expect(screen.getByText('New Export')).toBeInTheDocument();
  });

  it('shows error state when export fails', () => {
    mockUseDashboardStore.mockReturnValue({
      ...defaultStoreState,
      currentExport: {
        id: 'job-1',
        campaign_id: 'test-id',
        status: 'failed',
        download_url: null,
        expires_at: null,
        error_message: 'Export failed due to server error',
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
      },
    });
    
    render(<ExportButton campaignId="test-id" campaignName="Test Campaign" />);
    
    expect(screen.getByText('Export failed')).toBeInTheDocument();
    expect(screen.getByText('Export failed due to server error')).toBeInTheDocument();
    expect(screen.getByText('Retry Export')).toBeInTheDocument();
  });

  it('calls initiateExport when export button is clicked', async () => {
    const initiateExport = jest.fn().mockResolvedValue('job-1');
    mockUseDashboardStore.mockReturnValue({
      ...defaultStoreState,
      initiateExport,
    });
    
    render(<ExportButton campaignId="test-id" campaignName="Test Campaign" />);
    
    fireEvent.click(screen.getByText('Export CSV'));
    
    await waitFor(() => {
      expect(initiateExport).toHaveBeenCalledWith('test-id');
    });
  });

  it('calls downloadExport when download button is clicked', async () => {
    const downloadExport = jest.fn().mockResolvedValue(undefined);
    mockUseDashboardStore.mockReturnValue({
      ...defaultStoreState,
      downloadExport,
      currentExport: {
        id: 'job-1',
        campaign_id: 'test-id',
        status: 'completed',
        download_url: 'https://example.com/download',
        expires_at: '2024-01-16T10:00:00Z',
        error_message: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
      },
    });
    
    render(<ExportButton campaignId="test-id" campaignName="Test Campaign" />);
    
    fireEvent.click(screen.getByText('Download CSV'));
    
    await waitFor(() => {
      expect(downloadExport).toHaveBeenCalledWith(
        'https://example.com/download',
        'campaign_Test_Campaign_export.csv'
      );
    });
  });
});