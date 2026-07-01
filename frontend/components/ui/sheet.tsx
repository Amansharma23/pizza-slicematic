"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Bottom sheet built on Radix Dialog — accessible (focus trap, ESC, aria) and
 * reused for inline flows (customization, cart) so they never navigate away.
 */

export const Sheet = Dialog.Root;
export const SheetTrigger = Dialog.Trigger;
export const SheetClose = Dialog.Close;

export function SheetContent({
  children,
  className,
  title,
  description,
}: {
  children: React.ReactNode;
  className?: string;
  title: string;
  description?: string;
}) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-[2px] data-[state=open]:animate-[fade-in_0.2s_ease-out] data-[state=closed]:opacity-0" />
      <Dialog.Content
        className={cn(
          "fixed inset-x-0 bottom-0 z-50 mx-auto flex max-h-[92dvh] w-full max-w-md flex-col rounded-t-2xl border border-border bg-card shadow-2xl focus:outline-none",
          "data-[state=open]:animate-[sheet-up_0.28s_cubic-bezier(0.32,0.72,0,1)]",
          className
        )}
      >
        <div className="relative shrink-0 border-b border-border px-5 pb-3 pt-4">
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border" />
          <Dialog.Title className="font-heading text-lg font-semibold">
            {title}
          </Dialog.Title>
          {description ? (
            <Dialog.Description className="mt-0.5 text-sm text-muted-foreground">
              {description}
            </Dialog.Description>
          ) : (
            <Dialog.Description className="sr-only">{title}</Dialog.Description>
          )}
          <Dialog.Close
            aria-label="Close"
            className="absolute right-4 top-4 grid size-8 cursor-pointer place-items-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <X className="size-5" />
          </Dialog.Close>
        </div>
        {children}
      </Dialog.Content>
    </Dialog.Portal>
  );
}
