"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { AuthUser, Role } from "@/lib/api";

/**
 * Session state for ALL surfaces: one signed-in account at a time (JWT +
 * public user row), persisted to localStorage. Each surface's gate checks the
 * ROLE it needs — signing in as e.g. delivery doesn't open /admin.
 *
 * This is the UX layer only; the API independently verifies the JWT on
 * protected endpoints (full per-endpoint authorization is the next step).
 */

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  /** true once localStorage has been read — gates render nothing before that
   *  to avoid a login-screen flash for already-signed-in users. */
  hydrated: boolean;
  setAuth: (token: string, user: AuthUser) => void;
  /** Merge fresh server state for the signed-in user (e.g. after saving an address). */
  setUser: (user: AuthUser) => void;
  setHydrated: () => void;
  signOut: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hydrated: false,
      setAuth: (token, user) => set({ token, user }),
      setUser: (user) => set({ user }),
      setHydrated: () => set({ hydrated: true }),
      signOut: () => set({ token: null, user: null }),
    }),
    {
      name: "slicematic-auth",
      partialize: (s) => ({ token: s.token, user: s.user }),
      onRehydrateStorage: () => (state) => state?.setHydrated(),
    }
  )
);

/** Convenience: the signed-in user only if they hold the given role. */
export function useRoleUser(role: Role) {
  const { token, user, hydrated } = useAuthStore();
  const match = user && token && user.role === role;
  return {
    hydrated,
    token: match ? token : null,
    user: match ? user : null,
  };
}

export function initials(name: string): string {
  return (
    name
      .trim()
      .split(/\s+/)
      .map((w) => w[0]?.toUpperCase() ?? "")
      .slice(0, 2)
      .join("") || "?"
  );
}

export function memberSince(createdAt: string | undefined): string {
  if (!createdAt) return "today";
  const d = new Date(createdAt);
  if (Number.isNaN(d.getTime())) return "today";
  return d.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}
