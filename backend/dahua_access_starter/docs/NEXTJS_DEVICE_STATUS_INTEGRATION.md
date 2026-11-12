# Next.js device-status integration

This backend exposes an initial REST snapshot and a WebSocket stream. The frontend should use the REST response for the first render, then apply WebSocket updates. The WebSocket sends its own initial snapshot as well, so the example below uses the socket snapshot as the authoritative live initialization and REST as a fallback.

## Environment variables

In the Next.js project `.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WS_BASE_URL=ws://127.0.0.1:8000
```

For a deployed dashboard, point these variables at the backend's public/private API hostname and use `https://` plus `wss://` as appropriate.

## Event contract

Connect to:

```text
ws://127.0.0.1:8000/ws/devices
```

Optional single-device subscription:

```text
ws://127.0.0.1:8000/ws/devices?device_id=1
```

The first message is:

```json
{
  "type": "device.status.snapshot",
  "data": {
    "devices": [],
    "summary": {"total": 0, "online": 0, "offline": 0, "pending": 0},
    "generated_at": "2026-11-12T06:40:00+00:00"
  }
}
```

A state transition emits:

```json
{
  "type": "device.status.changed",
  "data": {
    "device_id": 1,
    "status": "online",
    "last_seen": "2026-11-12T06:40:00+00:00",
    "consecutive_failures": 0,
    "reason": "monitor_reconnected"
  }
}
```

Other messages: `device.deleted`, `heartbeat`, and `pong`. Timestamps are ISO-8601 UTC timestamps. `last_seen` represents the last successful TCP reachability check (or, if no TCP check has yet succeeded, the last successful SDK login).

## Example client hook

Create `src/hooks/use-device-status.ts` (adjust the path to the project's structure):

```tsx
"use client";

import { useEffect, useState } from "react";

export type DeviceStatus = {
  device_id: number;
  name: string;
  host: string;
  port: number;
  model: string | null;
  serial_number: string | null;
  mac_address: string | null;
  status: "online" | "offline" | "pending" | string;
  monitoring_enabled: boolean;
  last_seen: string | null;
  last_connected_at: string | null;
  last_health_check_at: string | null;
  last_tcp_reachable_at: string | null;
  consecutive_failures: number;
  last_error: string | null;
};

type StatusSummary = {
  total: number;
  online: number;
  offline: number;
  pending: number;
  unknown?: number;
};

type StatusState = { devices: DeviceStatus[]; summary: StatusSummary };

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://127.0.0.1:8000";

function summarize(devices: DeviceStatus[]): StatusSummary {
  return devices.reduce<StatusSummary>(
    (summary, device) => {
      summary.total += 1;
      if (device.status === "online") summary.online += 1;
      else if (device.status === "offline") summary.offline += 1;
      else if (device.status === "pending") summary.pending += 1;
      else summary.unknown = (summary.unknown ?? 0) + 1;
      return summary;
    },
    { total: 0, online: 0, offline: 0, pending: 0, unknown: 0 },
  );
}

export function useDeviceStatus() {
  const [state, setState] = useState<StatusState>({
    devices: [],
    summary: { total: 0, online: 0, offline: 0, pending: 0, unknown: 0 },
  });
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectDelay = 1000;
    let socketSnapshotReceived = false;

    fetch(`${API_URL}/devices/status`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Status API failed: ${response.status}`);
        return response.json();
      })
      .then((result: { items: DeviceStatus[]; summary: StatusSummary }) => {
        if (!active || socketSnapshotReceived) return;
        setState({ devices: result.items, summary: result.summary });
      })
      .catch((error) => console.error("Could not load device status", error));

    const connect = () => {
      if (!active) return;
      socket = new WebSocket(`${WS_URL}/ws/devices`);

      socket.onopen = () => {
        if (!active) return;
        setConnected(true);
        reconnectDelay = 1000;
      };

      socket.onmessage = (message) => {
        if (!active) return;
        try {
          const event = JSON.parse(message.data);
          if (event.type === "device.status.snapshot") {
            socketSnapshotReceived = true;
            setState({
              devices: event.data.devices as DeviceStatus[],
              summary: event.data.summary as StatusSummary,
            });
          } else if (event.type === "device.status.changed") {
            const updated = event.data as DeviceStatus;
            setState((current) => {
              const exists = current.devices.some((item) => item.device_id === updated.device_id);
              const devices = exists
                ? current.devices.map((item) => item.device_id === updated.device_id ? { ...item, ...updated } : item)
                : [...current.devices, updated];
              return { devices, summary: summarize(devices) };
            });
          } else if (event.type === "device.deleted") {
            const deletedId = Number(event.data.device_id);
            setState((current) => {
              const devices = current.devices.filter((item) => item.device_id !== deletedId);
              return { devices, summary: summarize(devices) };
            });
          }
          // heartbeat/pong are connection-liveness messages; no UI update is needed.
        } catch (error) {
          console.error("Invalid device WebSocket message", error);
        }
      };

      socket.onclose = () => {
        if (!active) return;
        setConnected(false);
        reconnectTimer = setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
      };

      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      active = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { ...state, connected };
}
```

## Use in a dashboard component

```tsx
"use client";

import { useDeviceStatus } from "@/hooks/use-device-status";

export function DeviceStatusPanel() {
  const { devices, summary, connected } = useDeviceStatus();

  return (
    <section>
      <p>Live connection: {connected ? "Connected" : "Reconnecting"}</p>
      <div>
        <span>Online: {summary.online}</span>
        <span>Offline: {summary.offline}</span>
        <span>Pending: {summary.pending}</span>
        <span>Total: {summary.total}</span>
      </div>
      <ul>
        {devices.map((device) => (
          <li key={device.device_id}>
            <strong>{device.name}</strong> — {device.status}
            <small>Last seen: {device.last_seen ?? "Never"}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

## Important integration notes

- Do not poll `/devices/status` every few seconds after the WebSocket is connected; use the socket for changes and REST as an initial/reconnect fallback.
- The status monitor defaults to a 10-second interval and requires two consecutive TCP failures before marking a device offline. A sudden disconnect can therefore take around 20 seconds to show as offline.
- `online` means the controller TCP port is reachable and the backend holds an SDK session. It does not mean the WebSocket connection itself is the controller health check.
- Run the backend with one Uvicorn worker. The Dahua SDK sessions and monitor are process-local.
- This starter currently has no authentication or tenant-level authorization. Keep it on a trusted network; add authorization before exposing it to the internet or allowing users to view only their own locations.
