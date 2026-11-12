"use client";

import { useState } from "react";
import { Bell, BellRing, Check, Mail } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { SeverityBadge, ToneBadge } from "@/components/dashboard/badges";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DEVICE, ALERTS, type Alert } from "@/lib/station-data";

const SEVERITIES = ["All", "Critical", "Warning", "Info"] as const;

const statusTone = {
  Active: "red",
  Acknowledged: "amber",
  Resolved: "green",
} as const;

function AlertsEventsView() {
  // shortcut: acknowledge/resolve is local state — the alert service lands later
  const [alerts, setAlerts] = useState<Alert[]>(ALERTS);
  const [severity, setSeverity] = useState<(typeof SEVERITIES)[number]>("All");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [inApp, setInApp] = useState(true);
  const [email, setEmail] = useState(false);

  const detail = alerts.find((a) => a.id === detailId) ?? null;
  const counts = {
    Active: alerts.filter((a) => a.status === "Active").length,
    Acknowledged: alerts.filter((a) => a.status === "Acknowledged").length,
    Resolved: alerts.filter((a) => a.status === "Resolved").length,
  };
  const filtered = alerts.filter(
    (a) => severity === "All" || a.severity === severity
  );

  const setStatus = (id: string, status: Alert["status"]) =>
    setAlerts(
      alerts.map((a) =>
        a.id === id ? { ...a, status, ackBy: status === "Active" ? null : "A. Rahman" } : a
      )
    );

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Alerts &amp; events</h2>
          <p className="text-xs text-muted-foreground">
            Exceptions that may need attention · severity mapping is defined centrally
          </p>
        </div>
        <div role="group" aria-label="Severity filter" className="inline-flex rounded-lg bg-muted p-0.5">
          {SEVERITIES.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={severity === s}
              onClick={() => setSeverity(s)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                severity === s ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* summary */}
      <div className="grid grid-cols-3 gap-3">
        {(["Active", "Acknowledged", "Resolved"] as const).map((status) => (
          <div key={status} className="card-glow rounded-lg border bg-card px-3 py-2">
            <p className="text-xs text-muted-foreground">{status}</p>
            <p className="text-xl font-semibold tabular-nums">{counts[status]}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* alert list */}
        <Panel
          title="Alerts"
          description={`${filtered.length} shown · documented event types only`}
          className="lg:col-span-2"
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Event</TableHead>
                <TableHead>Device</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((a) => (
                <TableRow key={a.id} className="cursor-pointer" onClick={() => setDetailId(a.id)}>
                  <TableCell className="font-mono text-xs">{a.ts}</TableCell>
                  <TableCell className="font-medium">{a.type}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{DEVICE.serial}</TableCell>
                  <TableCell><SeverityBadge severity={a.severity} /></TableCell>
                  <TableCell><ToneBadge tone={statusTone[a.status]}>{a.status}</ToneBadge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {filtered.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No {severity.toLowerCase()} alerts — you&apos;re all clear.
            </p>
          ) : null}
        </Panel>

        {/* notification preferences */}
        <Panel title="Notification preferences" description="Only implemented channels are shown">
          <label className="flex items-center justify-between gap-3 border-b py-2 text-sm">
            <span className="inline-flex items-center gap-2">
              <Bell aria-hidden className="size-4 text-muted-foreground" />
              In-app alerts
            </span>
            <input
              type="checkbox"
              checked={inApp}
              onChange={(e) => setInApp(e.target.checked)}
              className="size-4 accent-[var(--primary)]"
            />
          </label>
          <label className="flex items-center justify-between gap-3 border-b py-2 text-sm">
            <span className="inline-flex items-center gap-2">
              <Mail aria-hidden className="size-4 text-muted-foreground" />
              Email digests
            </span>
            <input
              type="checkbox"
              checked={email}
              onChange={(e) => setEmail(e.target.checked)}
              className="size-4 accent-[var(--primary)]"
            />
          </label>
          <p className="mt-2 text-xs text-muted-foreground">
            Email delivery requires SMTP configuration on the platform side
            before it takes effect.
          </p>
        </Panel>
      </div>

      {/* alert detail drawer */}
      <Sheet open={detail !== null} onOpenChange={(open) => !open && setDetailId(null)}>
        <SheetContent className="w-full sm:max-w-md">
          {detail ? (
            <SheetHeader className="mt-2 gap-4 text-left">
              <SheetTitle className="flex items-center gap-2">
                <BellRing aria-hidden className="size-4 text-led-amber" />
                {detail.type}
              </SheetTitle>
              <SheetDescription>
                {detail.ts} · {DEVICE.model} ({DEVICE.serial})
              </SheetDescription>
              <p className="text-sm">{detail.detail}</p>
              <div className="flex flex-wrap gap-2">
                <SeverityBadge severity={detail.severity} />
                <ToneBadge tone={statusTone[detail.status]}>{detail.status}</ToneBadge>
              </div>
              {detail.ackBy ? (
                <p className="text-xs text-muted-foreground">
                  Acknowledged by {detail.ackBy} — stored in the audit trail.
                </p>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-2">
                <Button size="sm" onClick={() => setStatus(detail.id, "Acknowledged")} disabled={detail.status !== "Active"}>
                  <Check aria-hidden />
                  Acknowledge
                </Button>
                <Button size="sm" variant="outline" onClick={() => setStatus(detail.id, "Resolved")}>
                  Resolve
                </Button>
              </div>
              <p className="mt-auto text-xs text-muted-foreground">
                Actor, timestamp and resolution note are recorded in the
                application audit log.
              </p>
            </SheetHeader>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export { AlertsEventsView };
