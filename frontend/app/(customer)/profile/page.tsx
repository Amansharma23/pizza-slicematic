"use client";

import {
  Check,
  ChevronRight,
  LogOut,
  MapPin,
  Pencil,
  Phone,
  Plus,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useTheme } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getMe, saveAddresses, type SavedAddress } from "@/lib/api";
import { initials, memberSince, useAuthStore } from "@/lib/auth-store";
import { useChatStore } from "@/lib/store";
import { THEMES } from "@/lib/themes";
import { cn } from "@/lib/utils";

export default function ProfilePage() {
  const { theme, setTheme } = useTheme();
  const { token, user, setUser, signOut } = useAuthStore();
  const resetChat = useChatStore((s) => s.reset);
  const router = useRouter();

  const [addrError, setAddrError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // null = closed, "" = adding new, otherwise the id being edited
  const [editing, setEditing] = useState<string | null>(null);
  const [label, setLabel] = useState("Home");
  const [line, setLine] = useState("");

  // Refresh from the user table on mount so the profile always shows current
  // server state (not just what was cached at sign-in).
  useEffect(() => {
    if (!token) return;
    getMe(token)
      .then((res) => {
        if (res.ok && res.user) setUser(res.user);
      })
      .catch(() => {}); // keep the cached copy on network hiccups
  }, [token, setUser]);

  if (!user) return null; // gate guarantees a user; satisfy the type checker

  const addresses = user.address ?? [];

  const startNewOrder = () => {
    resetChat();
    router.push("/");
  };

  const openEditor = (a?: SavedAddress) => {
    setEditing(a ? a.id : "");
    setLabel(a?.label ?? (addresses.length === 0 ? "Home" : "Work"));
    setLine(a?.line ?? "");
    setAddrError(null);
  };

  const persist = async (next: SavedAddress[]) => {
    if (!token) return;
    setSaving(true);
    setAddrError(null);
    try {
      // First address (or the edited default) becomes the default.
      if (next.length > 0 && !next.some((a) => a.isDefault)) {
        next = next.map((a, i) => ({ ...a, isDefault: i === 0 }));
      }
      const res = await saveAddresses(token, next);
      if (res.ok && res.user) {
        setUser(res.user);
        setEditing(null);
      } else {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setAddrError(first ?? "Couldn't save the address. Try again.");
      }
    } catch (err) {
      setAddrError(
        err instanceof Error ? err.message : "Couldn't save the address."
      );
    } finally {
      setSaving(false);
    }
  };

  const saveEditor = () => {
    const cleanLine = line.trim();
    if (!cleanLine) {
      setAddrError("Address can't be empty.");
      return;
    }
    const cleanLabel = label.trim() || "Home";
    if (editing === "") {
      void persist([
        ...addresses,
        {
          id: `addr-${Date.now()}`,
          label: cleanLabel,
          line: cleanLine,
          isDefault: addresses.length === 0,
        },
      ]);
    } else {
      void persist(
        addresses.map((a) =>
          a.id === editing ? { ...a, label: cleanLabel, line: cleanLine } : a
        )
      );
    }
  };

  const removeAddress = (id: string) => {
    void persist(addresses.filter((a) => a.id !== id));
  };

  const makeDefault = (id: string) => {
    void persist(addresses.map((a) => ({ ...a, isDefault: a.id === id })));
  };

  return (
    <div className="slick-scroll h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-2xl space-y-5 px-4 py-5">
        {/* Identity */}
        <Card className="flex items-center gap-4 p-5">
          <span className="grid size-16 shrink-0 place-items-center rounded-full bg-primary text-xl font-bold text-primary-foreground">
            {initials(user.name)}
          </span>
          <div className="min-w-0">
            <h1 className="font-heading text-xl font-bold">{user.name}</h1>
            <p className="text-sm text-muted-foreground">
              Member since {memberSince(user.created_at)}
            </p>
          </div>
        </Card>

        {/* Contact */}
        <Section title="Account">
          <Row icon={Phone} label="Phone" value={user.phone ?? "—"} />
        </Section>

        {/* Addresses — needed before a delivery order can be placed */}
        <Section title="Saved addresses">
          {addresses.length === 0 && editing === null && (
            <p className="px-4 py-3 text-sm text-muted-foreground">
              No address yet — add one so we can deliver to you.
            </p>
          )}
          {addresses.map((a) => (
            <div key={a.id} className="flex items-start gap-3 px-4 py-3">
              <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 text-sm font-medium">
                  {a.label}
                  {a.isDefault && <Badge variant="primary">Default</Badge>}
                </p>
                <p className="text-sm text-muted-foreground">{a.line}</p>
                {!a.isDefault && (
                  <button
                    type="button"
                    onClick={() => makeDefault(a.id)}
                    disabled={saving}
                    className="mt-1 cursor-pointer text-xs font-medium text-primary hover:underline"
                  >
                    Make default
                  </button>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  type="button"
                  aria-label={`Edit ${a.label}`}
                  onClick={() => openEditor(a)}
                  className="grid size-8 cursor-pointer place-items-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
                >
                  <Pencil className="size-3.5" />
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${a.label}`}
                  onClick={() => removeAddress(a.id)}
                  disabled={saving}
                  className="grid size-8 cursor-pointer place-items-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-destructive"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            </div>
          ))}

          {editing !== null ? (
            <div className="space-y-2.5 border-t border-border bg-surface-2 px-4 py-3">
              <div>
                <label
                  htmlFor="addr-label"
                  className="mb-1 block text-xs text-muted-foreground"
                >
                  Label
                </label>
                <input
                  id="addr-label"
                  className="h-10 w-full rounded-lg border border-input bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="Home, Work…"
                  maxLength={20}
                />
              </div>
              <div>
                <label
                  htmlFor="addr-line"
                  className="mb-1 block text-xs text-muted-foreground"
                >
                  Full address
                </label>
                <textarea
                  id="addr-line"
                  className="min-h-20 w-full rounded-lg border border-input bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={line}
                  onChange={(e) => setLine(e.target.value)}
                  placeholder="House / flat, street, area, city, PIN code"
                />
              </div>
              {addrError && (
                <p role="alert" className="text-xs text-destructive">
                  {addrError}
                </p>
              )}
              <div className="flex gap-2">
                <Button size="sm" onClick={saveEditor} disabled={saving}>
                  {saving ? "Saving…" : "Save address"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setEditing(null)}
                  disabled={saving}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => openEditor()}
              className="flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left text-sm font-medium text-primary transition-colors hover:bg-surface-2"
            >
              <Plus className="size-4" />
              Add {addresses.length > 0 ? "another" : "an"} address
            </button>
          )}
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
            onClick={() => {
              signOut();
              router.push("/");
            }}
          >
            <LogOut />
            Sign out
          </Button>
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
