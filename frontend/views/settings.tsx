"use client";

import { useState } from "react";
import { LogOut, MonitorSmartphone, Plug } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  const [timezone, setTimezone] = useState("Asia/Dubai (GMT+4)");
  const [dateFormat, setDateFormat] = useState("DD MMM YYYY");
  const [density, setDensity] = useState("Comfortable");

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Settings</h2>
        <p className="text-xs text-muted-foreground">
          Station-level preferences and your own account · managed centrally by the Super Admin
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* station profile */}
        <Panel title="Station profile" description="Read-only — station records are managed by the Super Admin">
          <dl>
            <Row label="Station ID" value={STATION.id} mono />
            <Row label="Name" value={STATION.name} />
            <Row label="Address" value={STATION.address} />
            <Row label="Contact" value={STATION.contact} mono />
          </dl>
        </Panel>

        {/* admin profile */}
        <Panel title="Admin profile" description="Your station admin account — role elevation is not permitted">
          <dl>
            <Row label="Name" value={STATION.admin.name} />
            <Row label="Email" value={STATION.admin.email} mono />
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
              <Button variant="outline" size="sm" render={<a />}>
                <LogOut aria-hidden />
                Sign out
              </Button>
            </div>
          </div>
        </Panel>
      </div>

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
