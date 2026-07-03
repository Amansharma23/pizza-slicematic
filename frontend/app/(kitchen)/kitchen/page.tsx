import { ChefHat } from "lucide-react";

// Kitchen display lands in a later milestone (incoming ticket queue, "start
// preparing" / "ready" actions that drive real order status). Independent
// entry point at /kitchen, behind the kitchen_staff kiosk gate.
export default function KitchenHomePage() {
  return (
    <div className="flex h-full min-h-[60dvh] flex-col items-center justify-center gap-4 px-8 text-center">
      <span className="grid size-16 place-items-center rounded-2xl bg-surface-2 text-primary">
        <ChefHat className="size-8" />
      </span>
      <div className="space-y-1">
        <h1 className="font-heading text-2xl font-bold">Kitchen Display</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Incoming order tickets with prepare/ready actions land here in a
          later milestone. Independent from the other surfaces.
        </p>
      </div>
    </div>
  );
}
