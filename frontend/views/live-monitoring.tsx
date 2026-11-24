"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { DoorClosed, Radio, ScrollText, ServerCog } from "lucide-react";

import {
  listAccessEventsAction,
  type AccessEventRecord,
} from "@/actions/access-events";
import { listDevicesAction, type DeviceListRecord } from "@/actions/get-devices";
import { Panel } from "@/components/dashboard/panel";
import { ResultBadge } from "@/components/dashboard/badges";
import { RemoteUnlock } from "@/components/device/remote-unlock";
import { Button } from "@/components/ui/button";
import { Led, type LedStatus } from "@/common/led";
import {
  eventTime,
  maskCard,
  personLabel,
  reasonLabel,
  resultLabel,
} from "@/lib/event-format";
import { fmtDay, fmtTimeSec } from "@/lib/station-data";

const FILTERS = ["All", "Granted", "Denied"] as const;
type FeedFilter = (typeof FILTERS)[number];
// shortcut: polls every 5 s because /ws/devices carries device status only; push access events over the socket to drop polling.
const POLL_MS = 5_000;

const ledFor = (status: string): LedStatus =>
  status === "online" ? "online" : status === "offline" ? "offline" : "pending";

function LiveMonitoringView() {
  const [filter, setFilter] = useState<FeedFilter>("All");
  const [events, setEvents] = useState<AccessEventRecord[]>([]);
  const [devices, setDevices] = useState<DeviceListRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    const [eventRes, deviceRes] = await Promise.all([
      listAccessEventsAction({ limit: 50 }),
      listDevicesAction(),
    ]);
    if (eventRes.success) setEvents(eventRes.data);
    if (deviceRes.success) setDevices(deviceRes.data);
    setError(
      !eventRes.success ? eventRes.error : !deviceRes.success ? deviceRes.error : null
    );
    setLoaded(true);
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  const feed = events
    .filter((e) => filter === "All" || resultLabel(e) === filter)
    .slice(0, 20);
  const online = devices.filter((d) => d.status === "online");

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
            {error
              ? `Backend unreachable — ${error}`
              : `${online.length} of ${devices.length} controller(s) online · refreshes every 5 s`}
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
          <ul className="divide-y" aria-live="polite">
            {feed.map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">
                    {fmtDay(eventTime(e))} {fmtTimeSec(eventTime(e))}
                  </span>
                  <span className="truncate">{personLabel(e)}</span>
                  <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
                    {maskCard(e.card_number)}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {reasonLabel(e) ? (
                    <span className="hidden text-xs text-muted-foreground md:inline">{reasonLabel(e)}</span>
                  ) : null}
                  <ResultBadge result={resultLabel(e)} />
                </div>
              </li>
            ))}
          </ul>
          {loaded && feed.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No {filter === "All" ? "" : `${filter.toLowerCase()} `}events received yet.
            </p>
          ) : null}
        </Panel>

        <div className="flex flex-col gap-4">
          {/* door status tile */}
          <Panel title="Door status" description="Physical state from the wired door contact">
            <div className="flex items-center gap-3 text-sm font-medium">
              <DoorClosed aria-hidden className="size-5 text-muted-foreground" />
              Not reported
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              The backend does not capture door-contact events yet; check the sensor setting in Device &amp; Door.
            </p>
          </Panel>

          {/* controller status tile */}
          <Panel title="Controllers" description="Connection state reported by the backend monitor">
            <ul className="flex flex-col gap-3">
              {devices.map((d) => (
                <li key={d.id} className="flex flex-col gap-2">
                  <div className="flex items-center gap-3 text-sm font-medium">
                    <ServerCog aria-hidden className="size-5 text-muted-foreground" />
                    {d.name}
                    <span className="text-xs font-normal capitalize text-muted-foreground">{d.status}</span>
                    <Led status={ledFor(d.status)} className="ml-auto" />
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">
                    {d.model ?? "Controller"} · {d.serial_number ?? d.host}
                  </p>
                  {d.status === "online" ? (
                    <RemoteUnlock deviceId={d.id} onDone={() => void load()} />
                  ) : null}
                </li>
              ))}
            </ul>
            {loaded && devices.length === 0 ? (
              <p className="text-sm text-muted-foreground">No controllers registered.</p>
            ) : null}
          </Panel>

          {/* quick actions */}
          <Panel title="Quick actions">
            <div className="flex flex-col gap-2">
              <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/logs" />}>
                <ScrollText aria-hidden />
                Open Access Logs
              </Button>
              <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/device" />}>
                <ServerCog aria-hidden />
                Open Device &amp; Door
              </Button>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

export { LiveMonitoringView };
