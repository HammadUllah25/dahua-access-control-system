"use server";

// Server Action 2: POST /device-initialization/discover
// Discovers uninitialized Dahua devices on the given local IP with custom wait seconds.

// Mirrors the backend DiscoveredDeviceRead schema (extra="forbid").
export type DiscoveredDevice = {
  ip_address: string;
  tcp_port: number;
  http_port: number | null;
  mac_address: string;
  serial_number: string | null;
  model: string | null;
  device_type: string | null;
  subnet_mask: string | null;
  gateway: string | null;
  local_ip: string;
  init_status_raw: number;
  initialization_state: string;
  password_reset_flags: number;
  supports_phone_reset: boolean;
  supports_email_reset: boolean;
};

export type DiscoverResponse = {
  count: number;
  searched_local_ips: string[];
  wait_seconds: number;
  devices: DiscoveredDevice[];
};

export type DiscoverPayload = {
  local_ip: string;
  wait_seconds: number;
};

export type ServerActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string; raw?: string };

// Local backend started with backend\dahua_access_starter\run.bat
const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

export async function discoverDevicesAction(
  payload: DiscoverPayload
): Promise<ServerActionResult<DiscoverResponse>> {
  try {
    const trimmedIp = payload.local_ip ? payload.local_ip.trim() : "";
    // backend validates wait_seconds in [2, 15]
    const waitSeconds = Math.min(
      Math.max(typeof payload.wait_seconds === "number" ? payload.wait_seconds : 5, 2),
      15
    );

    if (!trimmedIp) {
      return {
        success: false,
        error: "local_ip must be provided as a valid IPv4 address.",
      };
    }

    const res = await fetch(`${BASE_URL}/device-initialization/discover`, {
      method: "POST",
      headers: {
        accept: "*/*",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        local_ip: trimmedIp,
        wait_seconds: waitSeconds,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(waitSeconds * 1000 + 20_000),
    });

    if (!res.ok) {
      // Return the backend body verbatim so the UI can toast exactly what it said.
      const raw = await res.text();
      let detail = `Error (${res.status})`;
      try {
        const errorJson = JSON.parse(raw) as { detail?: string };
        detail = errorJson.detail || raw || detail;
      } catch {
        detail = raw || detail;
      }
      return {
        success: false,
        error: detail,
        raw: `HTTP ${res.status} — ${raw || detail}`,
      };
    }

    const data = (await res.json()) as DiscoverResponse;
    return {
      success: true,
      data,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error occurred";
    return {
      success: false,
      error: `Could not reach discover endpoint at ${BASE_URL}: ${message}`,
    };
  }
}

