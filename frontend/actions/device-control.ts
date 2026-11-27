"use server";

// Server Actions for controller commands: door sensor config, health check,
// connect/disconnect and remote unlock. The unlock key stays server-side.

import { backendRequest, type ActionResult } from "@/actions/backend";

export type DoorConfig = {
  device_id: number;
  door_index: number;
  sensor_enabled: boolean;
  close_check_sensor: boolean;
  close_timeout: number;
  door_not_closed_alarm_enable: boolean;
  forced_entry_alarm_enable: boolean;
  duress_alarm_enable: boolean;
  alarm_enabled: boolean;
  unlock_duration_seconds: number;
};

export type DoorConfigUpdate = Partial<
  Omit<DoorConfig, "device_id" | "door_index" | "alarm_enabled">
> & { door_index?: number };

export type RemoteUnlockResult = {
  status: string;
  event_id: number;
  door_index: number;
  physical_door_state_verified: boolean;
  message: string;
};

export async function getDoorConfigAction(
  deviceId: number,
  doorIndex = 0
): Promise<ActionResult<DoorConfig>> {
  return backendRequest<DoorConfig>(
    `/devices/${deviceId}/door-config?door_index=${doorIndex}`,
    { timeoutMs: 30_000 }
  );
}

export async function updateDoorConfigAction(
  deviceId: number,
  payload: DoorConfigUpdate
): Promise<ActionResult<DoorConfig & { message: string }>> {
  return backendRequest(`/devices/${deviceId}/door-config`, {
    method: "PUT",
    body: JSON.stringify(payload),
    timeoutMs: 45_000,
  });
}

export async function deviceHealthCheckAction(
  deviceId: number
): Promise<ActionResult<Record<string, unknown>>> {
  return backendRequest(`/devices/${deviceId}/health-check`, { method: "POST", timeoutMs: 30_000 });
}

export async function connectDeviceAction(
  deviceId: number
): Promise<ActionResult<Record<string, unknown>>> {
  return backendRequest(`/devices/${deviceId}/connect`, { method: "POST", timeoutMs: 45_000 });
}

export async function disconnectDeviceAction(
  deviceId: number
): Promise<ActionResult<Record<string, unknown>>> {
  return backendRequest(`/devices/${deviceId}/disconnect`, { method: "POST" });
}

export type InventoryCheckResult = {
  inventory_status: string;
  expected_count: number;
  observed_count: number;
  missing_cards: string[];
  unexpected_cards: string[];
  repaired_record_numbers: string[];
  note: string;
};

export type ReprovisionResult = {
  status: string;
  restored_cards: string[];
  failed_cards: { card_number: string; error: string }[];
};

// Reads the controller's card list, compares it with the database and repairs stored record numbers.
export async function inventoryCheckAction(
  deviceId: number
): Promise<ActionResult<InventoryCheckResult>> {
  return backendRequest<InventoryCheckResult>(`/devices/${deviceId}/inventory-check`, {
    method: "POST",
    timeoutMs: 60_000,
  });
}

// Writes the cards that are in the database but missing on the controller.
export async function reprovisionDeviceAction(
  deviceId: number
): Promise<ActionResult<ReprovisionResult>> {
  return backendRequest<ReprovisionResult>(`/devices/${deviceId}/reprovision`, {
    method: "POST",
    body: JSON.stringify({ confirmation: "REPROVISION_FROM_CLOUD" }),
    timeoutMs: 120_000,
  });
}

export async function remoteUnlockAction(
  deviceId: number,
  payload: { door_index?: number; operator_id?: string; reason?: string } = {}
): Promise<ActionResult<RemoteUnlockResult>> {
  const key = process.env.REMOTE_UNLOCK_API_KEY;
  if (!key) {
    return {
      success: false,
      error: "Remote unlock is not configured. Set REMOTE_UNLOCK_API_KEY in the frontend server environment.",
    };
  }
  return backendRequest<RemoteUnlockResult>(`/devices/${deviceId}/remote-unlock`, {
    method: "POST",
    headers: { "X-Unlock-API-Key": key },
    body: JSON.stringify(payload),
    timeoutMs: 30_000,
  });
}
