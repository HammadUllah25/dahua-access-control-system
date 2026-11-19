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

// Mock network hierarchy for the role-based views. Super Admin sees every row,
// Admin sees Area A, Branch sees Branch 04.
export type NetworkStation = {
  id: string;
  name: string;
  area: string;
  branch: string;
  status: "online" | "offline" | "pending";
  devices: number;
  lastSeen: string;
};

export const NETWORK_STATIONS: NetworkStation[] = [
  { id: "ST-01", name: "PumpStation 01", area: "Area A", branch: "Branch 04", status: "online", devices: 4, lastSeen: "Just now" },
  { id: "ST-02", name: "PumpStation 02", area: "Area A", branch: "Branch 04", status: "online", devices: 2, lastSeen: "1 min ago" },
  { id: "ST-03", name: "PumpStation 03", area: "Area A", branch: "Branch 05", status: "offline", devices: 3, lastSeen: "18 min ago" },
  { id: "ST-04", name: "PumpStation 04", area: "Area A", branch: "Branch 04", status: "online", devices: 3, lastSeen: "Just now" },
  { id: "ST-05", name: "PumpStation 05", area: "Area B", branch: "Branch 07", status: "pending", devices: 1, lastSeen: "Not connected" },
  { id: "ST-06", name: "PumpStation 06", area: "Area B", branch: "Branch 07", status: "online", devices: 2, lastSeen: "2 min ago" },
];

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
  { id: "AL06", ts: "2026-11-11 17:45", type: "Gate held open", severity: "Warning", status: "Active", detail: "Washroom entry gate was open for about 2 minutes. Check the door and ensure it is closed properly.", ackBy: null },
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
  stationId: string;
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
  // Footfall/outlet stations (Central region list)
  const stationIds = ["1", "2", "3", "4", "5", "7", "8", "9"];
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
      const stationId = stationIds[Math.floor(rand() * stationIds.length)];
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
        stationId,
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

// ---- outlet footfall (overview) --------------------------------------------
// Deterministic mock granted/denied counts per outlet for the Overview bar chart.
export type OutletFootfall = {
  id: number;
  outlet: string;
  city: string;
  region: string;
  status: "Completed" | "Incomplete";
  lat: number;
  lng: number;
  granted: number;
  denied: number;
};

export const OUTLET_FOOTFALL: OutletFootfall[] = [
  { id: 1, outlet: "Zahirpir F/s North bound", city: "Bahawalpur", region: "Central", status: "Completed", lat: 28.9224123, lng: 70.6229235, granted: 210, denied: 12 },
  { id: 2, outlet: "Zahirpir F/s South bound", city: "Bahawalpur", region: "Central", status: "Completed", lat: 28.9200065, lng: 70.62384, granted: 120, denied: 28 },
  { id: 3, outlet: "Multan FS", city: "Multan", region: "Central", status: "Completed", lat: 29.99495, lng: 71.3880017, granted: 185, denied: 9 },
  { id: 4, outlet: "Sher Shah", city: "Multan", region: "Central", status: "Completed", lat: 29.996665, lng: 71.3860283, granted: 40, denied: 18 },
  { id: 5, outlet: "Al Wahid Fs", city: "Multan", region: "Central", status: "Completed", lat: 30.3049433, lng: 71.6664683, granted: 230, denied: 22 },
  { id: 7, outlet: "Taj -2", city: "Lahore", region: "Central", status: "Completed", lat: 31.2042099, lng: 73.9636312, granted: 80, denied: 35 },
  { id: 8, outlet: "Al Rafay Fs", city: "Lahore", region: "Central", status: "Completed", lat: 31.47002, lng: 74.239714, granted: 195, denied: 7 },
  { id: 9, outlet: "Magic River", city: "Lahore", region: "Central", status: "Completed", lat: 31.5458005, lng: 74.2552353, granted: 115, denied: 20 },
];

// ---- overview additions (sales, sensors, gender) ---------------------------

export type StationSales = {
  outletId: number;
  outlet: string;
  sales: number; // PKR
};

export const STATION_SALES: StationSales[] = [
  { outletId: 1, outlet: "Zahirpir F/s North bound", sales: 720000 },
  { outletId: 2, outlet: "Zahirpir F/s South bound", sales: 410000 },
  { outletId: 3, outlet: "Multan FS", sales: 680000 },
  { outletId: 4, outlet: "Sher Shah", sales: 290000 },
  { outletId: 5, outlet: "Al Wahid Fs", sales: 810000 },
  { outletId: 7, outlet: "Taj -2", sales: 360000 },
  { outletId: 8, outlet: "Al Rafay Fs", sales: 740000 },
  { outletId: 9, outlet: "Magic River", sales: 430000 },
];

export const STATION_SALES_SERIES_META = [
  { key: "s1", outlet: "Zahirpir F/s North bound", color: "#b45309" },
  { key: "s2", outlet: "Zahirpir F/s South bound", color: "#d97706" },
  { key: "s3", outlet: "Multan FS", color: "#92400e" },
  { key: "s4", outlet: "Sher Shah", color: "#f59e0b" },
  { key: "s5", outlet: "Al Wahid Fs", color: "#a16207" },
  { key: "s7", outlet: "Taj -2", color: "#eab308" },
  { key: "s8", outlet: "Al Rafay Fs", color: "#ca8a04" },
  { key: "s9", outlet: "Magic River", color: "#fbbf24" },
] as const;

export type StationSalesSeriesPoint = {
  period: string;
  s1: number; s2: number; s3: number; s4: number; s5: number; s7: number; s8: number; s9: number;
};

export type SalesPeriod = "7d" | "this-month" | "past-month";

// Daily sales (PKR) per station — higher fluctuation for trend comparison
export const STATION_SALES_SERIES_7D: StationSalesSeriesPoint[] = [
  { period: "5 Nov",  s1: 82000,  s2: 38000, s3: 112000, s4: 52000, s5: 142000, s7: 64000, s8: 76000,  s9: 44000 },
  { period: "6 Nov",  s1: 124000, s2: 66000, s3: 78000,  s4: 28000, s5: 98000,  s7: 36000, s8: 128000, s9: 72000 },
  { period: "7 Nov",  s1: 94000,  s2: 48000, s3: 104000, s4: 46000, s5: 132000, s7: 58000, s8: 92000,  s9: 52000 },
  { period: "8 Nov",  s1: 136000, s2: 72000, s3: 86000,  s4: 34000, s5: 108000, s7: 42000, s8: 138000, s9: 78000 },
  { period: "9 Nov",  s1: 88000,  s2: 42000, s3: 118000, s4: 56000, s5: 148000, s7: 68000, s8: 84000,  s9: 46000 },
  { period: "10 Nov", s1: 118000, s2: 64000, s3: 92000,  s4: 30000, s5: 102000, s7: 38000, s8: 122000, s9: 70000 },
  { period: "11 Nov", s1: 102000, s2: 52000, s3: 108000, s4: 48000, s5: 126000, s7: 54000, s8: 110000, s9: 58000 },
];

// This month (Nov) — sampled days, higher fluctuation
export const STATION_SALES_SERIES_THIS_MONTH: StationSalesSeriesPoint[] = [
  { period: "1 Nov",  s1: 52000,  s2: 22000, s3: 148000, s4: 68000, s5: 186000, s7: 82000, s8: 46000,  s9: 24000 },
  { period: "3 Nov",  s1: 168000, s2: 96000, s3: 54000,  s4: 14000, s5: 62000,  s7: 18000, s8: 174000, s9: 98000 },
  { period: "5 Nov",  s1: 64000,  s2: 28000, s3: 136000, s4: 62000, s5: 172000, s7: 76000, s8: 58000,  s9: 32000 },
  { period: "7 Nov",  s1: 142000, s2: 84000, s3: 72000,  s4: 22000, s5: 88000,  s7: 28000, s8: 148000, s9: 86000 },
  { period: "9 Nov",  s1: 58000,  s2: 24000, s3: 152000, s4: 74000, s5: 194000, s7: 90000, s8: 52000,  s9: 28000 },
  { period: "11 Nov", s1: 156000, s2: 90000, s3: 64000,  s4: 18000, s5: 76000,  s7: 22000, s8: 162000, s9: 92000 },
  { period: "13 Nov", s1: 72000,  s2: 32000, s3: 128000, s4: 56000, s5: 158000, s7: 68000, s8: 66000,  s9: 36000 },
  { period: "15 Nov", s1: 134000, s2: 78000, s3: 82000,  s4: 26000, s5: 98000,  s7: 34000, s8: 140000, s9: 78000 },
  { period: "17 Nov", s1: 48000,  s2: 20000, s3: 158000, s4: 78000, s5: 198000, s7: 94000, s8: 42000,  s9: 22000 },
  { period: "19 Nov", s1: 162000, s2: 94000, s3: 58000,  s4: 16000, s5: 70000,  s7: 20000, s8: 168000, s9: 96000 },
  { period: "21 Nov", s1: 66000,  s2: 30000, s3: 142000, s4: 64000, s5: 166000, s7: 72000, s8: 60000,  s9: 34000 },
  { period: "23 Nov", s1: 146000, s2: 86000, s3: 76000,  s4: 24000, s5: 92000,  s7: 30000, s8: 152000, s9: 84000 },
  { period: "25 Nov", s1: 54000,  s2: 26000, s3: 146000, s4: 70000, s5: 182000, s7: 84000, s8: 48000,  s9: 26000 },
  { period: "27 Nov", s1: 158000, s2: 92000, s3: 60000,  s4: 20000, s5: 80000,  s7: 24000, s8: 164000, s9: 90000 },
  { period: "30 Nov", s1: 70000,  s2: 34000, s3: 134000, s4: 60000, s5: 160000, s7: 70000, s8: 64000,  s9: 38000 },
];

// Past month (Oct) — sampled days, higher fluctuation
export const STATION_SALES_SERIES_PAST_MONTH: StationSalesSeriesPoint[] = [
  { period: "1 Oct",  s1: 132000, s2: 18000, s3: 76000,  s4: 26000, s5: 98000,  s7: 34000, s8: 118000, s9: 54000 },
  { period: "3 Oct",  s1: 46000,  s2: 82000, s3: 142000, s4: 66000, s5: 178000, s7: 86000, s8: 38000,  s9: 18000 },
  { period: "5 Oct",  s1: 124000, s2: 24000, s3: 68000,  s4: 22000, s5: 90000,  s7: 30000, s8: 112000, s9: 58000 },
  { period: "7 Oct",  s1: 54000,  s2: 76000, s3: 134000, s4: 60000, s5: 164000, s7: 78000, s8: 46000,  s9: 22000 },
  { period: "9 Oct",  s1: 138000, s2: 20000, s3: 72000,  s4: 28000, s5: 104000, s7: 36000, s8: 126000, s9: 62000 },
  { period: "11 Oct", s1: 42000,  s2: 88000, s3: 148000, s4: 70000, s5: 184000, s7: 92000, s8: 34000,  s9: 16000 },
  { period: "13 Oct", s1: 128000, s2: 16000, s3: 82000,  s4: 24000, s5: 94000,  s7: 32000, s8: 116000, s9: 56000 },
  { period: "15 Oct", s1: 58000,  s2: 74000, s3: 138000, s4: 62000, s5: 170000, s7: 80000, s8: 50000,  s9: 24000 },
  { period: "17 Oct", s1: 144000, s2: 22000, s3: 66000,  s4: 20000, s5: 86000,  s7: 28000, s8: 132000, s9: 64000 },
  { period: "19 Oct", s1: 38000,  s2: 90000, s3: 152000, s4: 72000, s5: 188000, s7: 96000, s8: 30000,  s9: 14000 },
  { period: "21 Oct", s1: 134000, s2: 18000, s3: 74000,  s4: 26000, s5: 100000, s7: 34000, s8: 122000, s9: 60000 },
  { period: "23 Oct", s1: 50000,  s2: 80000, s3: 140000, s4: 64000, s5: 176000, s7: 84000, s8: 42000,  s9: 20000 },
  { period: "25 Oct", s1: 140000, s2: 24000, s3: 70000,  s4: 22000, s5: 92000,  s7: 30000, s8: 128000, s9: 66000 },
  { period: "27 Oct", s1: 44000,  s2: 86000, s3: 146000, s4: 68000, s5: 182000, s7: 90000, s8: 36000,  s9: 18000 },
  { period: "31 Oct", s1: 130000, s2: 20000, s3: 78000,  s4: 28000, s5: 106000, s7: 38000, s8: 118000, s9: 58000 },
];

export const STATION_SALES_SERIES: StationSalesSeriesPoint[] = STATION_SALES_SERIES_7D;

export const STATION_SALES_BY_PERIOD: Record<SalesPeriod, { label: string; data: StationSalesSeriesPoint[] }> = {
  "7d": { label: "7 days", data: STATION_SALES_SERIES_7D },
  "this-month": { label: "This month", data: STATION_SALES_SERIES_THIS_MONTH },
  "past-month": { label: "Past month", data: STATION_SALES_SERIES_PAST_MONTH },
};

export type SensorAlertLog = {
  id: string;
  ts: string;
  station: string;
  sensor: string;
  severity: "Critical" | "Warning" | "Info";
  status: "Active" | "Acknowledged" | "Resolved";
  detail: string;
};

export const SENSOR_ALERT_LOGS: SensorAlertLog[] = [
  { id: "SA01", ts: "2026-11-11 17:45", station: "Zahirpir F/s North bound", sensor: "Gate held open (Door sensor)", severity: "Warning", status: "Active", detail: "Washroom entry gate open for about 2 minutes. Check and close door." },
  { id: "SA02", ts: "2026-11-11 17:12", station: "Al Wahid Fs", sensor: "Motion sensor idle anomaly", severity: "Info", status: "Acknowledged", detail: "No motion detected after granted entry; sensor health check recommended." },
  { id: "SA03", ts: "2026-11-11 16:42", station: "Multan FS", sensor: "Door timeout sensor", severity: "Warning", status: "Active", detail: "Door held open longer than configured timeout after granted scan." },
  { id: "SA04", ts: "2026-11-11 15:28", station: "Taj -2", sensor: "Occupancy sensor threshold", severity: "Warning", status: "Active", detail: "Occupancy above threshold for 4 minutes in women’s washroom zone." },
  { id: "SA05", ts: "2026-11-11 14:09", station: "Magic River", sensor: "Reader tamper sensor", severity: "Warning", status: "Acknowledged", detail: "Tamper input triggered briefly; enclosure inspected by staff." },
  { id: "SA06", ts: "2026-11-11 12:51", station: "Sher Shah", sensor: "Door contact sensor mismatch", severity: "Critical", status: "Active", detail: "Relay command and door contact state mismatch detected on men’s washroom door." },
  { id: "SA07", ts: "2026-11-11 11:06", station: "Al Rafay Fs", sensor: "Humidity sensor alert", severity: "Info", status: "Resolved", detail: "Humidity level normalized after ventilation cycle." },
  { id: "SA08", ts: "2026-11-11 09:17", station: "Zahirpir F/s South bound", sensor: "Card reader sensor event", severity: "Info", status: "Acknowledged", detail: "Blocked card attempt detected and denied at reader sensor." },
  { id: "SA09", ts: "2026-11-10 22:34", station: "Multan FS", sensor: "Low-light sensor warning", severity: "Warning", status: "Resolved", detail: "Lighting level dropped below threshold; maintenance notified." },
  { id: "SA10", ts: "2026-11-10 21:03", station: "Taj -2", sensor: "Smoke/air-quality sensor check", severity: "Info", status: "Resolved", detail: "Air-quality reading returned to normal after routine check." },
];

export type GenderWashroom = "Women’s Washroom" | "Men’s Washroom";

export type GenderEntryLog = {
  id: string;
  ts: string;
  station: string;
  washroom: GenderWashroom;
  person: string;
  personType: "Staff" | "Visitor";
  card: string;
  result: "Granted" | "Denied" | "Pending";
  note: string;
};

export const GENDER_ENTRY_LOGS: GenderEntryLog[] = [
  { id: "GE01", ts: "2026-11-11 17:58:12", station: "Zahirpir F/s North bound", washroom: "Women’s Washroom", person: "A. Rahman", personType: "Staff", card: "0142 ···· 8871", result: "Granted", note: "Entry recorded" },
  { id: "GE02", ts: "2026-11-11 17:55:40", station: "Multan FS", washroom: "Men’s Washroom", person: "Visitor", personType: "Visitor", card: "0142 ···· 3298", result: "Granted", note: "General card scan" },
  { id: "GE03", ts: "2026-11-11 17:49:03", station: "Al Wahid Fs", washroom: "Women’s Washroom", person: "M. Okonkwo", personType: "Staff", card: "0142 ···· 4419", result: "Granted", note: "Own staff card" },
  { id: "GE04", ts: "2026-11-11 17:46:18", station: "Taj -2", washroom: "Men’s Washroom", person: "Staff", personType: "Staff", card: "0142 ···· 7712", result: "Denied", note: "Outside time section" },
  { id: "GE05", ts: "2026-11-11 17:41:55", station: "Al Rafay Fs", washroom: "Women’s Washroom", person: "S. Farouk", personType: "Visitor", card: "0142 ···· 9034", result: "Granted", note: "Profile card" },
  { id: "GE06", ts: "2026-11-11 17:38:27", station: "Sher Shah", washroom: "Men’s Washroom", person: "Visitor", personType: "Visitor", card: "0142 ···· 1185", result: "Denied", note: "Card blocked" },
  { id: "GE07", ts: "2026-11-11 17:33:09", station: "Magic River", washroom: "Men’s Washroom", person: "L. D'Souza", personType: "Staff", card: "0142 ···· 6642", result: "Granted", note: "Shared/general area card" },
  { id: "GE08", ts: "2026-11-11 17:29:44", station: "Zahirpir F/s South bound", washroom: "Women’s Washroom", person: "Staff", personType: "Staff", card: "0142 ···· 5560", result: "Pending", note: "Sync pending verification" },
];

export const GENDER_ENTRY_TOTALS = {
  women: 1542,
  men: 1394,
};
