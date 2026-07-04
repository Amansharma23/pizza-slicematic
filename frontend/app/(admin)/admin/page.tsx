import { AdminDashboard } from "@/components/admin/admin-dashboard";

export default function AdminHomePage() {
  return <AdminDashboard />;
}

function CreateEmployeeCard({ onCreated }: { onCreated: () => void }) {
  const token = useAuthStore((s) => s.token);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState<Role>("staff");
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<AuthUser | null>(null);

  const nameOk = /^[A-Za-z ]{2,40}$/.test(name.trim());
  const phoneOk = /^[6-9]\d{9}$/.test(phone.trim());
  const pinOk = /^\d{6}$/.test(pin);
  const canSubmit = !busy && nameOk && phoneOk && pinOk;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || !token) return;
    setBusy(true);
    setError(null);
    setCreated(null);
    try {
      const res = await createEmployee(token, {
        name: name.trim(),
        phone: phone.trim(),
        role,
        pin,
      });
      if (res.ok && res.employee) {
        setCreated(res.employee);
        setName("");
        setPhone("");
        setPin("");
        onCreated();
      } else {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setError(first ?? "Couldn't create the employee.");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Couldn't create the employee."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="h-fit space-y-4 p-5">
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <UserPlus className="size-4 text-primary" />
        Add an employee
      </h2>

      <form onSubmit={submit} className="space-y-3">
        <div>
          <label
            htmlFor="emp-name"
            className="mb-1 block text-xs text-muted-foreground"
          >
            Full name
          </label>
          <Input
            id="emp-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Ravi Kumar"
            aria-invalid={name.length > 0 && !nameOk}
          />
        </div>
        <div>
          <label
            htmlFor="emp-phone"
            className="mb-1 block text-xs text-muted-foreground"
          >
            Phone
          </label>
          <Input
            id="emp-phone"
            type="tel"
            inputMode="numeric"
            maxLength={10}
            value={phone}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
            placeholder="10-digit mobile number"
            aria-invalid={phone.length > 0 && !phoneOk}
          />
        </div>

        <fieldset>
          <legend className="mb-1 block text-xs text-muted-foreground">
            Role
          </legend>
          <div className="grid grid-cols-3 gap-1.5">
            {ROLES.map((r) => {
              const Icon = r.icon;
              const active = role === r.id;
              return (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setRole(r.id)}
                  aria-pressed={active}
                  className={cn(
                    "flex cursor-pointer flex-col items-center gap-1 rounded-lg border p-2.5 text-xs font-medium transition-colors",
                    active
                      ? "border-primary bg-primary/10 text-foreground"
                      : "border-border bg-surface-2 text-muted-foreground hover:border-primary/50"
                  )}
                >
                  <Icon className="size-4" />
                  {r.label.split(" ")[0]}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div>
          <label
            htmlFor="emp-pin"
            className="mb-1 block text-xs text-muted-foreground"
          >
            Assign a 6-digit PIN
          </label>
          <Input
            id="emp-pin"
            inputMode="numeric"
            maxLength={6}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            placeholder="e.g. 482913"
            aria-invalid={pin.length > 0 && !pinOk}
          />
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {error}
          </div>
        )}
        {created && (
          <div className="rounded-lg border border-success/40 bg-success/10 px-3 py-2 text-sm">
            <span className="font-semibold">{created.name}</span> created —
            share ID <span className="font-mono font-semibold">{created.emp_id}</span>{" "}
            and the PIN with them.
          </div>
        )}

        <Button type="submit" className="w-full" disabled={!canSubmit}>
          {busy && <Loader2 className="animate-spin" />}
          Create account
        </Button>
      </form>
    </Card>
  );
}

function EmployeeTable({
  employees,
  loading,
  error,
  onChanged,
}: {
  employees: AuthUser[];
  loading: boolean;
  error: string | null;
  onChanged: () => void;
}) {
  const token = useAuthStore((s) => s.token);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pinFor, setPinFor] = useState<string | null>(null);
  const [newPin, setNewPin] = useState("");
  const [rowError, setRowError] = useState<string | null>(null);

  const act = async (id: string, payload: { is_active?: boolean; pin?: string }) => {
    if (!token) return;
    setBusyId(id);
    setRowError(null);
    try {
      const res = await updateEmployee(token, id, payload);
      if (!res.ok) {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setRowError(first ?? "Update failed.");
      } else {
        setPinFor(null);
        setNewPin("");
        onChanged();
      }
    } catch (err) {
      setRowError(err instanceof Error ? err.message : "Update failed.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Card className="overflow-hidden p-0">
      {loading ? (
        <div className="space-y-2 p-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-12 animate-pulse rounded-lg bg-surface-2"
            />
          ))}
        </div>
      ) : error ? (
        <p role="alert" className="p-4 text-sm text-destructive">
          {error}
        </p>
      ) : employees.length === 0 ? (
        <p className="p-6 text-center text-sm text-muted-foreground">
          No employees yet — create the first one on the left.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-3 font-semibold">ID</th>
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Role</th>
                <th className="px-4 py-3 font-semibold">Phone</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {employees.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-3 font-mono text-xs">{e.emp_id}</td>
                  <td className="px-4 py-3 font-medium">{e.name}</td>
                  <td className="px-4 py-3">
                    <Badge variant="primary">
                      {ROLE_LABEL[e.role] ?? e.role}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 tabular-nums">{e.phone}</td>
                  <td className="px-4 py-3">
                    <Badge variant={e.is_active ? "success" : "destructive"}>
                      {e.is_active ? "Active" : "Deactivated"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1.5">
                      {pinFor === e.id ? (
                        <>
                          <Input
                            aria-label={`New PIN for ${e.name}`}
                            className="h-8 w-24 text-xs"
                            inputMode="numeric"
                            maxLength={6}
                            value={newPin}
                            onChange={(ev) =>
                              setNewPin(ev.target.value.replace(/\D/g, ""))
                            }
                            placeholder="New PIN"
                            autoFocus
                          />
                          <Button
                            size="sm"
                            disabled={
                              !/^\d{6}$/.test(newPin) || busyId === e.id
                            }
                            onClick={() => void act(e.id, { pin: newPin })}
                          >
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setPinFor(null);
                              setNewPin("");
                            }}
                          >
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyId === e.id}
                            onClick={() => {
                              setPinFor(e.id);
                              setNewPin("");
                            }}
                          >
                            <KeyRound />
                            Reset PIN
                          </Button>
                          <Button
                            size="sm"
                            variant={e.is_active ? "outline" : "secondary"}
                            className={cn(e.is_active && "text-destructive")}
                            disabled={busyId === e.id}
                            onClick={() =>
                              void act(e.id, { is_active: !e.is_active })
                            }
                          >
                            {e.is_active ? "Deactivate" : "Reactivate"}
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rowError && (
        <p role="alert" className="border-t border-border p-3 text-sm text-destructive">
          {rowError}
        </p>
      )}
    </Card>
  );
}
