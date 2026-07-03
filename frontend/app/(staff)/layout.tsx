import { StaffKioskGate } from "@/components/staff/kiosk-gate";

/**
 * Staff surface shell — kiosk-style, deliberately separate from (customer):
 * no chat, no voice, no bottom tab bar. Owns its own chrome. The role gate
 * (emp_id + PIN, role `staff`) lives here, per the surface-isolation seam.
 */
export default function StaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh bg-background">
      <StaffKioskGate>{children}</StaffKioskGate>
    </div>
  );
}
