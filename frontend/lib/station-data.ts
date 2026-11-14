// Station dashboard mock data — the single source the 9 pages derive from.
// shortcut: static fixtures standing in for NetSDK queries; swap these for
// real API calls once the backend integration lands.

export type RangeKey = "today" | "7d" | "30d";

export const STATION = {
  id: "ST-04",
  name: "PumpStation 04",
  address: "Sheikh Zayed Rd · Branch 04",
  lat: 25.2048,
  lng: 55.2708,
  timezone: "Asia/Dubai (GMT+4)",
  contact: "ops.station04@fuelco.example",
  admin: { name: "A. Rahman", email: "a.rahman@fuelco.example" },
};

export const DEVICE = {
  model: "Dahua DHI-ASI1201E",
  serial: "6H08A84PAJ00107",
  connection: "Ethernet / TCP-IP",
  ip: "10.20.4.11",
  online: true,
  lastSeen: "2026-11-11 17:59:54",
  doorName: "Washroom Entry · Reader 1",
  relayState: "Energised (locked)",
  doorContact: "Closed",
  doorContactWired: true,
  firmware: "NetSDK 3.060.R.251201",
  lastSync: "2026-11-11 05:12",
  pendingChanges: 1,
  lastError: null as string | null,
};

// Static map positions for the Overview Google map. Coordinates are percentages
// of the station view.
// shortcut: hand-placed pins — they do not follow map pan/zoom; a keyed Maps JS
// API is needed for anchored markers.
export type SiteDevice = {
  id: string;
  name: string;
  location: string;
  model: string;
  status: "online" | "offline" | "pending";
  x: number;
  y: number;
};

export const SITE_DEVICES: SiteDevice[] = [
  { id: "SD1", name: "Washroom entry · Reader 1", location: "Washroom block", model: "DHI-ASI1201E", status: "online", x: 38, y: 44 },
  { id: "SD2", name: "Washroom exit · Reader 2", location: "Washroom block", model: "DHI-ASI1201E", status: "online", x: 26, y: 66 },
  { id: "SD3", name: "Shop staff door", location: "Shop & kiosk", model: "DHI-ASI1201E", status: "pending", x: 58, y: 30 },
];

export type PersonCategory = "Normal" | "VIP" | "Guest" | "Patrol";

// Station admin assigns every person as staff or visitor; the controller
// category above stays separate because firmware exposes it independently.
export type PersonRole = "Staff" | "Visitor";

export type Person = {
  id: string;
  name: string;
  category: PersonCategory;
  role: PersonRole;
  status: "Active" | "Blocked";
};

export const PEOPLE: Person[] = [
  { id: "P001", name: "A. Rahman", category: "Normal", role: "Staff", status: "Active" },
  { id: "P002", name: "M. Okonkwo", category: "Normal", role: "Staff", status: "Active" },
  { id: "P003", name: "S. Farouk", category: "VIP", role: "Visitor", status: "Active" },
  { id: "P004", name: "L. D'Souza", category: "Patrol", role: "Staff", status: "Active" },
  { id: "P005", name: "R. Ibrahim", category: "Normal", role: "Staff", status: "Active" },
  { id: "P006", name: "K. Van Der Berg", category: "Guest", role: "Visitor", status: "Active" },
  { id: "P007", name: "H. Nakamura", category: "Guest", role: "Visitor", status: "Blocked" },
  { id: "P008", name: "T. Mwangi", category: "Patrol", role: "Staff", status: "Active" },
];

export type CardRecord = {
  id: string;
  personId: string;
  masked: string;
  tech: string;
  validFrom: string;
  validTo: string;
  status: "Active" | "Blocked" | "Expired";
  scheduleId: string;
};

export const CARDS: CardRecord[] = [
  { id: "C001", personId: "P001", masked: "0142 ···· 8871", tech: "MIFARE 13.56 MHz", validFrom: "2026-01-15", validTo: "2027-01-14", status: "Active", scheduleId: "SCH01" },
  { id: "C002", personId: "P002", masked: "0142 ···· 4419", tech: "MIFARE 13.56 MHz", validFrom: "2026-03-02", validTo: "2026-12-31", status: "Active", scheduleId: "SCH01" },
  { id: "C003", personId: "P003", masked: "0142 ···· 9034", tech: "MIFARE 13.56 MHz", validFrom: "2026-02-20", validTo: "2027-02-19", status: "Active", scheduleId: "SCH02" },
  { id: "C004", personId: "P004", masked: "0142 ···· 7712", tech: "MIFARE 13.56 MHz", validFrom: "2026-04-01", validTo: "2026-11-30", status: "Active", scheduleId: "SCH04" },
  { id: "C005", personId: "P005", masked: "0142 ···· 5560", tech: "MIFARE 13.56 MHz", validFrom: "2026-06-10", validTo: "2026-10-31", status: "Expired", scheduleId: "SCH01" },
  { id: "C006", personId: "P006", masked: "0142 ···· 3298", tech: "MIFARE 13.56 MHz", validFrom: "2026-11-01", validTo: "2026-11-20", status: "Active", scheduleId: "SCH03" },
  { id: "C007", personId: "P007", masked: "0142 ···· 1185", tech: "MIFARE 13.56 MHz", validFrom: "2026-05-05", validTo: "2026-11-05", status: "Blocked", scheduleId: "SCH03" },
  { id: "C008", personId: "P008", masked: "0142 ···· 6642", tech: "MIFARE 13.56 MHz", validFrom: "2026-08-18", validTo: "2027-02-17", status: "Active", scheduleId: "SCH04" },
];

export type Schedule = {
  id: string;
  name: string;
  days: number[]; // 0=Mon .. 6=Sun
  start: string;
  end: string;
  door: string;
  sync: "Synced" | "Pending" | "Error";
};

export const SCHEDULES: Schedule[] = [
  { id: "SCH01", name: "Staff hours", days: [0, 1, 2, 3, 4, 5, 6], start: "06:00", end: "22:00", door: "Washroom Entry · Reader 1", sync: "Synced" },
  { id: "SCH02", name: "Extended (VIP)", days: [0, 1, 2, 3, 4, 5, 6], start: "05:00", end: "23:30", door: "Washroom Entry · Reader 1", sync: "Synced" },
  { id: "SCH03", name: "Guest daytime", days: [0, 1, 2, 3, 4], start: "08:00", end: "18:00", door: "Washroom Entry · Reader 1", sync: "Pending" },
  { id: "SCH04", name: "Patrol night rounds", days: [0, 1, 2, 3, 4, 5, 6], start: "22:00", end: "06:00", door: "Washroom Entry · Reader 1", sync: "Synced" },
  { id: "SCH05", name: "Cleaning crew early", days: [0, 1, 2, 3, 4, 5], start: "05:00", end: "09:00", door: "Washroom Entry · Reader 1", sync: "Synced" },
];

export const HOLIDAYS = [
  { date: "2026-12-01", label: "Commemoration Day", period: "Follows Sunday schedule" },
  { date: "2026-12-02", label: "National Day", period: "Follows Sunday schedule" },
  { date: "2027-01-01", label: "New Year", period: "Guest schedule extended to 20:00" },
];

export type Alert = {
  id: string;
  ts: string;
  type: string;
  severity: "Critical" | "Warning" | "Info";
  status: "Active" | "Acknowledged" | "Resolved";
  detail: string;
  ackBy: string | null;
};

export const ALERTS: Alert[] = [
  { id: "AL01", ts: "2026-11-11 16:42", type: "Door timeout", severity: "Warning", status: "Active", detail: "Door held open longer than the configured timeout after a granted scan. Check the closer and the contact sensor wiring.", ackBy: null },
  { id: "AL02", ts: "2026-11-11 09:17", type: "Blocked card attempt", severity: "Info", status: "Acknowledged", detail: "A blocked card (P007) attempted access at the washroom reader. The attempt was denied and logged.", ackBy: "A. Rahman" },
  { id: "AL03", ts: "2026-11-10 21:03", type: "Tamper detected", severity: "Warning", status: "Acknowledged", detail: "Reader tamper input triggered briefly. Inspect the mounting and enclosure seal on the next patrol round.", ackBy: "A. Rahman" },
  { id: "AL04", ts: "2026-11-08 03:55", type: "Controller offline", severity: "Critical", status: "Resolved", detail: "Controller lost network connectivity for 4 minutes during a site switch restart. Reconnected automatically.", ackBy: "A. Rahman" },
  { id: "AL05", ts: "2026-11-05 14:28", type: "Intrusion (out of section)", severity: "Critical", status: "Resolved", detail: "Card presented outside its allowed time section while the door was forced. Denied and reported by the controller.", ackBy: "A. Rahman" },
];

export const DEVICE_EVENTS = [
  { ts: "2026-11-11 17:59:54", type: "Heartbeat", detail: "Online — TCP session healthy" },
  { ts: "2026-11-11 05:12:03", type: "Config sync", detail: "Schedule SCH03 queued (pending)" },
  { ts: "2026-11-08 03:55:11", type: "Offline", detail: "Network unreachable — 4 min outage" },
  { ts: "2026-11-08 03:59:36", type: "Online", detail: "Reconnected after site switch restart" },
  { ts: "2026-11-02 02:14:50", type: "Restart", detail: "Device rebooted after config push" },
];

// ---- access events ---------------------------------------------------------
// Generated deterministically (seeded LCG + fixed base date) so SSR and client
// renders always agree. Base = start of 11 Nov 2026 UTC; 60 days of history.

export type AccessEvent = {
  id: string;
  ts: string;
  personId: string | null;
  maskedCard: string;
  result: "Granted" | "Denied";
  reason: string | null;
  device: string;
  door: string;
};

// documented event reasons only; anti-passback is listed in the datasheet
// but not confirmed on the installed unit
const DENIAL_REASONS = [
  "Invalid card",
  "Expired card",
  "No permission",
  "Outside time section",
  "Card blocked",
];

const BASE = Date.UTC(2026, 10, 11); // 2026-11-11T00:00:00Z
const HOUR = 3_600_000;
const DAY = 24 * HOUR;

// washroom traffic: quiet night, morning + midday + evening peaks
const HOUR_WEIGHTS = [0, 0, 0, 0, 0, 1, 2, 4, 6, 5, 3, 4, 6, 5, 3, 3, 4, 5, 4, 2, 1, 1, 0, 0];

export const ACCESS_EVENTS: AccessEvent[] = (() => {
  let seed = 20261111;
  const rand = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };
  const weightSum = HOUR_WEIGHTS.reduce((a, b) => a + b, 0);
  const events: AccessEvent[] = [];
  let n = 0;
  for (let day = 59; day >= 0; day--) {
    const count = 45 + Math.floor(rand() * 26);
    for (let i = 0; i < count; i++) {
      let pick = rand() * weightSum;
      let hour = 0;
      while (pick >= HOUR_WEIGHTS[hour]) {
        pick -= HOUR_WEIGHTS[hour];
        hour++;
      }
      const minute = Math.floor(rand() * 60);
      const ts = BASE - day * DAY + hour * HOUR + minute * 60_000;
      const person = PEOPLE[Math.floor(rand() * PEOPLE.length)];
      const card = CARDS.find((c) => c.personId === person.id) ?? CARDS[0];
      const denied = rand() > 0.87;
      const unresolved = denied && rand() > 0.5; // some denials have no linked person
      events.push({
        id: `E${String(++n).padStart(4, "0")}`,
        ts: new Date(ts).toISOString(),
        personId: unresolved ? null : person.id,
        maskedCard: card.masked,
        result: denied ? "Denied" : "Granted",
        reason: denied
          ? DENIAL_REASONS[Math.floor(rand() * DENIAL_REASONS.length)]
          : null,
        device: DEVICE.serial,
        door: DEVICE.doorName,
      });
    }
  }
  return events.sort((a, b) => (a.ts < b.ts ? 1 : -1));
})();

// ---- derive helpers --------------------------------------------------------

export function eventsForRange(events: AccessEvent[], range: RangeKey): AccessEvent[] {
  const days = range === "today" ? 1 : range === "7d" ? 7 : 30;
  const cutoff = BASE - (days - 1) * DAY;
  return events.filter((e) => Date.parse(e.ts) >= cutoff);
}

export function eventsForPrevRange(events: AccessEvent[], range: RangeKey): AccessEvent[] {
  const days = range === "today" ? 1 : range === "7d" ? 7 : 30;
  const end = BASE - (days - 1) * DAY;
  const start = end - days * DAY;
  return events.filter((e) => {
    const t = Date.parse(e.ts);
    return t >= start && t < end;
  });
}

export function summarize(events: AccessEvent[]) {
  const total = events.length;
  const granted = events.filter((e) => e.result === "Granted").length;
  return {
    total,
    granted,
    denied: total - granted,
    successRate: total ? granted / total : 0,
  };
}

export function dailySeries(events: AccessEvent[], range: RangeKey) {
  const days = range === "today" ? 1 : range === "7d" ? 7 : 30;
  return Array.from({ length: days }, (_, i) => {
    const dayStart = BASE - (days - 1 - i) * DAY;
    const dayEvents = events.filter((e) => {
      const t = Date.parse(e.ts);
      return t >= dayStart && t < dayStart + DAY;
    });
    return {
      day: fmtDay(new Date(dayStart).toISOString()),
      granted: dayEvents.filter((e) => e.result === "Granted").length,
      denied: dayEvents.filter((e) => e.result === "Denied").length,
    };
  });
}

export function hourlyBuckets(events: AccessEvent[]) {
  return Array.from({ length: 24 }, (_, hour) => ({
    hour: `${String(hour).padStart(2, "0")}:00`,
    scans: events.filter((e) => new Date(e.ts).getUTCHours() === hour).length,
  }));
}

export function denialReasons(events: AccessEvent[]) {
  const counts = new Map<string, number>();
  for (const e of events) {
    if (e.result === "Denied" && e.reason) {
      counts.set(e.reason, (counts.get(e.reason) ?? 0) + 1);
    }
  }
  const total = [...counts.values()].reduce((a, b) => a + b, 0);
  return [...counts.entries()]
    .map(([reason, count]) => ({ reason, count, share: total ? count / total : 0 }))
    .sort((a, b) => b.count - a.count);
}

// ---- format helpers (fixed locale so SSR and client agree) -----------------

export const fmtDay = (iso: string) =>
  new Date(iso).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

export const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });

export const fmtTimeSec = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

export const pct = (ratio: number) => `${(ratio * 100).toFixed(1)}%`;
