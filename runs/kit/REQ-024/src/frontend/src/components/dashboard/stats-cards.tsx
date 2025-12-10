/**
 * Stats cards component for dashboard metrics.
 * REQ-024: Frontend dashboard and export UI
 */

'use client';

import React from 'react';
import { Card, CardContent, Spinner } from '@/components/ui';
import { CampaignStats } from '@/types/dashboard';
import { formatPercentage } from '@/lib/utils';
import {
  Users,
  CheckCircle,
  XCircle,
  PhoneMissed,
  Clock,
  Zap,
} from 'lucide-react';

interface StatsCardsProps {
  stats: CampaignStats | null;
  isLoading: boolean;
}

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'gray';
}

function StatCard({ title, value, subtitle, icon, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    purple: 'bg-purple-50 text-purple-600',
    gray: 'bg-gray-50 text-gray-600',
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
            {subtitle && (
              <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
            )}
          </div>
          <div className={`p-3 rounded-full ${colorClasses[color]}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function StatsCards({ stats, isLoading }: StatsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <Card key={i}>
            <CardContent className="p-6 flex items-center justify-center h-32">
              <Spinner size="md" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const avgDuration = stats.average_call_duration_seconds
    ? `${Math.round(stats.average_call_duration_seconds)}s`
    : 'N/A';

  const p95Latency = stats.p95_latency_ms
    ? `${stats.p95_latency_ms}ms`
    : 'N/A';

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <StatCard
        title="Total Contacts"
        value={stats.total_contacts}
        subtitle={`${stats.pending} pending, ${stats.in_progress} in progress`}
        icon={<Users className="h-6 w-6" />}
        color="blue"
      />
      <StatCard
        title="Completed"
        value={stats.completed}
        subtitle={formatPercentage(stats.completion_rate)}
        icon={<CheckCircle className="h-6 w-6" />}
        color="green"
      />
      <StatCard
        title="Refused"
        value={stats.refused}
        subtitle={formatPercentage(stats.refusal_rate)}
        icon={<XCircle className="h-6 w-6" />}
        color="red"
      />
      <StatCard
        title="Not Reached"
        value={stats.not_reached}
        subtitle={formatPercentage(stats.not_reached_rate)}
        icon={<PhoneMissed className="h-6 w-6" />}
        color="yellow"
      />
      <StatCard
        title="Avg Call Duration"
        value={avgDuration}
        icon={<Clock className="h-6 w-6" />}
        color="purple"
      />
      <StatCard
        title="P95 Latency"
        value={p95Latency}
        icon={<Zap className="h-6 w-6" />}
        color="gray"
      />
    </div>
  );
}