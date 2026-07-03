import { DeliveryGate } from "@/components/delivery/delivery-gate";

/**
 * Delivery surface shell — phone-first like the customer app (riders work from
 * their phones), but fully independent from every other surface (shares only
 * the root layout). The role gate (emp_id + PIN, role `delivery`) lives here.
 */
export default function DeliveryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh justify-center bg-backdrop">
      <div className="relative flex h-dvh w-full max-w-md flex-col overflow-hidden bg-background shadow-2xl sm:border-x sm:border-border">
        <DeliveryGate>{children}</DeliveryGate>
      </div>
    </div>
  );
}
