"use server";

// Server Actions for station people and operational roles.
// A station user is an operational person, not a dashboard login account.

import { backendRequest, type ActionResult } from "@/actions/backend";

export type OperationalRoleRecord = {
  id: number;
  station_id: number | null;
  code: string;
  name: string;
  description: string | null;
  is_system: boolean;
  default_is_billable: boolean;
  is_active: boolean;
  created_at: string;
};

export type UserAssignedCardRecord = {
  id: number;
  station_card_assignment_id: number;
  device_id: number;
  card_number: string;
  card_name: string;
  sync_status: string;
  is_valid: boolean;
  valid_from: string | null;
  valid_until: string | null;
  assigned_at: string;
};

export type StationUserRecord = {
  id: number;
  station_id: number;
  name: string;
  phone: string | null;
  role: OperationalRoleRecord;
  is_billable: boolean;
  is_billable_override: boolean | null;
  is_active: boolean;
  active_card: UserAssignedCardRecord | null;
  created_at: string;
  updated_at: string;
};

export type CreateStationUserPayload = {
  name: string;
  phone?: string | null;
  role_id: number;
  is_billable?: boolean | null;
};

export type UpdateStationUserPayload = {
  name?: string;
  phone?: string | null;
  role_id?: number;
  is_billable?: boolean | null;
  clear_billable_override?: boolean;
  is_active?: boolean;
};

export async function listStationRolesAction(
  stationId: number
): Promise<ActionResult<OperationalRoleRecord[]>> {
  return backendRequest<OperationalRoleRecord[]>(`/stations/${stationId}/roles`);
}

export async function listStationUsersAction(
  stationId: number
): Promise<ActionResult<StationUserRecord[]>> {
  return backendRequest<StationUserRecord[]>(`/stations/${stationId}/users`);
}

export async function createStationUserAction(
  stationId: number,
  payload: CreateStationUserPayload
): Promise<ActionResult<StationUserRecord>> {
  return backendRequest<StationUserRecord>(`/stations/${stationId}/users`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteStationUserAction(
  stationId: number,
  userId: number
): Promise<ActionResult<{ deleted: boolean; station_user_id: number; name: string }>> {
  return backendRequest(`/stations/${stationId}/users/${userId}`, {
    method: "DELETE",
  });
}

// Freezes the card on the controller and ends the user link; the card record is kept for history.
export async function revokeStationUserCardAction(
  stationId: number,
  userId: number
): Promise<ActionResult<{ deactivated: boolean; card_number: string; sync_status: string }>> {
  return backendRequest(`/stations/${stationId}/users/${userId}/card`, {
    method: "DELETE",
    timeoutMs: 45_000,
  });
}

export async function updateStationUserAction(
  stationId: number,
  userId: number,
  payload: UpdateStationUserPayload
): Promise<ActionResult<StationUserRecord>> {
  return backendRequest<StationUserRecord>(
    `/stations/${stationId}/users/${userId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}
