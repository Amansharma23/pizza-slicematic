import { MonitorSmartphone } from "lucide-react";

// Kiosk POS lands in a later milestone (category tabs, item grid, order-ticket
// sidebar, "Send to kitchen"). This is the independent entry point at /staff.
export default function StaffHomePage() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 px-8 text-center">
      <span className="grid size-16 place-items-center rounded-2xl bg-surface-2 text-primary">
        <MonitorSmartphone className="size-8" />
      </span>
      <div className="space-y-1">
        <h1 className="font-heading text-2xl font-bold">Staff Kiosk</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Touch-first POS for in-store staff — category tabs, item grid, and a
          running order ticket. Independent from the customer app.
        </p>
      </div>
    </div>
  );
}
