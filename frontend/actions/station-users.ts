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
