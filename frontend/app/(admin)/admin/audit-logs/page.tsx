"use client";

import { useEffect, useState } from "react";

import { getAdminAuditLogs, type AdminAuditLog } from "@/lib/admin-api";
import {
  AdminEmptyTableRow,
  AdminError,
  AdminLoading,
  AdminPageHeader,
} from "@/components/admin/admin-table-shell";
import { Badge } from "@/components/ui/badge";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; logs: AdminAuditLog[] };

export default function AdminAuditLogsPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const data = await getAdminAuditLogs();
      setState({ status: "ready", logs: data.audit_logs });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Audit load failed.",
      });
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state.status === "loading") return <AdminLoading label="Loading audit logs" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Audit Logs"
        subtitle="Track admin actions for pricing, menu availability, refunds, and more."
      />
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Entity</th>
                <th className="px-4 py-3">By</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Time</th>
              </tr>
            </thead>
            <tbody>
              {state.logs.length ? (
                state.logs.map((log) => (
                  <tr key={log.id} className="border-t border-border">
                    <td className="px-4 py-3">
                      <Badge variant="primary">{log.action_type}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{log.entity_type}</p>
                      <p className="text-xs text-muted-foreground">{log.entity_id}</p>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {log.performed_by_name ?? "System"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {log.reason ?? "-"}
                    </td>
                    <td className="px-4 py-3">
                      {new Date(log.performed_at).toLocaleString("en-IN")}
                    </td>
                  </tr>
                ))
              ) : (
                <AdminEmptyTableRow
                  colSpan={5}
                  title="No audit logs"
                  description="Admin changes to menu, pricing, refunds, inventory, and settings will be recorded here."
                />
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
