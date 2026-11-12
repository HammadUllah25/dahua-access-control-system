"use client";

import { useState } from "react";
import Link from "next/link";
import { DoorClosed, Radio, ScrollText, ServerCog } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { ResultBadge } from "@/components/dashboard/badges";
import { Button } from "@/components/ui/button";
import { Led } from "@/common/led";
import {
  ACCESS_EVENTS,
  DEVICE,
  PEOPLE,
  fmtDay,
  fmtTimeSec,
} from "@/lib/station-data";

const FILTERS = ["All", "Granted", "Denied"] as const;
type FeedFilter = (typeof FILTERS)[number];

function LiveMonitoringView() {
  const [filter, setFilter] = useState<FeedFilter>("All");
  const feed = ACCESS_EVENTS.filter(
    (e) => filter === "All" || e.result === filter
  ).slice(0, 20);

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      {/* live status header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-led-green/25 bg-led-green/10 px-2.5 py-0.5 text-xs font-medium text-led-green">
            <Radio aria-hidden className="size-3 motion-safe:animate-pulse" />
            Live
          </span>
          <p className="text-xs text-muted-foreground">
            {DEVICE.online
              ? `Controller online · last communication ${DEVICE.lastSeen}`
              : "Controller offline — feed is stale"}
          </p>
        </div>
        {/* event filters */}
        <div
          role="group"
          aria-label="Event filter"
          className="inline-flex rounded-lg bg-muted p-0.5"
        >
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={filter === f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                filter === f
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* latest scan feed */}
        <Panel
          title="Latest scans"
          description="Chronological stream of card authentication attempts"
          className="lg:col-span-2"
        >
          <ul className="divide-y">
            {feed.map((e) => {
              const person = PEOPLE.find((p) => p.id === e.personId);
              return (
                <li key={e.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="font-mono text-xs text-muted-foreground">
                      {fmtDay(e.ts)} {fmtTimeSec(e.ts)}
                    </span>
                    <span className="truncate">{person ? person.name : "Unresolved card"}</span>
                    <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
                      {e.maskedCard}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {e.reason ? (
                      <span className="hidden text-xs text-muted-foreground md:inline">{e.reason}</span>
                    ) : null}
                    <ResultBadge result={e.result} />
                  </div>
                </li>
              );
            })}
          </ul>
          {feed.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No {filter.toLowerCase()} events in the retained window.
            </p>
          ) : null}
        </Panel>

        <div className="flex flex-col gap-4">
          {/* door status tile */}
          <Panel title="Door status" description="Physical state from the wired door contact">
            <div className="flex items-center gap-3 text-sm font-medium">
              <DoorClosed aria-hidden className="size-5 text-muted-foreground" />
              {DEVICE.doorContact}
              <span className="ml-auto text-xs font-normal text-muted-foreground">
                {DEVICE.doorContactWired ? "sensor wired" : "unknown — no sensor"}
              </span>
            </div>
          </Panel>

          {/* controller status tile */}
          <Panel title="Controller" description="Connection state from the connected client">
            <div className="flex items-center gap-3 text-sm font-medium">
              <ServerCog aria-hidden className="size-5 text-muted-foreground" />
              {DEVICE.online ? "Online" : "Offline"}
              <Led status={DEVICE.online ? "online" : "offline"} className="ml-auto" />
            </div>
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              {DEVICE.model} · {DEVICE.serial}
            </p>
          </Panel>

          {/* quick actions */}
          <Panel title="Quick actions">
            <div className="flex flex-col gap-2">
              <Button variant="outline" size="sm" render={<Link href="/logs" />}>
                <ScrollText aria-hidden />
                Open Access Logs
              </Button>
              <Button variant="outline" size="sm" render={<Link href="/device" />}>
                <ServerCog aria-hidden />
                Open Device &amp; Door
              </Button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              No remote unlock action is exposed by default.
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}

export { LiveMonitoringView };
