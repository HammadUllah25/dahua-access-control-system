"use server";

// Server Actions: GET /devices/status (header badge) and GET /devices
// (full rows used by the station and people screens). Live changes arrive
// over ws://.../ws/devices (the browser connects directly; no CORS involved).

import { backendRequest } from "@/actions/backend";

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
  changed_at?: string;
  reason?: string | null;
};

export type DeviceStatusSummary = {
  total: number;
  online: number;
  offline: number;
  pending: number;
  unknown?: number;
};

export type DeviceStatusSnapshot = {
  items: DeviceStatus[];
  summary: DeviceStatusSummary;
};

// Mirrors the backend DeviceRead schema (GET /devices).
export type DeviceListRecord = {
  id: number;
  name: string;
  station_id: number | null;
  connection_type: string;
  host: string;
  port: number;
  username: string;
  model: string | null;
  serial_number: string | null;
  mac_address: string | null;
  status: string;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  last_connected_at: string | null;
  monitoring_enabled: boolean;
  last_health_check_at: string | null;
  last_tcp_reachable_at: string | null;
  last_connect_attempt_at: string | null;
  consecutive_failures: number;
  inventory_status: string;
  last_inventory_at: string | null;
  expected_card_count: number | null;
  observed_card_count: number | null;
};

export type ServerActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

// Local backend started with backend\dahua_access_starter\run.bat
const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

export async function listDevicesAction(): Promise<
  ServerActionResult<DeviceListRecord[]>
> {
  return backendRequest<DeviceListRecord[]>("/devices");
}

export async function getDeviceStatusAction(): Promise<
  ServerActionResult<DeviceStatusSnapshot>
> {
  try {
    const res = await fetch(`${BASE_URL}/devices/status`, {
      headers: { accept: "*/*" },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });

    if (!res.ok) {
      let detail = `Error (${res.status})`;
      try {
        const errorJson = await res.json();
        detail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        detail = await res.text();
      }
      return { success: false, error: detail };
    }

    const data = (await res.json()) as DeviceStatusSnapshot;
    return { success: true, data };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error occurred";
    return {
      success: false,
      error: `Could not reach device status endpoint at ${BASE_URL}: ${message}`,
    };
  }
}
