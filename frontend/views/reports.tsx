"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { DateRange } from "@/components/dashboard/date-range";
import { Panel } from "@/components/dashboard/panel";
import { Button } from "@/components/ui/button";
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
  dailySeries,
  denialReasons,
  eventsForRange,
  hourlyBuckets,
  pct,
  summarize,
  type RangeKey,
} from "@/lib/station-data";

const GRID_STROKE = "var(--border)";
const AXIS_FILL = "var(--muted-foreground)";
const RED = "var(--led-red)";
const ACCENT = "var(--chart-1)";

function ReportsView() {
  const [range, setRange] = useState<RangeKey>("30d");
  const events = eventsForRange(ACCESS_EVENTS, range);
  const stats = summarize(events);
  const series = dailySeries(events, range);
  const hourly = hourlyBuckets(events);
  const reasons = denialReasons(events);
  const rangeLabel =
    range === "today" ? "today" : range === "7d" ? "last 7 days" : "last 30 days";

  const topHours = [...hourly]
    .sort((a, b) => b.scans - a.scans)
    .slice(0, 5);
  const busiestDay = [...series].sort((a, b) => a.granted + a.denied < b.granted + b.denied ? 1 : -1)[0];

  const exportCsv = () => {
    const header = "date,granted,denied";
    const rows = series.map((d) => [d.day, d.granted, d.denied].join(","));
    const blob = new Blob([[header, ...rows].join("\n")], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `usage-report-${range}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Reports</h2>
          <p className="text-xs text-muted-foreground">
            Usage patterns and exportable records · all blocks use the same range
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DateRange value={range} onChange={setRange} />
          <Button variant="outline" size="sm" onClick={exportCsv}>
            <Download aria-hidden />
            Export CSV
          </Button>
        </div>
      </div>

      {/* usage trend */}
      <Panel title="Usage trend" description={`Daily scan totals with granted/denied split · ${rangeLabel}`}>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={{ fill: AXIS_FILL, fontSize: 11 }} tickLine={false} axisLine={{ stroke: GRID_STROKE }} />
              <YAxis tick={{ fill: AXIS_FILL, fontSize: 11 }} tickLine={false} axisLine={false} width={40} allowDecimals={false} />
              <Tooltip contentStyle={{ borderRadius: 8, borderColor: GRID_STROKE, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="granted" name="Granted" stackId="a" fill={ACCENT} />
              <Bar dataKey="denied" name="Denied" stackId="a" fill={RED} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* hourly usage */}
        <Panel title="Hourly usage" description="Scan distribution by hour — useful for staffing and cleaning planning">
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

        {/* outcome breakdown + top periods */}
        <div className="flex flex-col gap-4">
          <Panel title="Outcome breakdown" description={`Granted vs denied · ${rangeLabel}`}>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border border-led-green/25 bg-led-green/10 p-3">
                <dt className="text-xs text-muted-foreground">Granted</dt>
                <dd className="text-xl font-semibold tabular-nums text-led-green">{stats.granted}</dd>
                <dd className="text-xs text-muted-foreground">{pct(stats.successRate)} of attempts</dd>
              </div>
              <div className="rounded-lg border border-led-red/25 bg-led-red/10 p-3">
                <dt className="text-xs text-muted-foreground">Denied</dt>
                <dd className="text-xl font-semibold tabular-nums text-led-red">{stats.denied}</dd>
                <dd className="text-xs text-muted-foreground">{pct(1 - stats.successRate)} of attempts</dd>
              </div>
            </dl>
          </Panel>

          <Panel title="Top usage periods" description="Busiest hours and day in the selected range">
            <ol className="space-y-1.5 text-sm">
              {topHours.map((h, i) => (
                <li key={h.hour} className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2">
                    <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {i + 1}
                    </span>
                    {h.hour}
                  </span>
                  <span className="tabular-nums text-muted-foreground">{h.scans} scans</span>
                </li>
              ))}
            </ol>
            <p className="mt-2 border-t pt-2 text-xs text-muted-foreground">
              Busiest day: <span className="font-medium text-foreground">{busiestDay.day}</span> ·{" "}
              {busiestDay.granted + busiestDay.denied} scans
            </p>
          </Panel>
        </div>
      </div>

      {/* denial reasons */}
      <Panel
        title="Denial reasons"
        description="Most frequent rejection reasons returned by the controller"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Reason</TableHead>
              <TableHead>Count</TableHead>
              <TableHead>Share of denials</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {reasons.map((r) => (
              <TableRow key={r.reason}>
                <TableCell className="font-medium">{r.reason}</TableCell>
                <TableCell className="tabular-nums">{r.count}</TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-2">
                    <span className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
                      <span className="block h-full rounded-full bg-led-red" style={{ width: `${r.share * 100}%` }} />
                    </span>
                    <span className="tabular-nums text-xs text-muted-foreground">{pct(r.share)}</span>
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>
    </div>
  );
}

export { ReportsView };
