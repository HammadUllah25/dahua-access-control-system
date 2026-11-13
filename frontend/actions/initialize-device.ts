"use server";

// Server Action 3: POST /device-initialization/initialize
// Creates the first admin account on the uninitialized Dahua controller.

// cellphone/email are optional (str | None = None) in the backend
// DeviceInitializeRequest and are not collected during onboarding.
export type InitializeDevicePayload = {
  mac_address: string;
  local_ip: string;
  username: string;
  password: string;
  confirm_password: string;
};

// Mirrors the backend DeviceInitializeResponse schema.
export type DeviceInitializeResponse = {
  success: boolean;
  message: string;
  mac_address: string;
  local_ip: string;
  device_ip: string;
  tcp_port: number;
  serial_number: string | null;
  model: string | null;
  next_step: string;
};

export type ServerActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string; raw?: string };

// Local backend started with backend\dahua_access_starter\run.bat
const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

export async function initializeDeviceAction(
  payload: InitializeDevicePayload
): Promise<ServerActionResult<{ message: string; next_step: string }>> {
  try {
    const res = await fetch(`${BASE_URL}/device-initialization/initialize`, {
      method: "POST",
      headers: {
        accept: "*/*",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
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

    const data = (await res.json()) as DeviceInitializeResponse;
    return {
      success: true,
      data: {
        message: data.message || "Device initialized successfully.",
        next_step: data.next_step || "",
      },
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error occurred";
    return {
      success: false,
      error: `Could not reach initialize endpoint at ${BASE_URL}: ${message}`,
    };
  }
}

