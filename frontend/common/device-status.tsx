"use client";

import { CircleCheck, CircleDashed, CircleOff, Loader2, ServerCrash } from "lucide-react";

import { useDeviceStatus } from "@/hooks/use-device-status";

const TONE = {
  online:
    "border-emerald-600/30 bg-emerald-600/10 text-emerald-700 dark:text-emerald-400",
  offline: "border-rose-600/30 bg-rose-600/10 text-rose-700 dark:text-rose-400",
  pending: "border-amber-600/30 bg-amber-600/10 text-amber-700 dark:text-amber-400",
  neutral: "border-border bg-muted/50 text-muted-foreground",
} as const;

function Dot({ tone }: { tone: keyof typeof TONE }) {
  const color =
    tone === "online"
      ? "bg-emerald-600"
      : tone === "offline"
        ? "bg-rose-600"
        : tone === "pending"
          ? "bg-amber-600"
          : "bg-muted-foreground";
  return (
    <span
      aria-hidden
      className={`size-1.5 rounded-full ${color} ${tone === "online" ? "animate-pulse" : ""}`}
    />
  );
}

function Badge({
  tone,
  icon,
  children,
  title,
}: {
  tone: keyof typeof TONE;
  icon?: React.ReactNode;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <span
      role="status"
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${TONE[tone]}`}
    >
      {icon ?? <Dot tone={tone} />}
      {children}
    </span>
  );
}

// Live controller status for the dashboard header, driven by the
// backend WebSocket (WS /ws/devices).
export function DeviceStatus() {
  const { devices, connected, ready } = useDeviceStatus();

  if (devices === null) {
    if (!ready) {
      return (
        <Badge
          tone="neutral"
          icon={<Loader2 aria-hidden className="size-3.5 animate-spin" />}
        >
          Checking controller
        </Badge>
      );
    }
    return (
      <Badge
        tone="neutral"
        icon={<ServerCrash aria-hidden className="size-3.5" />}
        title="The backend API and status socket are not reachable. Start it with backend\dahua_access_starter\run.bat"
      >
        Backend offline
      </Badge>
    );
  }

  if (devices.length === 0) {
    return (
      <Badge
        tone="offline"
        icon={<CircleOff aria-hidden className="size-3.5" />}
        title="No controller registered — the dashboard has no device to report on"
      >
        Offline
      </Badge>
    );
  }

  const online = devices.filter((d) => d.status === "online").length;
  const first = devices[0];
  // Single indicator: no counts. The station reads Online as soon as one
  // registered controller is online, so a stale/secondary offline row cannot
  // mask a healthy device. Offline only when none are online.
  const tone: keyof typeof TONE =
    online > 0
      ? "online"
      : devices.some((d) => d.status === "offline")
        ? "offline"
        : "pending";
  const label =
    tone === "online" ? "Online" : tone === "offline" ? "Offline" : "Connecting";
  const title = [
    devices.length === 1
      ? [first.name, first.host, first.last_error].filter(Boolean).join(" · ")
      : devices.map((d) => `${d.name}: ${d.status}`).join("\n"),
    connected ? null : "Live connection lost — reconnecting",
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <Badge
      tone={tone}
      icon={
        tone === "online" ? (
          <CircleCheck aria-hidden className="size-3.5" />
        ) : tone === "offline" ? (
          <CircleOff aria-hidden className="size-3.5" />
        ) : (
          <CircleDashed aria-hidden className="size-3.5" />
        )
      }
      title={title}
    >
      {label}
    </Badge>
  );
}
