"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

type AdminConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  busy?: boolean;
  variant?: "destructive" | "secondary" | "primary";
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
};

export function AdminConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  busy = false,
  variant = "destructive",
  onCancel,
  onConfirm,
}: AdminConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <section
        className="w-full max-w-md rounded-lg border border-border bg-card p-5 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-confirm-title"
      >
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
            <AlertTriangle className="size-5" />
          </div>
          <div>
            <h2 id="admin-confirm-title" className="font-heading text-lg font-semibold">
              {title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {description}
            </p>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" disabled={busy} onClick={onCancel}>
            Cancel
          </Button>
          <Button variant={variant} disabled={busy} onClick={() => void onConfirm()}>
            {busy ? "Working" : confirmLabel}
          </Button>
        </div>
      </section>
    </div>
  );
}
