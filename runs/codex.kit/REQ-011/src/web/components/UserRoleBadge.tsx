import type { Role } from "@/lib/api/types";

const roleText: Record<Role, string> = {
  admin: "Admin",
  campaign_manager: "Campaign Manager",
  viewer: "Viewer"
};

const roleStyle: Record<Role, string> = {
  admin: "bg-emerald-100 text-emerald-800",
  campaign_manager: "bg-blue-100 text-blue-800",
  viewer: "bg-slate-100 text-slate-600"
};

export function UserRoleBadge({ role }: { role: Role }) {
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${roleStyle[role]}`}>{roleText[role]}</span>
  );
}