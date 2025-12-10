/**
 * CampaignForm component tests.
 * REQ-023: Frontend campaign management UI
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CampaignForm } from '@/components/campaigns/campaign-form';
import { useCampaignStore } from '@/store/campaign-store';

// Mock the store
jest.mock('@/store/campaign-store');

const mockUseCampaignStore = useCampaignStore as jest.MockedFunction<typeof useCampaignStore>;

const mockCampaign = {
  id: '1',
  name: 'Test Campaign',
  description: 'Test description',
  status: 'draft' as const,
  language: 'en' as const,
  intro_script: 'Hello, this is a test',
  question_1_text: 'Question 1',
  question_1_type: 'free_text' as const,
  question_2_text: 'Question 2',
  question_2_type: 'numeric' as const,
  question_3_text: 'Question 3',
  question_3_type: 'scale' as const,
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

describe('CampaignForm', () => {
  const mockCreateCampaign = jest.fn();
  const mockUpdateCampaign = jest.fn();

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
      createCampaign: mockCreateCampaign,
      updateCampaign: mockUpdateCampaign,
      deleteCampaign: jest.fn(),
      activateCampaign: jest.fn(),
      pauseCampaign: jest.fn(),
      validateCampaign: jest.fn(),
      uploadContacts: jest.fn(),
      resetUploadState: jest.fn(),
      clearCurrentCampaign: jest.fn(),
    });
  });

  it('renders create form with empty fields', () => {
    render(<CampaignForm mode="create" />);
    expect(screen.getByLabelText('Campaign Name')).toHaveValue('');
    expect(screen.getByLabelText('Description')).toHaveValue('');
  });

  it('renders edit form with campaign data', () => {
    render(<CampaignForm campaign={mockCampaign} mode="edit" />);
    expect(screen.getByLabelText('Campaign Name')).toHaveValue('Test Campaign');
    expect(screen.getByLabelText('Description')).toHaveValue('Test description');
  });

  it('validates required fields', async () => {
    render(<CampaignForm mode="create" />);
    const submitButton = screen.getByText('Create Campaign');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Campaign name is required')).toBeInTheDocument();
    });
  });

  it('validates max attempts range', async () => {
    render(<CampaignForm mode="create" />);
    
    const nameInput = screen.getByLabelText('Campaign Name');
    await userEvent.type(nameInput, 'Test');
    
    const maxAttemptsInput = screen.getByLabelText('Max Attempts per Contact');
    await userEvent.clear(maxAttemptsInput);
    await userEvent.type(maxAttemptsInput, '10');
    
    const submitButton = screen.getByText('Create Campaign');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Max attempts must be between 1 and 5')).toBeInTheDocument();
    });
  });

  it('validates time window', async () => {
    render(<CampaignForm mode="create" />);
    
    const nameInput = screen.getByLabelText('Campaign Name');
    await userEvent.type(nameInput, 'Test');
    
    const startInput = screen.getByLabelText('Call Window Start (Local Time)');
    const endInput = screen.getByLabelText('Call Window End (Local Time)');
    
    fireEvent.change(startInput, { target: { value: '20:00' } });
    fireEvent.change(endInput, { target: { value: '09:00' } });
    
    const submitButton = screen.getByText('Create Campaign');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('End time must be after start time')).toBeInTheDocument();
    });
  });

  it('calls createCampaign on valid submit in create mode', async () => {
    mockCreateCampaign.mockResolvedValue({ id: 'new-id', ...mockCampaign });
    
    render(<CampaignForm mode="create" />);
    
    const nameInput = screen.getByLabelText('Campaign Name');
    await userEvent.type(nameInput, 'New Campaign');
    
    const submitButton = screen.getByText('Create Campaign');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(mockCreateCampaign).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Campaign',
        })
      );
    });
  });

  it('calls updateCampaign on valid submit in edit mode', async () => {
    mockUpdateCampaign.mockResolvedValue(mockCampaign);
    
    render(<CampaignForm campaign={mockCampaign} mode="edit" />);
    
    const nameInput = screen.getByLabelText('Campaign Name');
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Updated Campaign');
    
    const submitButton = screen.getByText('Save Changes');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(mockUpdateCampaign).toHaveBeenCalledWith(
        '1',
        expect.objectContaining({
          name: 'Updated Campaign',
        })
      );
    });
  });

  it('disables fields for non-draft campaigns', () => {
    const runningCampaign = { ...mockCampaign, status: 'running' as const };
    render(<CampaignForm campaign={runningCampaign} mode="edit" />);
    
    expect(screen.getByLabelText('Campaign Name')).toBeDisabled();
    expect(screen.getByLabelText('Description')).toBeDisabled();
  });

  it('shows warning for non-draft campaigns', () => {
    const runningCampaign = { ...mockCampaign, status: 'running' as const };
    render(<CampaignForm campaign={runningCampaign} mode="edit" />);
    
    expect(screen.getByText('Limited editing')).toBeInTheDocument();
  });
});