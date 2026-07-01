/**
 * Staff surface shell — kiosk-style, deliberately separate from (customer):
 * no chat, no voice, no bottom tab bar. Owns its own chrome. Independent so it
 * can evolve (and later be auth/role-gated) without touching customer/admin.
 */
export default function StaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="min-h-dvh bg-background">{children}</div>;
}
