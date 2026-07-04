"use client";

import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function AdminLoading({ label }: { label: string }) {
  return (
    <div className="grid min-h-[50dvh] place-items-center text-sm text-muted-foreground">
      <span className="flex items-center gap-3">
        <RefreshCw className="size-4 animate-spin" />
        {label}
      </span>
    </div>
  );
}

export function AdminError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="grid min-h-[50dvh] place-items-center px-4">
      <Card className="max-w-md rounded-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangle className="size-5 text-destructive" />
            Could not load
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{message}</p>
          <Button onClick={onRetry} variant="secondary">
            <RefreshCw />
            Retry
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export function AdminPageHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <header className="border-b border-border pb-5">
      <h1 className="font-heading text-2xl font-bold">{title}</h1>
      <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
    </header>
  );
}

export function AdminEmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex min-h-32 flex-col items-center justify-center px-4 py-8 text-center">
      <div className="flex size-10 items-center justify-center rounded-lg bg-surface-2 text-muted-foreground">
        <Inbox className="size-5" />
      </div>
      <h3 className="mt-3 text-sm font-semibold">{title}</h3>
      <p className="mt-1 max-w-md text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </div>
  );
}

export function AdminEmptyTableRow({
  colSpan,
  title,
  description,
}: {
  colSpan: number;
  title: string;
  description: string;
}) {
  return (
    <tr className="border-t border-border">
      <td colSpan={colSpan}>
        <AdminEmptyState title={title} description={description} />
      </td>
    </tr>
  );
}
