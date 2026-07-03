import { KitchenKioskGate } from "@/components/kitchen/kiosk-gate";

/**
 * Kitchen surface shell — kiosk-style, independent from every other surface
 * (shares only the root layout). The role gate (emp_id + PIN, role
 * `kitchen_staff`) lives here, per the surface-isolation seam.
 */
export default function KitchenLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh bg-background">
      <KitchenKioskGate>{children}</KitchenKioskGate>
    </div>
  );
}
