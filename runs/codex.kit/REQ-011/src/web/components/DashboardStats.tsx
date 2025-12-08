import type { CampaignStats } from "@/lib/api/types";

export function DashboardStats({ stats }: { stats: CampaignStats }) {
  const cards = [
    { label: "Total contacts", value: stats.totals.contacts },
    { label: "Completed", value: stats.totals.completed },
    { label: "Refused", value: stats.totals.refused },
    { label: "Not reached", value: stats.totals.not_reached },
    { label: "Avg attempts", value: stats.attempts_avg.toFixed(1) },
    { label: "Completion rate", value: `${(stats.completion_rate * 100).toFixed(1)}%` }
  ];

  return (
    <section className="grid gap-4 md:grid-cols-3">
      {cards.map((card) => (
        <article key={card.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">{card.label}</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{card.value}</p>
        </article>
      ))}
    </section>
  );
}