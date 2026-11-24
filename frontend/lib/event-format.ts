// Display helpers for backend access events (GET /access-events rows).
import type { AccessEventRecord } from "@/actions/access-events";
import type { AccessEvent } from "@/lib/station-data";

// Vendor nErrorCode meanings for denied scans (NetSDK SDK_Struct.py).
const ERROR_REASONS: Record<number, string> = {
  0x10: "Unauthorized card",
  0x11: "Card lost or cancelled",
  0x12: "No door right",
  0x13: "Unlock mode error",
  0x14: "Outside validity period",
  0x15: "Anti-passback",
  0x17: "Door held closed",
  0x18: "Interlock active",
  0x1a: "Intrusion alarm active",
  0x20: "Outside time section",
  0x21: "Holiday time section",
  0x23: "Card overdue",
  0x63: "Repeat entry",
};

export const resultLabel = (e: AccessEventRecord): "Granted" | "Denied" =>
  e.access_result === "granted" ? "Granted" : "Denied";

export const maskCard = (card: string | null) =>
  card ? `···· ${card.slice(-4).toUpperCase()}` : "—";

export const personLabel = (e: AccessEventRecord) =>
  e.cardholder_name ||
  (e.event_type === "REMOTE_UNLOCK" ? `Remote · ${e.operator_id ?? e.user_type ?? "admin"}` : null) ||
  (e.card_role ? e.card_role.charAt(0) + e.card_role.slice(1).toLowerCase() : null) ||
  "Unresolved";

export function reasonLabel(e: AccessEventRecord) {
  if (e.reason) return e.reason;
  if (e.access_result === "granted" || e.error_code == null) return null;
  return ERROR_REASONS[e.error_code] ?? `Code 0x${e.error_code.toString(16)}`;
}

// Prefer the controller's own clock; fall back to when the backend received it.
export const eventTime = (e: AccessEventRecord) => e.device_event_time ?? e.received_at;

// Shape the overview widgets (summarize, hourlyBuckets, AccessRhythm, DenialReasons) already read.
export const toDashboardEvent = (e: AccessEventRecord): AccessEvent => ({
  id: String(e.id),
  ts: eventTime(e),
  personId: null,
  maskedCard: maskCard(e.card_number),
  result: resultLabel(e),
  reason: reasonLabel(e),
  device: e.device_serial_number ?? e.device_name ?? "",
  door: e.door_name ?? String(e.door_number ?? ""),
  stationId: String(e.station_id ?? ""),
});
