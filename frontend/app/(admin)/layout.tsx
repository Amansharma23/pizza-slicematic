import { AdminGate } from "@/components/admin/admin-gate";

/**
 * Admin surface shell — independent from every other surface (shares only the
 * root layout). The role gate (email + password, role `admin`) lives here, per
 * the surface-isolation seam. Desktop/webpage idiom, no phone frame.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh bg-background">
      <AdminGate>{children}</AdminGate>
    </div>
  );
}
