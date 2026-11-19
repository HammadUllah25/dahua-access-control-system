"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Bell, Clock3 } from "lucide-react";

import { SeverityBadge } from "@/components/dashboard/badges";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ALERTS } from "@/lib/station-data";

function NotificationsMenu() {
  const [open, setOpen] = useState(false);
  const items = useMemo(() => ALERTS.slice(0, 3), []);
  const activeCount = useMemo(
    () => ALERTS.filter((alert) => alert.status === "Active").length,
    []
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            variant="ghost"
            size="icon-sm"
            className="relative"
            aria-label={
              activeCount > 0
                ? `Notifications, ${activeCount} active`
                : "Notifications"
            }
          />
        }
      >
        <Bell aria-hidden className="size-4" />
        {activeCount > 0 ? (
          <span className="absolute -right-0.5 -top-0.5 flex min-w-4 h-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-none text-white">
            {activeCount > 9 ? "9+" : activeCount}
          </span>
        ) : null}
      </PopoverTrigger>

      <PopoverContent align="end" className="w-[340px] p-0">
        <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
          <p className="text-sm font-semibold">Notifications</p>
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {activeCount} active
          </span>
        </div>

        {items.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            No notifications
          </div>
        ) : (
          <div className="divide-y divide-border/60">
            {items.map((alert) => (
              <div key={alert.id} className="space-y-1.5 px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-start gap-2">
                    <span
                      aria-hidden
                      className={`mt-1.5 size-2 shrink-0 rounded-full ${
                        alert.status === "Active"
                          ? "bg-destructive"
                          : alert.status === "Acknowledged"
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                      }`}
                    />
                    <p className="truncate text-sm font-medium leading-tight">
                      {alert.type}
                    </p>
                  </div>
                  <SeverityBadge severity={alert.severity} />
                </div>
                <p className="pl-4 text-xs leading-relaxed text-muted-foreground line-clamp-2">
                  {alert.detail}
                </p>
                <p className="inline-flex items-center gap-1 pl-4 font-mono text-[11px] text-muted-foreground">
                  <Clock3 aria-hidden className="size-3" />
                  {alert.ts}
                </p>
              </div>
            ))}
          </div>
        )}

        <div className="border-t border-border/60 p-2">
          <Button
            className="w-full"
            size="sm"
            nativeButton={false}
            render={<Link href="/notifications" onClick={() => setOpen(false)} />}
          >
            View all
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export { NotificationsMenu };
