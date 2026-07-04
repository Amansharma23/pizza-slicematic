import { DashboardGate } from "@/components/dashboard/dashboard-gate";

/**
 * Observability dashboard surface — independent from every other surface
 * (shares only the root layout), including /admin: this is a standalone
 * screen, not a tab bolted onto the admin panel. Desktop/webpage idiom, no
 * phone frame.
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh bg-background">
      <DashboardGate>{children}</DashboardGate>
    </div>
  );
}
