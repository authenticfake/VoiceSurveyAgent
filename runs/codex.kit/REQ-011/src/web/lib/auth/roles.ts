import type { Role } from "@/lib/api/types";

export function canManageCampaigns(role?: Role) {
  return role === "admin" || role === "campaign_manager";
}

export function canViewAdmin(role?: Role) {
  return role === "admin";
}

export function canUploadCsv(role?: Role) {
  return canManageCampaigns(role);
}

export function canTriggerExport(role?: Role) {
  return role === "admin" || role === "campaign_manager";
}

export function canActivateCampaign(role?: Role) {
  return role === "admin" || role === "campaign_manager";
}