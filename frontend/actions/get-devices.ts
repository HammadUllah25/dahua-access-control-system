"use server";

// Server Action: GET /devices/status
// Initial credential-free snapshot for the header badge. Live changes arrive
// over ws://.../ws/devices (the browser connects directly; no CORS involved).

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

export type ServerActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

// Local backend started with backend\dahua_access_starter\run.bat
const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

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
