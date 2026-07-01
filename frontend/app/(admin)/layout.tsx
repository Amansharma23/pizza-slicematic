/**
 * Admin surface shell — independent from (customer) and (staff). Not yet scoped;
 * this seam lets a teammate build admin features here without touching, or being
 * able to break, the other surfaces. Auth/role gating will live in this layout.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="min-h-dvh bg-background">{children}</div>;
}
