"use server";

// Server Actions for access events and the dashboard/report aggregates:
// GET /access-events, /access-events/summary, /dashboard/summary,
// /dashboard/stations and /reports/usage.

import { backendRequest, type ActionResult } from "@/actions/backend";

// Mirrors the backend AccessEventRead schema (fields the UI reads).
export type AccessEventRecord = {
  id: number;
  device_id: number | null;
  device_name: string | null;
  device_serial_number: string | null;
  station_id: number | null;
  station_name: string | null;
  card_role: string | null;
  is_billable: boolean;
  rate_applied: number | null;
  currency: string;
  event_source: string;
  event_type: string;
  user_type: string | null;
  operator_id: string | null;
  reason: string | null;
  door_number: number | null;
  door_name: string | null;
  card_number: string | null;
  cardholder_name: string | null;
  event_direction: string;
  open_method: number | null;
  access_result: "granted" | "denied" | string;
  error_code: number | null;
  device_event_time: string | null;
  received_at: string;
};

export type AccessEventFilters = {
  station_id?: number;
  device_id?: number;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
};

export type AccessEventSummary = {
  total: number;
  granted: number;
  denied: number;
  unknown: number;
};

// Decimal fields arrive as JSON numbers or strings depending on the encoder.
type Money = number | string;

export type UsageSummary = {
  station_id: number | null;
  start_date: string;
  end_date: string;
  total_scans: number;
  granted_scans: number;
  denied_scans: number;
  user_entries: number;
  staff_entries: number;
  billable_entries: number;
  unpriced_billable_entries: number;
  expected_collection: Money;
  actual_cash_collected: Money;
  outstanding_balance: Money;
  currency: string;
};

export type StationOverview = {
  station_id: number;
  station_code: string;
  station_name: string;
  city: string | null;
  is_active: boolean;
  device_count: number;
  online_devices: number;
  devices_needing_attention: number;
  total_cards: number;
  active_cards: number;
  usage: UsageSummary;
};

export type UsageBucket = {
  period: string;
  total_scans: number;
  granted_scans: number;
  denied_scans: number;
  user_entries: number;
  staff_entries: number;
  billable_entries: number;
  expected_collection: Money;
};

type DateFilters = { station_id?: number; start_date?: string; end_date?: string };

function query(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export async function listAccessEventsAction(
  filters: AccessEventFilters = {}
): Promise<ActionResult<AccessEventRecord[]>> {
  return backendRequest<AccessEventRecord[]>(`/access-events${query(filters)}`);
}

export async function accessEventSummaryAction(
  filters: { station_id?: number; device_id?: number } = {}
): Promise<ActionResult<AccessEventSummary>> {
  return backendRequest<AccessEventSummary>(`/access-events/summary${query(filters)}`);
}

export async function dashboardSummaryAction(
  filters: DateFilters = {}
): Promise<ActionResult<UsageSummary>> {
  return backendRequest<UsageSummary>(`/dashboard/summary${query(filters)}`);
}

export async function dashboardStationsAction(
  filters: DateFilters = {}
): Promise<ActionResult<{ station_count: number; items: StationOverview[] }>> {
  return backendRequest(`/dashboard/stations${query(filters)}`);
}

export async function usageReportAction(
  filters: DateFilters & { group_by?: "day" | "week" | "month" | "year" } = {}
): Promise<ActionResult<{ group_by: string; currency: string; items: UsageBucket[] }>> {
  return backendRequest(`/reports/usage${query(filters)}`);
}
