"use server";

// Server Action 1: GET /device-initialization/interfaces
// Lists active local IPv4 addresses available for LAN discovery.

export type InterfaceItem = {
  ip_address: string;
};

export type ServerActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

// Local backend started with backend\dahua_access_starter\run.bat
const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

export async function getInterfacesAction(): Promise<ServerActionResult<InterfaceItem[]>> {
  try {
    const res = await fetch(`${BASE_URL}/device-initialization/interfaces`, {
      method: "GET",
      headers: {
        accept: "*/*",
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });

    if (!res.ok) {
      const errText = await res.text();
      return {
        success: false,
        error: `Failed to fetch interfaces (${res.status}): ${errText}`,
      };
    }

    const data = (await res.json()) as InterfaceItem[];
    return {
      success: true,
      data,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error occurred";
    return {
      success: false,
      error: `Could not connect to device server at ${BASE_URL}: ${message}`,
    };
  }
}

