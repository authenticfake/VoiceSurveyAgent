/**
 * Time series chart component for call activity visualization.
 * REQ-024: Frontend dashboard and export UI
 */

'use client';

import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent, Spinner, Alert } from '@/components/ui';
import { TimeSeriesData } from '@/types/dashboard';
import { formatDate } from '@/lib/utils';

interface TimeSeriesChartProps {
  data: TimeSeriesData | null;
  isLoading: boolean;
  error: string | null;
  onRetry?: () => void;
}

export function TimeSeriesChart({ data, isLoading, error, onRetry }: TimeSeriesChartProps) {
  const chartData = useMemo(() => {
    if (!data?.data_points) return [];
    
    return data.data_points.map((point) => ({
      ...point,
      label: data.granularity === 'hourly' 
        ? `${point.hour}:00`
        : point.day || formatDate(point.timestamp),
    }));
  }, [data]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Call Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="flex items-center justify-center h-80">
            <Spinner size="lg" />
          </div>
        )}

        {error && (
          <Alert variant="error" title="Failed to load chart">
            {error}
            {onRetry && (
              <button
                onClick={onRetry}
                className="ml-2 text-sm underline hover:no-underline"
              >
                Retry
              </button>
            )}
          </Alert>
        )}

        {!isLoading && !error && chartData.length === 0 && (
          <div className="flex items-center justify-center h-80 text-gray-500">
            No data available for the selected period
          </div>
        )}

        {!isLoading && !error && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis 
                dataKey="label" 
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="calls_attempted"
                name="Attempted"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="calls_completed"
                name="Completed"
                stroke="#22c55e"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="calls_refused"
                name="Refused"
                stroke="#ef4444"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="calls_not_reached"
                name="Not Reached"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}