"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Bell, Check, CheckCheck, Clock3, DoorOpen } from "lucide-react";

import { SeverityBadge, ToneBadge } from "@/components/dashboard/badges";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ALERTS, DEVICE, type Alert } from "@/lib/station-data";

const STATUS_TONE = {
  Active: "red",
  Acknowledged: "amber",
  Resolved: "green",
} as const;

type Filter = "all" | Alert["status"];

function NotificationsView() {
  const [alerts, setAlerts] = useState<Alert[]>(ALERTS);
  const [tab, setTab] = useState<Filter>("all");

  const counts = useMemo(
    () => ({
      all: alerts.length,
      active: alerts.filter((alert) => alert.status === "Active").length,
      acknowledged: alerts.filter(
        (alert) => alert.status === "Acknowledged"
      ).length,
      resolved: alerts.filter((alert) => alert.status === "Resolved").length,
    }),
    [alerts]
  );

  const filtered = useMemo(
    () => alerts.filter((alert) => (tab === "all" ? true : alert.status === tab)),
    [alerts, tab]
  );

  const setStatus = (id: string, status: Alert["status"]) => {
    setAlerts((current) =>
      current.map((alert) =>
        alert.id === id
          ? {
              ...alert,
              status,
              ackBy: status === "Active" ? null : "A. Rahman",
            }
          : alert
      )
    );
  };

  const acknowledgeAll = () => {
    setAlerts((current) =>
      current.map((alert) =>
        alert.status === "Active"
          ? { ...alert, status: "Acknowledged", ackBy: "A. Rahman" }
          : alert
      )
    );
  };

  return (
    <div className="flex flex-col gap-5 p-4 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold tracking-tight">Notifications</h2>
          <p className="text-sm text-muted-foreground">
            Alerts for {DEVICE.doorName} · {DEVICE.serial}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={acknowledgeAll}
            disabled={counts.active === 0}
          >
            <CheckCheck aria-hidden />
            Acknowledge all
          </Button>
          <Button
            size="sm"
            variant="ghost"
            nativeButton={false}
            render={<Link href="/alerts" />}
          >
            Alerts &amp; events
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden py-0 gap-0">
        <Tabs
          value={tab}
          onValueChange={(value) => setTab(value as Filter)}
          className="gap-0"
        >
          <div className="border-b border-border/60 px-2 sm:px-4">
            <TabsList className="h-auto w-full justify-start gap-1 overflow-x-auto rounded-none bg-transparent p-0">
              <TabsTrigger
                value="all"
                className="h-auto rounded-none border-b-2 border-transparent px-3 py-3 text-sm data-selected:border-primary data-selected:bg-transparent data-selected:text-foreground data-selected:shadow-none"
              >
                All
                <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[11px] font-medium leading-none text-muted-foreground">
                  {counts.all}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="Active"
                className="h-auto rounded-none border-b-2 border-transparent px-3 py-3 text-sm data-selected:border-primary data-selected:bg-transparent data-selected:text-foreground data-selected:shadow-none"
              >
                Active
                <span
                  className={`ml-1.5 rounded-full px-1.5 py-0.5 text-[11px] font-medium leading-none ${
                    counts.active > 0
                      ? "bg-destructive/10 text-destructive"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {counts.active}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="Acknowledged"
                className="h-auto rounded-none border-b-2 border-transparent px-3 py-3 text-sm data-selected:border-primary data-selected:bg-transparent data-selected:text-foreground data-selected:shadow-none"
              >
                Acknowledged
                <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[11px] font-medium leading-none text-muted-foreground">
                  {counts.acknowledged}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="Resolved"
                className="h-auto rounded-none border-b-2 border-transparent px-3 py-3 text-sm data-selected:border-primary data-selected:bg-transparent data-selected:text-foreground data-selected:shadow-none"
              >
                Resolved
                <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[11px] font-medium leading-none text-muted-foreground">
                  {counts.resolved}
                </span>
              </TabsTrigger>
            </TabsList>
          </div>

          {filtered.length === 0 ? (
            <CardContent className="flex flex-col items-center gap-2 py-14 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-muted">
                <Bell aria-hidden className="size-5 text-muted-foreground" />
              </span>
              <p className="text-sm font-medium">No notifications</p>
              <p className="text-sm text-muted-foreground">
                Nothing to show in this tab.
              </p>
            </CardContent>
          ) : (
            <div className="divide-y divide-border/60">
              {filtered.map((alert) => (
                <div
                  key={alert.id}
                  className={`flex gap-3 p-4 transition-colors hover:bg-muted/30 sm:gap-4 sm:p-5 ${
                    alert.status === "Active" ? "bg-primary/[0.03]" : ""
                  }`}
                >
                  <span
                    className={`mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl border ${
                      alert.status === "Active"
                        ? "border-destructive/20 bg-destructive/10 text-destructive"
                        : alert.status === "Acknowledged"
                          ? "border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                    }`}
                  >
                    {alert.type.toLowerCase().includes("gate") ||
                    alert.type.toLowerCase().includes("door") ? (
                      <DoorOpen aria-hidden className="size-4" />
                    ) : alert.status === "Resolved" ? (
                      <Check aria-hidden className="size-4" />
                    ) : (
                      <Bell aria-hidden className="size-4" />
                    )}
                  </span>

                  <div className="min-w-0 flex-1 space-y-2.5">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 space-y-1">
                        <p className="text-sm font-semibold leading-tight sm:text-[15px]">
                          {alert.type}
                        </p>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                          <span className="inline-flex items-center gap-1 font-mono">
                            <Clock3 aria-hidden className="size-3.5" />
                            {alert.ts}
                          </span>
                          <span>Washroom Entry · Reader 1</span>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <SeverityBadge severity={alert.severity} />
                        <ToneBadge tone={STATUS_TONE[alert.status]}>
                          {alert.status}
                        </ToneBadge>
                      </div>
                    </div>

                    <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
                      {alert.detail}
                    </p>

                    <div className="flex flex-wrap items-center gap-2">
                      {alert.status === "Active" ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setStatus(alert.id, "Acknowledged")}
                        >
                          <Check aria-hidden />
                          Acknowledge
                        </Button>
                      ) : null}
                      {alert.status !== "Resolved" ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setStatus(alert.id, "Resolved")}
                        >
                          Mark resolved
                        </Button>
                      ) : null}
                      {alert.ackBy ? (
                        <span className="text-xs text-muted-foreground">
                          Acknowledged by {alert.ackBy}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Tabs>
      </Card>
    </div>
  );
}

export { NotificationsView };
