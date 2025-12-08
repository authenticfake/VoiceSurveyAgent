"use client";

import type { Role } from "@/lib/api/types";
import { useUserContext } from "@/lib/auth/user-context";

interface Props {
  allowed: Role[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
  loadingPlaceholder?: React.ReactNode;
}

export function RbacGuard({ allowed, children, fallback = null, loadingPlaceholder = null }: Props) {
  const { user, loading } = useUserContext();

  if (loading) {
    return <>{loadingPlaceholder}</>;
  }

  if (!user || !allowed.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}