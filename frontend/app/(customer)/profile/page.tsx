"use client";

import {
  Check,
  ChevronRight,
  LogOut,
  Mail,
  MapPin,
  Phone,
  RotateCcw,
  Star,
} from "lucide-react";
import { useRouter } from "next/navigation";

import { useTheme } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useChatStore } from "@/lib/store";
import { THEMES } from "@/lib/themes";
import { CURRENT_USER as u } from "@/lib/user";
import { cn } from "@/lib/utils";

export default function ProfilePage() {
  const { theme, setTheme } = useTheme();
  const resetChat = useChatStore((s) => s.reset);
  const router = useRouter();

  const startNewOrder = () => {
    resetChat();
    router.push("/");
  };

  return (
    <div className="slick-scroll h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-2xl space-y-5 px-4 py-5">
        {/* Identity */}
        <Card className="flex items-center gap-4 p-5">
          <span className="grid size-16 shrink-0 place-items-center rounded-full bg-primary text-xl font-bold text-primary-foreground">
            {u.initials}
          </span>
          <div className="min-w-0">
            <h1 className="font-heading text-xl font-bold">{u.name}</h1>
            <p className="text-sm text-muted-foreground">
              Member since {u.memberSince}
            </p>
          </div>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <Card className="p-4">
            <p className="text-2xl font-bold tabular-nums">{u.stats.orders}</p>
            <p className="text-sm text-muted-foreground">Total orders</p>
          </Card>
          <Card className="p-4">
            <p className="flex items-center gap-1.5 truncate text-lg font-semibold">
              <Star className="size-4 shrink-0 text-secondary" />
              {u.stats.favourite}
            </p>
            <p className="text-sm text-muted-foreground">Favourite</p>
          </Card>
        </div>

        {/* Contact */}
        <Section title="Account">
          <Row icon={Phone} label="Phone" value={u.phone} />
          <Row icon={Mail} label="Email" value={u.email} />
        </Section>

        {/* Addresses */}
        <Section title="Saved addresses">
          {u.addresses.map((a) => (
            <div key={a.id} className="flex items-start gap-3 px-4 py-3">
              <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 text-sm font-medium">
                  {a.label}
                  {a.isDefault && <Badge variant="primary">Default</Badge>}
                </p>
                <p className="text-sm text-muted-foreground">{a.line}</p>
              </div>
            </div>
          ))}
        </Section>

        {/* Appearance — configurable palette lives here (settings-style) */}
        <Section title="Appearance">
          <div className="grid grid-cols-2 gap-2 p-3">
            {THEMES.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTheme(t.id)}
                aria-pressed={theme === t.id}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-left transition-colors",
                  theme === t.id
                    ? "border-primary bg-primary/10"
                    : "border-border bg-surface-2 hover:border-primary/50"
                )}
              >
                <span className="flex shrink-0 -space-x-1.5">
                  <span
                    className="size-5 rounded-full border border-black/20"
                    style={{ background: t.swatch.primary }}
                  />
                  <span
                    className="size-5 rounded-full border border-black/20"
                    style={{ background: t.swatch.accent }}
                  />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {t.label}
                  </span>
                </span>
                {theme === t.id && (
                  <Check className="size-4 shrink-0 text-primary" />
                )}
              </button>
            ))}
          </div>
        </Section>

        {/* Actions */}
        <div className="space-y-2">
          <button
            type="button"
            onClick={startNewOrder}
            className="flex w-full cursor-pointer items-center gap-3 rounded-xl border border-border bg-card px-4 py-3.5 text-left transition-colors hover:border-primary/60"
          >
            <RotateCcw className="size-5 text-muted-foreground" />
            <span className="flex-1 text-sm font-medium">
              Start a new order
            </span>
            <ChevronRight className="size-4 text-muted-foreground" />
          </button>

          <Button
            variant="outline"
            className="w-full text-destructive"
            disabled
            title="Auth is a future milestone"
          >
            <LogOut />
            Sign out
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            Demo profile — sign-in arrives with auth.
          </p>
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      <Card className="divide-y divide-border overflow-hidden p-0">
        {children}
      </Card>
    </section>
  );
}

function Row({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Phone;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <Icon className="size-4 shrink-0 text-muted-foreground" />
      <span className="flex-1 text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}
