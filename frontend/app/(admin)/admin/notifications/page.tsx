"use client";

import { Bell, Send } from "lucide-react";
import { useEffect, useState } from "react";

import {
  createMockNotification,
  getAdminNotifications,
  type AdminNotificationLog,
} from "@/lib/admin-api";
import {
  AdminEmptyTableRow,
  AdminError,
  AdminLoading,
  AdminPageHeader,
} from "@/components/admin/admin-table-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; logs: AdminNotificationLog[] };

export default function AdminNotificationsPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const data = await getAdminNotifications();
      setState({ status: "ready", logs: data.notifications.logs });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Notifications load failed.",
      });
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state.status === "loading") return <AdminLoading label="Loading notifications" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Notifications"
        subtitle="Mock WhatsApp/email notifications with provider-ready logs."
      />
      <NotificationComposer onCreated={load} />
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="border-b border-border p-4">
          <h2 className="font-heading text-lg font-semibold">Notification Logs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[840px] text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Channel</th>
                <th className="px-4 py-3">Recipient</th>
                <th className="px-4 py-3">Template</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {state.logs.length ? (
                state.logs.map((log) => (
                  <tr key={log.id} className="border-t border-border">
                    <td className="px-4 py-3">
                      <Badge variant="primary">{log.channel}</Badge>
                    </td>
                    <td className="px-4 py-3">{log.recipient}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {log.template_name}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={log.status === "mocked" ? "success" : "default"}>
                        {log.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {new Date(log.created_at).toLocaleString("en-IN")}
                    </td>
                  </tr>
                ))
              ) : (
                <AdminEmptyTableRow
                  colSpan={5}
                  title="No notifications"
                  description="Mock and provider-backed WhatsApp or email notification attempts will appear here."
                />
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function NotificationComposer({ onCreated }: { onCreated: () => Promise<void> }) {
  const [channel, setChannel] = useState("whatsapp");
  const [recipient, setRecipient] = useState("9876543210");
  const [message, setMessage] = useState("Your SliceMatic order update is ready.");
  const [saving, setSaving] = useState(false);

  async function send() {
    setSaving(true);
    try {
      await createMockNotification({
        channel,
        recipient,
        template_name: "admin_manual_update",
        payload: { message, subject: "SliceMatic update", body: message },
      });
      await onCreated();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="mb-4 flex items-center gap-2">
        <Bell className="size-5 text-primary" />
        <h2 className="font-heading text-lg font-semibold">Send Mock Notification</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-[160px_1fr_2fr_auto]">
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={channel}
          onChange={(event) => setChannel(event.target.value)}
        >
          <option value="whatsapp">WhatsApp</option>
          <option value="email">Email</option>
          <option value="mock">Mock</option>
        </select>
        <Input value={recipient} onChange={(event) => setRecipient(event.target.value)} />
        <Input value={message} onChange={(event) => setMessage(event.target.value)} />
        <Button disabled={saving} onClick={() => void send()}>
          <Send />
          Send
        </Button>
      </div>
    </section>
  );
}
