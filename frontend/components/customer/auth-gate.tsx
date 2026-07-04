"use client";

import { CustomerAuthScreens } from "@/components/customer/auth-screens";
import { useRoleUser } from "@/lib/auth-store";

/**
 * Customer surface gate: everything inside the phone frame (header, tabs,
 * screens) renders only for a signed-in `user`-role account; otherwise the
 * sign-in / sign-up screens take over the frame.
 *
 * UX-layer gate only — the API independently verifies the JWT server-side.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { hydrated, user } = useRoleUser("user");

  // Wait for localStorage before deciding — avoids a login flash on reload.
  if (!hydrated) return null;
  if (!user) return <CustomerAuthScreens />;
  return <>{children}</>;
}
