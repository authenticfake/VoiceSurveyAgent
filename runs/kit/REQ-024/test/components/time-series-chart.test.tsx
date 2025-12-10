/**
 * Tests for TimeSeriesChart component.
 * REQ-024: Frontend dashboard and export UI
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { TimeSeriesChart } from '@/components/dashboard/time-series-chart';
import { TimeSeriesData } from '@/types/dashboard';

// Mock recharts to avoid canvas issues in tests
jest.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const mockTimeSeriesData: TimeSeriesData = {
  campaign_id: 'test-campaign-id',
  granularity: 'hourly',
  data_points: [
    {
      timestamp: '2024-01-15T09:00:00Z',
      hour: 9,
      calls_attempted: 50,
      calls_completed: 25,
      calls_refused: 5,
      calls_not_reached: 10,
    },
    {
      timestamp: '2024-01-15T10:00:00Z',
      hour: 10,
      calls_attempted: 60,
      calls_completed: 30,
      calls_refused: 8,
      calls_not_reached: 12,
    },
  ],
  start_date: '2024-01-15',
  end_date: '2024-01-15',
};

describe('TimeSeriesChart', () => {
  it('renders loading state', () => {
    render(
      <TimeSeriesChart
        data={null}
        isLoading={true}
        error={null}
      />
    );
    
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    const onRetry = jest.fn();
    
    render(
      <TimeSeriesChart
        data={null}
        isLoading={false}
        error="Failed to load data"
        onRetry={onRetry}
      />
    );
    
    expect(screen.getByText('Failed to load chart')).toBeInTheDocument();
    expect(screen.getByText('Failed to load data')).toBeInTheDocument();
    
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('renders empty state when no data points', () => {
    const emptyData: TimeSeriesData = {
      ...mockTimeSeriesData,
      data_points: [],
    };
    
    render(
      <TimeSeriesChart
        data={emptyData}
        isLoading={false}
        error={null}
      />
    );
    
    expect(screen.getByText('No data available for the selected period')).toBeInTheDocument();
  });

  it('renders chart when data is available', () => {
    render(
      <TimeSeriesChart
        data={mockTimeSeriesData}
        isLoading={false}
        error={null}
      />
    );
    
    expect(screen.getByText('Call Activity')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });
});