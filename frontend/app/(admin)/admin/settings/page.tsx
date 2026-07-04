"use client";

import { Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  getAdminSettings,
  updateAdminSettings,
  type AdminSetting,
} from "@/lib/admin-api";
import {
  AdminError,
  AdminLoading,
  AdminPageHeader,
} from "@/components/admin/admin-table-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const editableKeys = [
  "restaurant_name",
  "restaurant_gstin",
  "restaurant_phone",
  "restaurant_address",
  "notification_whatsapp_provider",
  "notification_email_provider",
];

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; settings: AdminSetting[] };

export default function AdminSettingsPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [saving, setSaving] = useState(false);

  async function load() {
    setState({ status: "loading" });
    try {
      const data = await getAdminSettings();
      setState({ status: "ready", settings: data.settings });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Settings load failed.",
      });
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state.status === "loading") return <AdminLoading label="Loading settings" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  return <SettingsForm settings={state.settings} saving={saving} setSaving={setSaving} onSaved={load} />;
}

function SettingsForm({
  settings,
  saving,
  setSaving,
  onSaved,
}: {
  settings: AdminSetting[];
  saving: boolean;
  setSaving: (saving: boolean) => void;
  onSaved: () => Promise<void>;
}) {
  const initial = useMemo(() => {
    return Object.fromEntries(
      settings
        .filter((setting) => editableKeys.includes(setting.key))
        .map((setting) => [setting.key, String(setting.value?.value ?? "")])
    );
  }, [settings]);
  const [values, setValues] = useState(initial);

  async function save() {
    setSaving(true);
    try {
      await updateAdminSettings(values, "Stage 5B settings update");
      await onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Settings"
        subtitle="Restaurant identity and provider selection. Secrets stay in environment variables."
      />
      <section className="grid gap-4 rounded-lg border border-border bg-card p-4">
        {editableKeys.map((key) => (
          <label key={key} className="space-y-2">
            <span className="text-sm font-medium">{labelFor(key)}</span>
            <Input
              value={values[key] ?? ""}
              onChange={(event) =>
                setValues((current) => ({ ...current, [key]: event.target.value }))
              }
            />
          </label>
        ))}
        <Button className="w-fit" disabled={saving} onClick={() => void save()}>
          <Save />
          Save Settings
        </Button>
      </section>
    </main>
  );
}

function labelFor(key: string) {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
