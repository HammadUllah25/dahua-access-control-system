"use server";

// Server Action: PUT /devices/{id}
// Refreshes an already-registered controller instead of failing on the
// backend's duplicate serial/MAC check (e.g. re-running onboarding after the
// device password changed).

import type { DeviceRecord } from "@/actions/add-device";

export type UpdateDevicePayload = {
  name?: string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  monitoring_enabled?: boolean;
  reconnect?: boolean;
};

export type ServerActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string; raw?: string };

// Local backend started with backend\dahua_access_starter\run.bat
const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

export async function updateDeviceAction(
  deviceId: number,
  payload: UpdateDevicePayload
): Promise<ServerActionResult<DeviceRecord>> {
  try {
    const res = await fetch(`${BASE_URL}/devices/${deviceId}`, {
      method: "PUT",
      headers: {
        accept: "*/*",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      // reconnect performs an SDK login attempt, so allow extra time.
      signal: AbortSignal.timeout(45_000),
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

    const data = (await res.json()) as DeviceRecord;
    return { success: true, data };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error occurred";
    return {
      success: false,
      error: `Could not reach update device endpoint at ${BASE_URL}: ${message}`,
    };
  }
}
