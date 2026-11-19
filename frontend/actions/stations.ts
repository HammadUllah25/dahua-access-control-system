"use server";

// Server Actions for the station lifecycle:
// GET/POST /stations and POST /stations/{station_id}/devices/{device_id}.

import { backendRequest, type ActionResult } from "@/actions/backend";

export type StationRecord = {
  id: number;
  station_code: string;
  name: string;
  address: string | null;
  city: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateStationPayload = {
  station_code: string;
  name: string;
  address?: string | null;
  city?: string | null;
  contact_name?: string | null;
  contact_phone?: string | null;
  is_active?: boolean;
};

export async function listStationsAction(): Promise<ActionResult<StationRecord[]>> {
  return backendRequest<StationRecord[]>("/stations");
}

export async function createStationAction(
  payload: CreateStationPayload
): Promise<ActionResult<StationRecord>> {
  return backendRequest<StationRecord>("/stations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type UpdateStationCardPayload = {
  valid_from?: string;
  valid_until?: string;
  card_name?: string;
  is_valid?: boolean;
  is_active?: boolean;
  role?: "USER" | "STAFF";
  card_type?: "general" | "vip" | "guest";
  is_billable?: boolean | null;
  door_indices?: number[];
  time_section_indices?: number[];
};

export async function updateStationCardAction(
  stationId: number,
  assignmentId: number,
  payload: UpdateStationCardPayload
): Promise<ActionResult<Record<string, unknown>>> {
  return backendRequest<Record<string, unknown>>(
    `/stations/${stationId}/cards/${assignmentId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    }
  );
}

export async function assignDeviceToStationAction(
  stationId: number,
  deviceId: number
): Promise<ActionResult<Record<string, unknown>>> {
  return backendRequest<Record<string, unknown>>(
    `/stations/${stationId}/devices/${deviceId}`,
    { method: "POST" }
  );
}
