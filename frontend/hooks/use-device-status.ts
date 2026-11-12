"use client";

import { useEffect, useState } from "react";

import {
  getDeviceStatusAction,
  type DeviceStatus,
} from "@/actions/get-devices";

// Live device status: REST snapshot first (through the Next server), then
// WebSocket events from the backend. See backend docs
// NEXTJS_DEVICE_STATUS_INTEGRATION.md for the event contract.
const WS_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://127.0.0.1:8000";

type StatusEvent =
  | { type: "device.status.snapshot"; data: { devices: DeviceStatus[] } }
  | { type: "device.status.changed"; data: DeviceStatus }
  | { type: "device.deleted"; data: { device_id: number } }
  | { type: "heartbeat" | "pong"; data: unknown };

export function useDeviceStatus() {
  const [devices, setDevices] = useState<DeviceStatus[] | null>(null);
  const [connected, setConnected] = useState(false);
  // true once the first snapshot attempt (REST or socket) has settled
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectDelay = 1000;
    let gotSocketSnapshot = false;

    // Fallback for the first render; ignored once the socket snapshot lands.
    getDeviceStatusAction().then((res) => {
      if (!active) return;
      if (res.success && !gotSocketSnapshot) setDevices(res.data.items);
      setReady(true);
    });

    const connect = () => {
      if (!active) return;
      socket = new WebSocket(`${WS_URL}/ws/devices`);

      socket.onopen = () => {
        if (!active) return;
        setConnected(true);
        setReady(true);
        reconnectDelay = 1000;
      };

      socket.onmessage = (message) => {
        if (!active) return;
        let event: StatusEvent;
        try {
          event = JSON.parse(message.data) as StatusEvent;
        } catch {
          return;
        }

        if (event.type === "device.status.snapshot") {
          gotSocketSnapshot = true;
          setDevices(event.data.devices);
        } else if (event.type === "device.status.changed") {
          const updated = event.data;
          setDevices((current) => {
            const list = current ?? [];
            const exists = list.some((d) => d.device_id === updated.device_id);
            return exists
              ? list.map((d) =>
                  d.device_id === updated.device_id ? { ...d, ...updated } : d
                )
              : [...list, updated];
          });
        } else if (event.type === "device.deleted") {
          const deletedId = Number(event.data.device_id);
          setDevices((current) =>
            (current ?? []).filter((d) => d.device_id !== deletedId)
          );
        }
        // heartbeat/pong only prove the socket is alive.
      };

      socket.onclose = () => {
        if (!active) return;
        setConnected(false);
        reconnectTimer = setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30_000);
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

  return { devices, connected, ready };
}
