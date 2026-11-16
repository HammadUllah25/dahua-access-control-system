"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, KeyRound, ShieldCheck, Trash2, UserPlus, UsersRound } from "lucide-react";
import { toast } from "react-toastify";

import { Panel } from "@/components/dashboard/panel";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSession } from "@/components/role-provider";
import {
  createAccount,
  readAccounts,
  removeAccount,
  type Account,
  type AccountRole,
} from "@/lib/accounts";
import {
  DEFAULT_PERMISSIONS,
  permissionModules,
} from "@/lib/nav";
import {
  ROLE_META,
  roleScopeLabel,
  setPermissionsCookie,
  type PagePermissions,
} from "@/lib/roles";

const EMPTY_FORM = {
  name: "",
  email: "",
  password: "",
  role: "admin" as AccountRole,
};

function UsersView() {
  const router = useRouter();
  const { role, permissions } = useSession();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [draft, setDraft] = useState<PagePermissions>(permissions);

  // localStorage is only available after hydration.
  useEffect(() => {
    setAccounts(readAccounts());
  }, []);

  const admins = accounts.filter((account) => account.role === "admin").length;
  const branchAccounts = accounts.filter(
    (account) => account.role === "branch"
  ).length;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.name.trim().length < 2) {
      toast.error("Enter the account holder's name.");
      return;
    }
    if (!form.email.includes("@")) {
      toast.error("Enter a valid email address.");
      return;
    }
    if (form.password.length < 5) {
      toast.error("Password must be at least 5 characters.");
      return;
    }
    if (
      readAccounts().some(
        (account) =>
          account.email.toLowerCase() === form.email.trim().toLowerCase()
      )
    ) {
      toast.error("An account with this email already exists.");
      return;
    }
    const account = createAccount({
      name: form.name,
      email: form.email,
      password: form.password,
      role: form.role,
    });
    setAccounts((current) => [...current, account]);
    setForm({ ...EMPTY_FORM, role: form.role });
    toast.success(
      `${account.name} can now sign in as ${ROLE_META[account.role].label}.`
    );
  };

  const deleteAccount = (account: Account) => {
    if (!window.confirm(`Remove ${account.name}'s account?`)) return;
    removeAccount(account.id);
    setAccounts((current) =>
      current.filter((item) => item.id !== account.id)
    );
    toast.success(`${account.name}'s account was removed.`);
  };

  const togglePermission = (target: AccountRole, href: string) => {
    setDraft((current) => {
      const next = new Set(current[target]);
      if (next.has(href)) next.delete(href);
      else next.add(href);
      return target === "admin"
        ? { ...current, admin: [...next] }
        : { ...current, branch: [...next] };
    });
  };

  const savePermissions = () => {
    setPermissionsCookie(draft);
    router.refresh();
    toast.success("Page permissions saved for Admin and Branch.");
  };

  const resetPermissions = () => {
    setDraft(DEFAULT_PERMISSIONS);
    setPermissionsCookie(DEFAULT_PERMISSIONS);
    router.refresh();
    toast.success("Page permissions reset to defaults.");
  };

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Users & Roles</h2>
          <p className="text-xs text-muted-foreground">
            Create Admin and Branch accounts and choose which pages each role
            can open.
          </p>
        </div>
        <Badge variant="outline">{ROLE_META[role].label}</Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard
          label="Accounts"
          value={accounts.length}
          hint="Admin and Branch sign-ins"
          icon={UsersRound}
          tone="violet"
        />
        <KpiCard
          label="Admins"
          value={admins}
          hint="Area monitoring"
          icon={ShieldCheck}
          tone="violet"
        />
        <KpiCard
          label="Branch"
          value={branchAccounts}
          hint="Branch monitoring"
          icon={Building2}
          tone="muted"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel
          title="Create an account"
          description="The Super Admin creates the Admin and Branch accounts that can sign in here."
          action={<UserPlus aria-hidden className="size-4 text-muted-foreground" />}
        >
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2" noValidate>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">
                Full name
              </span>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="S. Khan"
              />
            </label>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">
                Email
              </span>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="s.khan@fuelco.example"
              />
            </label>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">
                Temporary password
              </span>
              <Input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="At least 5 characters"
              />
            </label>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">
                Role
              </span>
              <Select
                value={form.role}
                onValueChange={(value) =>
                  value &&
                  setForm({ ...form, role: value as AccountRole })
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="branch">Branch</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <div className="sm:col-span-2">
              <Button type="submit">
                <UserPlus aria-hidden />
                Create account
              </Button>
            </div>
          </form>
          <p className="mt-3 flex items-start gap-2 text-xs text-muted-foreground">
            <KeyRound aria-hidden className="mt-0.5 size-3.5 shrink-0" />
            Demo only — accounts are stored in this browser. Share the email and
            password with the account holder.
          </p>
        </Panel>

        <Panel
          title="Page permissions"
          description="Choose the optional pages Admin and Branch can open. Core monitoring pages stay available."
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Page</TableHead>
                <TableHead>Admin</TableHead>
                <TableHead>Branch</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {permissionModules().map((item) => (
                <TableRow key={item.href}>
                  <TableCell>
                    <span className="inline-flex items-center gap-2 font-medium">
                      <item.icon
                        aria-hidden
                        className="size-4 text-muted-foreground"
                      />
                      {item.title}
                    </span>
                  </TableCell>
                  {(["admin", "branch"] as const).map((target) => {
                    const available = item.roles.includes(target);
                    return (
                      <TableCell key={target}>
                        {available ? (
                          <input
                            type="checkbox"
                            checked={draft[target].includes(item.href)}
                            onChange={() =>
                              togglePermission(target, item.href)
                            }
                            aria-label={`${item.title} for ${ROLE_META[target].label}`}
                            className="size-4 accent-[var(--primary)]"
                          />
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Not available
                          </span>
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="mt-3 text-xs text-muted-foreground">
            Overview, Stations, Access Logs, Device & Door and Settings stay
            available to every role. Modules hidden in Settings → Dashboard
            customization stay hidden for every role.
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              {draft.admin.length} Admin page(s) · {draft.branch.length} Branch
              page(s) selected.
            </p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={resetPermissions}>
                Reset defaults
              </Button>
              <Button size="sm" onClick={savePermissions}>
                Save permissions
              </Button>
            </div>
          </div>
        </Panel>
      </div>

      <Panel
        title="Accounts"
        description="Admin and Branch sign-ins. The Super Admin account is built in."
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Account</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Scope</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {accounts.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="text-center text-muted-foreground"
                >
                  No Admin or Branch accounts yet.
                </TableCell>
              </TableRow>
            ) : (
              accounts.map((account) => (
                <TableRow key={account.id}>
                  <TableCell>
                    <span className="font-medium">{account.name}</span>
                    <span className="block font-mono text-[11px] text-muted-foreground">
                      {account.email}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {ROLE_META[account.role].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {roleScopeLabel(account.role)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {account.createdAt}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteAccount(account)}
                      aria-label={`Remove ${account.name}`}
                    >
                      <Trash2 aria-hidden />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Panel>
    </div>
  );
}

export { UsersView };
