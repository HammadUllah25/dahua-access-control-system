"use client";

import { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Cpu,
  DoorClosed,
  Gauge,
  ScanLine,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Bar,
  BarChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { DateRange } from "@/components/dashboard/date-range";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { Panel } from "@/components/dashboard/panel";
import { ResultBadge } from "@/components/dashboard/badges";
import { AccessRhythm } from "@/components/overview/access-rhythm";
import { DenialReasons } from "@/components/overview/denial-reasons";
import { Led } from "@/common/led";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ACCESS_EVENTS,
  ALERTS,
  DEVICE,
  PEOPLE,
  STATION,
  dailySeries,
  eventsForPrevRange,
  eventsForRange,
  fmtDay,
  fmtTime,
  hourlyBuckets,
  pct,
  summarize,
  type RangeKey,
} from "@/lib/station-data";

const GRID_STROKE = "var(--border)";
const AXIS_FILL = "var(--muted-foreground)";
const RED = "var(--led-red)";
const ACCENT = "var(--chart-1)";

function OverviewView() {
  const [range, setRange] = useState<RangeKey>("7d");
  const events = eventsForRange(ACCESS_EVENTS, range);
  const stats = summarize(events);
  const prev = summarize(eventsForPrevRange(ACCESS_EVENTS, range));
  const series = dailySeries(events, range);
  const hourly = hourlyBuckets(events);
  const recent = events.slice(0, 8);
  const rangeLabel =
    range === "today" ? "today" : range === "7d" ? "last 7 days" : "last 30 days";

  // banner derives from controller connectivity + active critical alerts
  const activeCritical = ALERTS.some(
    (a) => a.status === "Active" && a.severity === "Critical"
  );
  const banner = !DEVICE.online
    ? { tone: "red" as const, label: "Offline", detail: "Controller connection lost — check Device & Door." }
    : activeCritical
      ? { tone: "amber" as const, label: "Attention required", detail: "Active critical alert — review Alerts & Events." }
      : { tone: "green" as const, label: "Operational", detail: `Controller online · ${ALERTS.filter((a) => a.status === "Active").length} active alert(s)` };

  const grantedDelta = prev.granted
    ? stats.granted / prev.granted - 1
    : null;

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      {/* header + date range */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            Station command centre
          </h2>
          <p className="text-xs text-muted-foreground">
            {STATION.name} · {STATION.address}
          </p>
        </div>
        <DateRange value={range} onChange={setRange} />
      </div>

      {/* system status banner */}
      <div
        role="status"
        className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-sm ${
          banner.tone === "green"
            ? "border-led-green/25 bg-led-green/10"
            : banner.tone === "amber"
              ? "border-led-amber/25 bg-led-amber/10"
              : "border-led-red/25 bg-led-red/10"
        }`}
      >
        <ShieldCheck aria-hidden className="size-4 shrink-0" />
        <span className="font-medium">{banner.label}</span>
        <span className="text-xs text-muted-foreground">{banner.detail}</span>
      </div>

      {/* KPI row */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard
          label="Total scans"
          value={stats.total}
          hint={`attempts incl. denied · ${rangeLabel}`}
          icon={ScanLine}
          href="/logs"
        />
        <KpiCard
          label="Granted access"
          value={stats.granted}
          hint={
            grantedDelta === null ? (
              "no prior period data"
            ) : (
              <span className="inline-flex items-center gap-1">
                {grantedDelta >= 0 ? (
                  <TrendingUp aria-hidden className="size-3 text-led-green" />
                ) : (
                  <TrendingDown aria-hidden className="size-3 text-led-red" />
                )}
                {pct(Math.abs(grantedDelta))} vs previous period
              </span>
            )
          }
          icon={CheckCircle2}
          tone="green"
          href="/logs?result=Granted"
        />
        <KpiCard
          label="Denied access"
          value={stats.denied}
          hint="click to open filtered logs"
          icon={XCircle}
          tone="red"
          href="/logs?result=Denied"
        />
        <KpiCard
          label="Success rate"
          value={pct(stats.successRate)}
          hint={`${stats.granted} of ${stats.total} attempts · ${rangeLabel}`}
          icon={Gauge}
        />
        <KpiCard
          label="Controller status"
          value={DEVICE.online ? "Online" : "Offline"}
          hint={`last seen ${DEVICE.lastSeen}`}
          icon={Cpu}
          tone={DEVICE.online ? "green" : "red"}
          href="/device"
        />
      </div>

      {/* row 2: activity line + outcome donut */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel
          title="Access activity"
          description={`Granted and denied scans · ${rangeLabel}`}
          className="lg:col-span-2"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: AXIS_FILL, fontSize: 11 }} tickLine={false} axisLine={{ stroke: GRID_STROKE }} />
                <YAxis tick={{ fill: AXIS_FILL, fontSize: 11 }} tickLine={false} axisLine={false} width={40} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: GRID_STROKE, fontSize: 12 }} />
                <Line type="monotone" dataKey="granted" name="Granted" stroke={ACCENT} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                <Line type="monotone" dataKey="denied" name="Denied" stroke={RED} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Access outcomes" description={`Granted vs denied · ${rangeLabel}`}>
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <div className="relative h-40 w-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: "Granted", value: stats.granted },
                      { name: "Denied", value: stats.denied },
                    ]}
                    dataKey="value"
                    innerRadius={50}
                    outerRadius={70}
                    startAngle={90}
                    endAngle={-270}
                    strokeWidth={0}
                  >
                    <Cell fill={ACCENT} />
                    <Cell fill={RED} />
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 8, borderColor: GRID_STROKE, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-semibold tabular-nums">{stats.total}</span>
                <span className="text-xs text-muted-foreground">total scans</span>
              </div>
            </div>
            <div className="w-full space-y-1.5 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2">
                  <span className="size-2 rounded-full" style={{ backgroundColor: ACCENT }} />
                  Granted
                </span>
                <span className="tabular-nums text-muted-foreground">
                  {stats.granted} · {pct(stats.successRate)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2">
                  <span className="size-2 rounded-full" style={{ backgroundColor: RED }} />
                  Denied
                </span>
                <span className="tabular-nums text-muted-foreground">
                  {stats.denied} · {pct(1 - stats.successRate)}
                </span>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      {/* row 3: usage by hour + device/door status */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Usage by hour" description="Scan volume grouped by hour of day">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourly} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="hour" tick={{ fill: AXIS_FILL, fontSize: 10 }} tickLine={false} axisLine={{ stroke: GRID_STROKE }} interval={2} />
                <YAxis tick={{ fill: AXIS_FILL, fontSize: 11 }} tickLine={false} axisLine={false} width={40} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: GRID_STROKE, fontSize: 12 }} />
                <Bar dataKey="scans" name="Scans" fill={ACCENT} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel
          title="Device & door status"
          description="Controller connection and door state where a contact sensor is installed"
          action={
            <Link href="/device" className="text-xs font-medium text-primary hover:underline">
              Device &amp; Door
            </Link>
          }
        >
          <dl className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">Controller</dt>
              <dd className="flex items-center gap-2 font-medium">
                <Led status={DEVICE.online ? "online" : "offline"} />
                {DEVICE.online ? "Online" : "Offline"}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">Device</dt>
              <dd className="font-mono text-xs">{DEVICE.model} · {DEVICE.serial}</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">Last seen</dt>
              <dd className="font-mono text-xs">{DEVICE.lastSeen}</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">
                Door contact
                <span className="ml-1 text-xs text-muted-foreground/70">(physical sensor)</span>
              </dt>
              <dd className="flex items-center gap-2 font-medium">
                <DoorClosed aria-hidden className="size-4 text-muted-foreground" />
                {DEVICE.doorContact}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">Lock relay command</dt>
              <dd className="font-mono text-xs">{DEVICE.relayState}</dd>
            </div>
            <p className="rounded-md bg-muted/60 p-2 text-xs text-muted-foreground">
              Relay command is not proof the door physically opened — state above
              comes from the wired door contact sensor.
            </p>
          </dl>
        </Panel>
      </div>

      {/* row 4: custom recharts panels (no shadcn primitives) */}
      <div className="grid gap-4 lg:grid-cols-2">
        <AccessRhythm events={events} />
        <DenialReasons events={events} />
      </div>

      {/* recent activity */}
      <Panel
        title="Recent access activity"
        description="Latest authentication attempts at the washroom reader"
        action={
          <Link href="/logs" className="text-xs font-medium text-primary hover:underline">
            View all logs
          </Link>
        }
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Person</TableHead>
              <TableHead>Card</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recent.map((e) => {
              const person = PEOPLE.find((p) => p.id === e.personId);
              return (
                <TableRow key={e.id}>
                  <TableCell className="font-mono text-xs">
                    {fmtDay(e.ts)} {fmtTime(e.ts)}
                  </TableCell>
                  <TableCell>{person ? person.name : <span className="text-muted-foreground">Unresolved</span>}</TableCell>
                  <TableCell className="font-mono text-xs">{e.maskedCard}</TableCell>
                  <TableCell><ResultBadge result={e.result} /></TableCell>
                  <TableCell className="text-muted-foreground">{e.reason ?? "—"}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Panel>
    </div>
  );
}

export { OverviewView };
