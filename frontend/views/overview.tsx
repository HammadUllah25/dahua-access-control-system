import {
  ActivityFeed,
  type FeedItem,
} from "@/components/overviewpage/activity-feed";
import {
  AllocateCardDialog,
} from "@/components/overviewpage/allocate-card-dialog";
import {
  CardsNeedingAttention,
  type AttentionCard,
} from "@/components/overviewpage/attention-cards";
import {
  KpiCards,
  type Kpi,
} from "@/components/overviewpage/kpi-cards";
import {
  TrafficChart,
  type TrafficPoint,
} from "@/components/overviewpage/traffic-chart";
import {
  WashroomRack,
  type WashroomDevice,
} from "@/components/overviewpage/washroom-rack";
import { Cctv, CreditCard, ScanLine, TriangleAlert } from "lucide-react";

// shortcut: static seed data shaped like the FastAPI /devices, /persons and
// /devices/{id}/cards responses; swap for real fetches once the API is wired.
const kpis: Kpi[] = [
  {
    label: "Washrooms online",
    value: "3",
    sub: "of 5 registered",
    icon: Cctv,
    delta: { text: "1 offline", negative: true },
  },
  {
    label: "Cards active",
    value: "157",
    sub: "+12 assigned this week",
    icon: CreditCard,
    delta: { text: "+8%" },
  },
  {
    label: "Entries today",
    value: "398",
    sub: "card reads across all washrooms",
    icon: ScanLine,
    delta: { text: "+6%" },
  },
  {
    label: "Cards needing attention",
    value: "4",
    sub: "2 failed sync, 2 expiring",
    icon: TriangleAlert,
    delta: { text: "2 failed", negative: true },
  },
];

const washrooms: WashroomDevice[] = [
  {
    id: 1,
    name: "Washroom A",
    location: "Ground floor",
    model: "ASI1201E",
    host: "192.168.1.201:37777",
    status: "online",
    cards: 48,
    entriesToday: 132,
    lastSeen: "2 min ago",
  },
  {
    id: 2,
    name: "Washroom B",
    location: "Ground floor",
    model: "ASI1201E",
    host: "192.168.1.202:37777",
    status: "online",
    cards: 22,
    entriesToday: 96,
    lastSeen: "2 min ago",
  },
  {
    id: 3,
    name: "Washroom C",
    location: "First floor",
    model: "ASI1201E",
    host: "192.168.1.203:37777",
    status: "pending",
    cards: 17,
    entriesToday: 41,
    lastSeen: "38 min ago",
  },
  {
    id: 4,
    name: "Washroom D",
    location: "First floor",
    model: "ASI1201E",
    host: "192.168.1.204:37777",
    status: "online",
    cards: 31,
    entriesToday: 118,
    lastSeen: "2 min ago",
  },
  {
    id: 5,
    name: "Staff washroom",
    location: "Facilities",
    model: "ASI1201E",
    host: "192.168.1.205:37777",
    status: "offline",
    cards: 39,
    entriesToday: 11,
    lastSeen: "1 h ago",
  },
];

const traffic: TrafficPoint[] = [
  { time: "07:00", granted: 24, denied: 1 },
  { time: "08:00", granted: 52, denied: 2 },
  { time: "09:00", granted: 48, denied: 0 },
  { time: "10:00", granted: 37, denied: 1 },
  { time: "11:00", granted: 41, denied: 0 },
  { time: "12:00", granted: 33, denied: 2 },
  { time: "13:00", granted: 29, denied: 0 },
  { time: "14:00", granted: 35, denied: 1 },
  { time: "15:00", granted: 28, denied: 0 },
  { time: "16:00", granted: 31, denied: 1 },
  { time: "17:00", granted: 22, denied: 0 },
  { time: "18:00", granted: 12, denied: 0 },
  { time: "19:00", granted: 6, denied: 0 },
];

const activity: FeedItem[] = [
  {
    time: "09:41",
    text: "Card 0019BC20 failed to sync to Washroom A",
    kind: "error",
  },
  {
    time: "09:38",
    text: "Washroom C flagged pending after 3 missed health checks",
    kind: "error",
  },
  {
    time: "09:21",
    text: "Ayesha Khan enrolled as EMP-0021",
    kind: "person",
  },
  {
    time: "09:02",
    text: "Card FB66983B assigned to Washroom B",
    kind: "success",
  },
  {
    time: "08:47",
    text: "Staff washroom reader went offline",
    kind: "error",
  },
  {
    time: "08:15",
    text: "Card 77C4D910 updated on Washroom C",
    kind: "success",
  },
];

const attentionCards: AttentionCard[] = [
  {
    id: 1,
    personName: "Sahil Mehmood",
    department: "IT",
    cardNumber: "0019BC20",
    controller: "Washroom A",
    status: "offline",
    statusLabel: "Failed sync",
    validUntil: "2036-11-09",
  },
  {
    id: 2,
    personName: "Ayesha Khan",
    department: "Operations",
    cardNumber: "FB66983B",
    controller: "Washroom B",
    status: "pending",
    statusLabel: "Expiring soon",
    validUntil: "2026-12-01",
  },
  {
    id: 3,
    personName: "Bilal Ahmed",
    department: "Logistics",
    cardNumber: "77C4D910",
    controller: "Washroom C",
    status: "pending",
    statusLabel: "Frozen",
    validUntil: "2030-05-20",
  },
  {
    id: 4,
    personName: "Usman Tariq",
    department: "Facilities",
    cardNumber: "EE31A05F",
    controller: "Washroom A",
    status: "offline",
    statusLabel: "Expired",
    validUntil: "2026-10-31",
  },
];

function OverviewView() {
  return (
    <div className="w-full flex-1 p-4 md:p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4 pb-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Overview</h2>
          <p className="text-sm text-muted-foreground">
            Washroom access and card allocation across your site.
          </p>
        </div>
        <AllocateCardDialog />
      </div>
      <KpiCards kpis={kpis} />
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TrafficChart data={traffic} />
        </div>
        <ActivityFeed items={activity} />
      </div>
      <div className="mt-6">
        <WashroomRack devices={washrooms} />
      </div>
      <div className="mt-6">
        <CardsNeedingAttention cards={attentionCards} />
      </div>
    </div>
  );
}

export { OverviewView }
