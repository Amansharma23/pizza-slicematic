import type { LucideIcon } from "lucide-react";

/** Placeholder for tabs whose flows land in later milestones. */
export function ComingSoon({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 px-8 text-center">
      <span className="grid size-16 place-items-center rounded-2xl bg-surface-2 text-primary">
        <Icon className="size-8" />
      </span>
      <div className="space-y-1">
        <h2 className="font-heading text-xl font-semibold">{title}</h2>
        <p className="max-w-xs text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
