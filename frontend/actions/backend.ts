// Shared server-side helper for the FastAPI backend. Not a Server Action file:
// it only runs inside the action modules that import it.

export type ActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string; raw?: string };

const BASE_URL = process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000";

export async function backendRequest<T>(
  path: string,
  init: RequestInit & { timeoutMs?: number } = {}
): Promise<ActionResult<T>> {
  const { timeoutMs = 20_000, ...request } = init;
  const headers = new Headers(request.headers);
  headers.set("accept", "*/*");
  if (request.body && !headers.has("content-type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...request,
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });

    if (!res.ok) {
      const raw = await res.text();
      let detail = `Error (${res.status})`;
      try {
        const errorJson = JSON.parse(raw) as { detail?: unknown };
        if (typeof errorJson.detail === "string") {
          detail = errorJson.detail;
        } else if (errorJson.detail) {
          detail = JSON.stringify(errorJson.detail);
        } else if (raw) {
          detail = raw;
        }
      } catch {
        detail = raw || detail;
      }
      return {
        success: false,
        error: detail,
        raw: `HTTP ${res.status} — ${raw || detail}`,
      };
    }

    return { success: true, data: (await res.json()) as T };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error occurred";
    return {
      success: false,
      error: `Could not reach backend at ${BASE_URL}: ${message}`,
    };
  }
}
