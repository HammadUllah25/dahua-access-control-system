"use server";

// Server Action 4: POST /devices
// Registers the initialized controller with the station so the dashboard
// can monitor and manage it.

export type AddDevicePayload = {
  name: string;
  connection_type: "ip_domain";
  host: string;
  port: number;
  username: string;
  password: string;
  model: string | null;
  serial_number: string | null;
  mac_address: string | null;
  connect_now: boolean;
  monitoring_enabled: boolean;
};

// Mirrors the backend DeviceRead schema (fields used by the onboarding).
export type DeviceRecord = {
  id: number;
  name: string;
  connection_type: string;
  host: string;
  port: number;
  username: string;
  model: string | null;
  serial_number: string | null;
  mac_address: string | null;
  status: string;
  last_error: string | null;
  monitoring_enabled: boolean;
};

export type ServerActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

// Local backend started with backend\dahua_access_starter\run.bat
const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

export async function addDeviceAction(
  payload: AddDevicePayload
): Promise<ServerActionResult<DeviceRecord>> {
  try {
    const res = await fetch(`${BASE_URL}/devices`, {
      method: "POST",
      headers: {
        accept: "*/*",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      // connect_now performs an SDK login attempt, so allow extra time.
      signal: AbortSignal.timeout(45_000),
    });

    if (!res.ok) {
      let detail = `Error (${res.status})`;
      try {
        const errorJson = await res.json();
        detail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        detail = await res.text();
      }
      return {
        success: false,
        error: detail,
      };
    }

    const data = (await res.json()) as DeviceRecord;
    return {
      success: true,
      data,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error occurred";
    return {
      success: false,
      error: `Could not reach device endpoint at ${BASE_URL}: ${message}`,
    };
  }
}
