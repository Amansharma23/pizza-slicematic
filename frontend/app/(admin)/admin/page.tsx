import { ShieldCheck } from "lucide-react";

// Admin is not yet scoped (awaiting the feature list). Independent entry point
// at /admin so the surface exists and stays isolated from customer/staff.
export default function AdminHomePage() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 px-8 text-center">
      <span className="grid size-16 place-items-center rounded-2xl bg-surface-2 text-primary">
        <ShieldCheck className="size-8" />
      </span>
      <div className="space-y-1">
        <h1 className="font-heading text-2xl font-bold">Admin</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Reserved, isolated surface. Features to be scoped — build them here
          without affecting the customer or staff flows.
        </p>
      </div>
    </div>
  );
}
