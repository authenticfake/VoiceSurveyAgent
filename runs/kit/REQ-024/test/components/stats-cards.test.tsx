/**
 * Tests for StatsCards component.
 * REQ-024: Frontend dashboard and export UI
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatsCards } from '@/components/dashboard/stats-cards';
import { CampaignStats } from '@/types/dashboard';

const mockStats: CampaignStats = {
  campaign_id: 'test-campaign-id',
  total_contacts: 1000,
  completed: 450,
  refused: 100,
  not_reached: 200,
  pending: 200,
  in_progress: 50,
  excluded: 0,
  completion_rate: 0.45,
  refusal_rate: 0.1,
  not_reached_rate: 0.2,
  average_call_duration_seconds: 120,
  p95_latency_ms: 1200,
  last_updated: '2024-01-15T10:30:00Z',
};

describe('StatsCards', () => {
  it('renders loading state with spinners', () => {
    render(<StatsCards stats={null} isLoading={true} />);
    
    // Should show 6 loading cards
    const cards = screen.getAllByRole('status');
    expect(cards).toHaveLength(6);
  });

  it('renders nothing when stats is null and not loading', () => {
    const { container } = render(<StatsCards stats={null} isLoading={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders all stat cards with correct values', () => {
    render(<StatsCards stats={mockStats} isLoading={false} />);
    
    // Total contacts
    expect(screen.getByText('Total Contacts')).toBeInTheDocument();
    expect(screen.getByText('1000')).toBeInTheDocument();
    expect(screen.getByText('200 pending, 50 in progress')).toBeInTheDocument();
    
    // Completed
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('450')).toBeInTheDocument();
    expect(screen.getByText('45.0%')).toBeInTheDocument();
    
    // Refused
    expect(screen.getByText('Refused')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('10.0%')).toBeInTheDocument();
    
    // Not Reached
    expect(screen.getByText('Not Reached')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText('20.0%')).toBeInTheDocument();
    
    // Avg Call Duration
    expect(screen.getByText('Avg Call Duration')).toBeInTheDocument();
    expect(screen.getByText('120s')).toBeInTheDocument();
    
    // P95 Latency
    expect(screen.getByText('P95 Latency')).toBeInTheDocument();
    expect(screen.getByText('1200ms')).toBeInTheDocument();
  });

  it('renders N/A for null duration and latency', () => {
    const statsWithNulls: CampaignStats = {
      ...mockStats,
      average_call_duration_seconds: null,
      p95_latency_ms: null,
    };
    
    render(<StatsCards stats={statsWithNulls} isLoading={false} />);
    
    const naElements = screen.getAllByText('N/A');
    expect(naElements).toHaveLength(2);
  });
});