import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { AccessEvent } from "@/lib/station-data";

// Day split for the radar; hours are UTC to match the mock event generator.
const SEGMENTS = [
  { label: "Night", from: 0, to: 5 },
  { label: "Morning", from: 6, to: 9 },
  { label: "Midday", from: 10, to: 13 },
  { label: "Afternoon", from: 14, to: 17 },
  { label: "Evening", from: 18, to: 21 },
  { label: "Late", from: 22, to: 23 },
] as const;

type RhythmPoint = { segment: string; scans: number; share: number };

function bucketize(events: AccessEvent[]): RhythmPoint[] {
  const total = events.length;
  return SEGMENTS.map((segment) => {
    const scans = events.filter((event) => {
      const hour = new Date(event.ts).getUTCHours();
      return hour >= segment.from && hour <= segment.to;
    }).length;
    return {
      segment: segment.label,
      scans,
      share: total ? scans / total : 0,
    };
  });
}

function RhythmTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: RhythmPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-popover-foreground">{point.segment}</p>
      <p className="mt-0.5 text-muted-foreground">
        <span className="font-mono tabular-nums text-foreground">
          {point.scans}
        </span>{" "}
        scans · {Math.round(point.share * 100)}% of period
      </p>
    </div>
  );
}

export function AccessRhythm({ events }: { events: AccessEvent[] }) {
  const data = bucketize(events);
  const peak = data.reduce((best, item) =>
    item.scans > best.scans ? item : best
  );

  return (
    <section className="card-glow flex flex-col rounded-xl border border-border/70 bg-card p-5 shadow-sm">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight">Access rhythm</h3>
          <p className="text-xs text-muted-foreground">
            When the washroom reader sees the most traffic
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary">
          Peak · {peak.segment}
        </span>
      </header>

      <div
        role="img"
        aria-label={`Radar chart of washroom scans by day segment. Busiest: ${peak.segment} with ${peak.scans} scans.`}
        className="mt-2 h-64"
      >
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="74%">
            <defs>
              <radialGradient id="rhythm-fill" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                <stop
                  offset="100%"
                  stopColor="var(--chart-1)"
                  stopOpacity={0.06}
                />
              </radialGradient>
            </defs>
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis
              dataKey="segment"
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <PolarRadiusAxis tick={false} axisLine={false} />
            <Tooltip content={<RhythmTooltip />} />
            <Radar
              dataKey="scans"
              name="Scans"
              stroke="var(--chart-1)"
              strokeWidth={2}
              fill="url(#rhythm-fill)"
              dot={{ r: 3, fill: "var(--chart-1)", strokeWidth: 0 }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-auto flex items-center justify-between gap-3 border-t border-border/60 pt-3 text-xs text-muted-foreground">
        <span>{events.length} scans in period</span>
        <span className="tabular-nums">
          busiest {peak.segment.toLowerCase()} · {peak.scans}
        </span>
      </div>
    </section>
  );
}
