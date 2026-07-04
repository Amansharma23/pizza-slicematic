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
  // Tablet-first (device idiom by role, like the customer phone frame): on a
  // desktop the kiosk sits in a centered landscape-tablet frame (~1024×800,
  // backdrop gutters + border); on a real tablet it fills the screen.
  return (
    <div className="flex min-h-dvh items-center justify-center bg-backdrop lg:p-6">
      <div className="relative h-dvh w-full max-w-5xl overflow-hidden bg-background shadow-2xl lg:h-[min(800px,calc(100dvh-3rem))] lg:rounded-2xl lg:border lg:border-border">
        <StaffKioskGate>{children}</StaffKioskGate>
      </div>
    </div>
  );
}
