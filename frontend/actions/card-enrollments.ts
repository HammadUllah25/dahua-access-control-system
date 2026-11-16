"use server";

// Server Actions for the physical card-enrollment flow.
// Start listening, poll for the card UID, then confirm the assignment.

import { backendRequest, type ActionResult } from "@/actions/backend";

export type CardEnrollmentRecord = {
  session_token: string;
  device_id: number;
  status:
    | "waiting"
    | "captured"
    | "confirming"
    | "confirmed"
    | "expired"
    | "cancelled";
  card_number: string | null;
  created_at: string;
  expires_at: string;
  captured_at: string | null;
  event_access_result: string | null;
  event_error_code: number | null;
  event_door_number: number | null;
  message: string;
};

export type ConfirmCardPayload = {
  card_name?: string | null;
  card_type?: "general" | "vip" | "guest";
  is_valid?: boolean;
  valid_from?: string;
  valid_until?: string;
  door_indices?: number[];
  time_section_indices?: number[];
};

export async function startCardEnrollmentAction(
  stationId: number,
  userId: number,
  deviceId: number,
  timeoutSeconds = 90
): Promise<ActionResult<CardEnrollmentRecord>> {
  return backendRequest<CardEnrollmentRecord>(
    `/stations/${stationId}/users/${userId}/card-enrollments`,
    {
      method: "POST",
      body: JSON.stringify({
        device_id: deviceId,
        timeout_seconds: timeoutSeconds,
      }),
      timeoutMs: 45_000,
    }
  );
}

export async function getCardEnrollmentAction(
  stationId: number,
  userId: number,
  sessionToken: string
): Promise<ActionResult<CardEnrollmentRecord>> {
  return backendRequest<CardEnrollmentRecord>(
    `/stations/${stationId}/users/${userId}/card-enrollments/${sessionToken}`
  );
}

export async function confirmCardEnrollmentAction(
  stationId: number,
  userId: number,
  sessionToken: string,
  payload: ConfirmCardPayload
): Promise<ActionResult<Record<string, unknown>>> {
  return backendRequest<Record<string, unknown>>(
    `/stations/${stationId}/users/${userId}/card-enrollments/${sessionToken}/confirm`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      timeoutMs: 45_000,
    }
  );
}
