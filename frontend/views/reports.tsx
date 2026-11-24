"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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

import { toast } from "react-toastify";

import {
  dashboardSummaryAction,
  listAccessEventsAction,
  usageReportAction,
  type AccessEventRecord,
  type UsageBucket,
  type UsageSummary,
} from "@/actions/access-events";
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
import { eventTime, reasonLabel } from "@/lib/event-format";
import { fmtDay, pct, rangeToDates, type RangeKey } from "@/lib/station-data";

const GRID_STROKE = "var(--border)";
const AXIS_FILL = "var(--muted-foreground)";
const RED = "var(--led-red)";
const ACCENT = "var(--chart-1)";

function ReportsView() {
  const [range, setRange] = useState<RangeKey>("30d");
  const [buckets, setBuckets] = useState<UsageBucket[]>([]);
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [events, setEvents] = useState<AccessEventRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const dates = rangeToDates(range);
    const [usageRes, summaryRes, eventRes] = await Promise.all([
      usageReportAction({ ...dates, group_by: "day" }),
      dashboardSummaryAction(dates),
      // shortcut: hourly and denial-reason blocks count the newest 500 events client-side; add backend aggregates when ranges exceed that.
      listAccessEventsAction({ ...dates, limit: 500 }),
    ]);
    const failed = [usageRes, summaryRes, eventRes].find((res) => !res.success);
    if (failed && !failed.success) {
      setError(failed.error);
      toast.error(failed.raw ?? failed.error);
    } else {
      setError(null);
    }
    if (usageRes.success) setBuckets(usageRes.data.items);
    if (summaryRes.success) setSummary(summaryRes.data);
    if (eventRes.success) setEvents(eventRes.data);
  }, [range]);

  useEffect(() => {
    void load();
  }, [load]);

  const series = buckets.map((b) => ({
    day: fmtDay(`${b.period}T00:00:00`),
    granted: b.granted_scans,
    denied: b.denied_scans,
  }));
  const hourly = useMemo(() => {
    const counts = Array.from({ length: 24 }, (_, h) => ({ hour: `${String(h).padStart(2, "0")}:00`, scans: 0 }));
    for (const e of events) counts[new Date(eventTime(e)).getHours()].scans += 1;
    return counts;
  }, [events]);
  const reasons = useMemo(() => {
    const denied = events.filter((e) => e.access_result !== "granted");
    const counts = new Map<string, number>();
    for (const e of denied) {
      const reason = reasonLabel(e) ?? "Not reported";
      counts.set(reason, (counts.get(reason) ?? 0) + 1);
    }
    return [...counts]
      .map(([reason, count]) => ({ reason, count, share: count / denied.length }))
      .sort((x, y) => y.count - x.count);
  }, [events]);
  const granted = summary?.granted_scans ?? 0;
  const denied = summary?.denied_scans ?? 0;
  const successRate = granted + denied ? granted / (granted + denied) : 0;
  const rangeLabel =
    range === "today" ? "today" : range === "7d" ? "last 7 days" : "last 30 days";

  const topHours = [...hourly]
    .sort((a, b) => b.scans - a.scans)
    .slice(0, 5);
  const busiestDay = [...series].sort((a, b) => b.granted + b.denied - (a.granted + a.denied))[0];

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
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={series.length === 0}>
            <Download aria-hidden />
            Export CSV
          </Button>
        </div>
      </div>

      {error ? (
        <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}

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
                <dd className="text-xl font-semibold tabular-nums text-led-green">{granted}</dd>
                <dd className="text-xs text-muted-foreground">{pct(successRate)} of attempts</dd>
              </div>
              <div className="rounded-lg border border-led-red/25 bg-led-red/10 p-3">
                <dt className="text-xs text-muted-foreground">Denied</dt>
                <dd className="text-xl font-semibold tabular-nums text-led-red">{denied}</dd>
                <dd className="text-xs text-muted-foreground">{pct(granted + denied ? 1 - successRate : 0)} of attempts</dd>
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
            {busiestDay ? (
              <p className="mt-2 border-t pt-2 text-xs text-muted-foreground">
                Busiest day: <span className="font-medium text-foreground">{busiestDay.day}</span> ·{" "}
                {busiestDay.granted + busiestDay.denied} scans
              </p>
            ) : null}
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
        {reasons.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No denied scans in this range.</p>
        ) : null}
      </Panel>
    </div>
  );
}

export { ReportsView };
