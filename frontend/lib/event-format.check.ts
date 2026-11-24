// Self-check for lib/event-format.ts and rangeToDates. Run: node lib/event-format.check.ts
import assert from "node:assert/strict";

import { maskCard, personLabel, reasonLabel, resultLabel, toDashboardEvent } from "./event-format.ts";
import { rangeToDates } from "./station-data.ts";

const base = {
  id: 1, device_id: 1, device_name: "Door 1", device_serial_number: "6H08A84PAJ00107",
  station_id: 2, station_name: "PumpStation 04", card_role: "STAFF", is_billable: false,
  rate_applied: null, currency: "PKR", event_source: "RFID", event_type: "CARD_ACCESS",
  user_type: "STAFF", operator_id: null, reason: null, door_number: 0, door_name: null,
  card_number: "fb66983b", cardholder_name: null, event_direction: "ENTRY", open_method: 1,
  access_result: "denied", error_code: 0x20, device_event_time: "2026-11-21T10:05:00",
  received_at: "2026-11-21T05:05:01",
};

assert.equal(resultLabel(base), "Denied");
assert.equal(reasonLabel(base), "Outside time section");
assert.equal(reasonLabel({ ...base, error_code: 0x99 }), "Code 0x99");
assert.equal(reasonLabel({ ...base, access_result: "granted" }), null);
assert.equal(maskCard(base.card_number), "···· 983B");
assert.equal(maskCard(null), "—");
assert.equal(personLabel(base), "Staff");
assert.equal(personLabel({ ...base, event_type: "REMOTE_UNLOCK", operator_id: "DASHBOARD", card_role: null }), "Remote · DASHBOARD");
assert.equal(toDashboardEvent(base).ts, "2026-11-21T10:05:00");

const week = rangeToDates("7d");
const prevWeek = rangeToDates("7d", 1);
const days = (a: string, b: string) => (Date.parse(b) - Date.parse(a)) / 86_400_000;
assert.equal(days(week.start_date, week.end_date), 6);
assert.equal(days(prevWeek.end_date, week.start_date), 1);
assert.equal(rangeToDates("today").start_date, rangeToDates("today").end_date);

console.log("event-format checks passed");
