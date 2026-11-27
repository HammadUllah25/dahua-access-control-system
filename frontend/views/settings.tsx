"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, MonitorSmartphone, Plug, SlidersHorizontal } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
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
import { useSession } from "@/components/role-provider";
import { customisableModules } from "@/lib/nav";
import {
  ROLE_META,
  clearRoleCookie,
  clearUserCookie,
  roleScopeLabel,
  setHiddenModulesCookie,
} from "@/lib/roles";
import { DEVICE, STATION } from "@/lib/station-data";

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b py-2 text-sm last:border-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={`font-medium ${mono ? "font-mono text-xs" : ""}`}>{value}</dd>
    </div>
  );
}

function SettingsView() {
  const router = useRouter();
  const { role, hidden, user } = useSession();
  const meta = ROLE_META[role];
  const [timezone, setTimezone] = useState(STATION.timezone);
  const [dateFormat, setDateFormat] = useState("DD MMM YYYY");
  const [density, setDensity] = useState("Comfortable");
  const [hiddenModules, setHiddenModules] = useState(hidden);
  const modules = customisableModules();

  const toggleModule = (href: string) => {
    const next = hiddenModules.includes(href)
      ? hiddenModules.filter((item) => item !== href)
      : [...hiddenModules, href];
    setHiddenModules(next);
    setHiddenModulesCookie(next);
    router.refresh();
  };

  const resetModules = () => {
    setHiddenModules([]);
    setHiddenModulesCookie([]);
    router.refresh();
  };

  const signOut = () => {
    clearRoleCookie();
    clearUserCookie();
    router.push("/login");
  };

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Settings</h2>
          <p className="text-xs text-muted-foreground">
            {meta.label} preferences and your own account · {roleScopeLabel(role)}
          </p>
        </div>
        <Badge variant="outline">{meta.label}</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* role and scope */}
        <Panel
          title="Role & scope"
          description="What this account can monitor and manage"
        >
          <dl>
            <Row label="Role" value={<Badge variant="outline">{meta.label}</Badge>} />
            <Row label="Scope" value={roleScopeLabel(role)} />
            <Row label="Access" value={meta.description} />
          </dl>
        </Panel>

        {/* station profile */}
        <Panel
          title="Station profile"
          description={
            role === "superadmin"
              ? "Read-only — station records are managed centrally"
              : "Read-only — station records are managed by the Super Admin"
          }
        >
          <dl>
            <Row label="Station ID" value={STATION.id} mono />
            <Row label="Name" value={STATION.name} />
            <Row label="Address" value={STATION.address} />
            <Row label="Contact" value={STATION.contact} mono />
          </dl>
        </Panel>

        {/* admin profile */}
        <Panel
          title={`${meta.label} profile`}
          description={
            role === "superadmin"
              ? "Your Super Admin account"
              : "Your account — role elevation is not permitted"
          }
        >
          <dl>
            <Row label="Name" value={user.name} />
            <Row label="Email" value={user.email} mono />
            <Row label="Role" value={<Badge variant="outline">{meta.label}</Badge>} />
          </dl>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">New password</span>
              <Input type="password" placeholder="••••••••" />
            </label>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">Confirm password</span>
              <Input type="password" placeholder="••••••••" />
            </label>
          </div>
          <Button size="sm" variant="outline" className="mt-3">
            Update password
          </Button>
        </Panel>

        {/* display preferences */}
        <Panel title="Display preferences">
          <div className="grid gap-3 text-sm">
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">Timezone (station location)</span>
              <Select value={timezone} onValueChange={(v) => v && setTimezone(v)}>
                <SelectTrigger className="w-full" size="sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Asia/Dubai (GMT+4)">Asia/Dubai (GMT+4)</SelectItem>
                  <SelectItem value="Asia/Karachi (GMT+5)">Asia/Karachi (GMT+5)</SelectItem>
                  <SelectItem value="Asia/Riyadh (GMT+3)">Asia/Riyadh (GMT+3)</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">Date format</span>
              <Select value={dateFormat} onValueChange={(v) => v && setDateFormat(v)}>
                <SelectTrigger className="w-full" size="sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="DD MMM YYYY">DD MMM YYYY</SelectItem>
                  <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                  <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">Table density</span>
              <Select value={density} onValueChange={(v) => v && setDensity(v)}>
                <SelectTrigger className="w-full" size="sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Comfortable">Comfortable</SelectItem>
                  <SelectItem value="Compact">Compact</SelectItem>
                </SelectContent>
              </Select>
            </label>
          </div>
        </Panel>

        {/* security / session */}
        <Panel title="Security & sessions" description="Active sessions for your account">
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2">
              <span className="inline-flex items-center gap-2">
                <MonitorSmartphone aria-hidden className="size-4 text-muted-foreground" />
                This browser · Dubai, AE
              </span>
              <ToneBadge tone="green">Current</ToneBadge>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2">
              <span className="inline-flex items-center gap-2">
                <MonitorSmartphone aria-hidden className="size-4 text-muted-foreground" />
                Chrome on Windows · last active 2 h ago
              </span>
              <Button variant="outline" size="sm" onClick={signOut}>
                <LogOut aria-hidden />
                Sign out
              </Button>
            </div>
          </div>
        </Panel>
      </div>

      {/* super-admin module customisation */}
      {role === "superadmin" ? (
        <Panel
          title="Dashboard customization"
          description="Choose which modules appear for every role. Overview, Stations, Access Logs, Door & Sensor, Settings and Users & Roles always stay visible."
          action={
            <SlidersHorizontal aria-hidden className="size-4 text-muted-foreground" />
          }
        >
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {modules.map((item) => {
              const visible = !hiddenModules.includes(item.href);
              return (
                <label
                  key={item.href}
                  className="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={visible}
                    onChange={() => toggleModule(item.href)}
                    className="size-4 accent-[var(--primary)]"
                  />
                  <item.icon aria-hidden className="size-4 text-muted-foreground" />
                  <span>{item.title}</span>
                </label>
              );
            })}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              Applies to every role in this workspace. {hiddenModules.length} module(s) hidden.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={resetModules}
              disabled={hiddenModules.length === 0}
            >
              Reset modules
            </Button>
          </div>
        </Panel>
      ) : null}

      {/* integration information */}
      <Panel
        title="Integration"
        description="Controller model and integration state — secrets, keys and passwords are never shown"
        action={<Plug aria-hidden className="size-4 text-muted-foreground" />}
      >
        <dl className="grid gap-x-8 sm:grid-cols-2">
          <div>
            <Row label="Controller model" value={DEVICE.model} />
            <Row label="Serial" value={DEVICE.serial} mono />
            <Row label="Firmware" value={DEVICE.firmware} mono />
          </div>
          <div>
            <Row label="Integration state" value={<ToneBadge tone="green">Connected via SmartPSS Lite</ToneBadge>} />
            <Row label="Connection" value={DEVICE.connection} />
            <Row label="Support reference" value="DHI-ASI1201E feature sheet · 10 Nov 2026" />
          </div>
        </dl>
      </Panel>
    </div>
  );
}

export { SettingsView };
