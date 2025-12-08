"use client";

import type { User } from "@/lib/api/types";
import { apiClient } from "@/lib/api/client";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

interface UserState {
  user: User | null;
  loading: boolean;
  error?: string;
  refresh: () => Promise<void>;
}

const UserContext = createContext<UserState | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const fetchUser = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getCurrentUser();
      setUser(data);
      setError(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load user");
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const value = useMemo<UserState>(
    () => ({
      user,
      loading,
      error,
      refresh: fetchUser
    }),
    [user, loading, error]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUserContext() {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error("useUserContext must be used within UserProvider");
  }
  return ctx;
}