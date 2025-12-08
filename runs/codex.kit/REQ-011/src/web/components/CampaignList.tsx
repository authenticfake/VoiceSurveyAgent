"use client";

import type { Campaign, PaginatedResult } from "@/lib/api/types";
import Link from "next/link";
import { useMemo, useState } from "react";
import { UserRoleBadge } from "@/components/UserRoleBadge";
import { useUserContext } from "@/lib/auth/user-context";
import { canManageCampaigns } from "@/lib/auth/roles";

interface CampaignListProps {
  campaigns: PaginatedResult<Campaign>;
}

export function CampaignList({ campaigns }: CampaignListProps) {
  const { user } = useUserContext();
  const [filter, setFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    if (filter === "all") return campaigns.data;
    return campaigns.data.filter((c) => c.status === filter);
  }, [filter, campaigns.data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Campaigns</h1>
          <p className="text-sm text-slate-600">Track configuration and outcomes for every outbound survey.</p>
        </div>
        <div className="flex items-center gap-2">
          {user ? <UserRoleBadge role={user.role} /> : null}
          {canManageCampaigns(user?.role) ? (
            <Link
              href="/campaigns/new"
              className="rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow hover:bg-brand-700"
            >
              New campaign
            </Link>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <label className="text-sm font-medium text-slate-700" htmlFor="status-filter">
          Status filter
        </label>
        <select
          id="status-filter"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          className="rounded-md border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none"
        >
          <option value="all">All</option>
          <option value="draft">Draft</option>
          <option value="scheduled">Scheduled</option>
          <option value="running">Running</option>
          <option value="paused">Paused</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {filtered.map((campaign) => (
          <article key={campaign.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{campaign.name}</h2>
                <p className="text-sm text-slate-500">{campaign.description}</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                {campaign.status}
              </span>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm text-slate-600">
              <div>
                <dt className="font-medium">Language</dt>
                <dd>{campaign.language.toUpperCase()}</dd>
              </div>
              <div>
                <dt className="font-medium">Max attempts</dt>
                <dd>{campaign.max_attempts}</dd>
              </div>
            </dl>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
              <Link href={`/campaigns/${campaign.id}/dashboard`} className="text-brand-700 hover:text-brand-500">
                Dashboard
              </Link>
              {canManageCampaigns(user?.role) ? (
                <Link href={`/campaigns/${campaign.id}/edit`} className="text-brand-700 hover:text-brand-500">
                  Edit
                </Link>
              ) : null}
            </div>
          </article>
        ))}
        {filtered.length === 0 ? <p className="text-sm text-slate-500">No campaigns match the current filter.</p> : null}
      </div>
    </div>
  );
}