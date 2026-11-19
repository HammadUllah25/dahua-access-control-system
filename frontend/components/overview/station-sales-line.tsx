"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Panel } from "@/components/dashboard/panel";
import {
  STATION_SALES_SERIES_META,
  STATION_SALES_SERIES_PAST_MONTH,
  STATION_SALES_SERIES_THIS_MONTH,
} from "@/lib/station-data";

const GRID = "var(--border)";
const AXIS = "var(--muted-foreground)";
const THIS_MONTH_COLOR = "var(--chart-1)";
const PAST_MONTH_COLOR = "#d97706";

function shortName(name: string) {
  return name.length > 16 ? `${name.slice(0, 15)}…` : name;
}

const data = STATION_SALES_SERIES_META.map((m) => {
  const key = m.key as keyof (typeof STATION_SALES_SERIES_THIS_MONTH)[number];
  const thisMonth = STATION_SALES_SERIES_THIS_MONTH.reduce((sum, p) => sum + (p[key] as number), 0);
  const pastMonth = STATION_SALES_SERIES_PAST_MONTH.reduce((sum, p) => sum + (p[key] as number), 0);
  return { name: shortName(m.outlet), full: m.outlet, thisMonth, pastMonth };
});

function SalesTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ dataKey?: string; value?: number; color?: string; name?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const full = data.find((d) => d.name === label)?.full ?? label;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1.5 font-medium text-popover-foreground">{full}</p>
      <div className="space-y-1">
        {payload.map((p) => (
          <p key={String(p.dataKey)} className="flex items-center justify-between gap-3">
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <span className="inline-block size-2 rounded-full" style={{ backgroundColor: p.color }} />
              <span>{p.name}</span>
            </span>
            <span className="shrink-0 font-mono tabular-nums text-foreground">
              PKR {(p.value ?? 0).toLocaleString()}
            </span>
          </p>
        ))}
      </div>
    </div>
  );
}

export function StationSalesLine() {
  return (
    <Panel
      title="Station Total Sales Comparison"
      description="Sales (PKR) by station · This month vs Past month"
      action={<span className="rounded-full bg-led-amber/10 px-2.5 py-1 text-[11px] font-medium text-led-amber">8 stations</span>}
      className="card-glow"
    >
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 28, left: 8 }}>
            <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: AXIS, fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: GRID }}
              interval={0}
              angle={-12}
              textAnchor="end"
              height={52}
            />
            <YAxis
              tick={{ fill: AXIS, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={76}
              tickFormatter={(v) => `PKR ${(Number(v) / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<SalesTooltip />} cursor={{ stroke: "var(--muted)" }} />
            <Legend verticalAlign="bottom" height={28} iconType="plainline" />
            <Line
              type="monotone"
              dataKey="thisMonth"
              name="This month"
              stroke={THIS_MONTH_COLOR}
              strokeWidth={2.5}
              dot={{ r: 3, fill: THIS_MONTH_COLOR, strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="pastMonth"
              name="Past month"
              stroke={PAST_MONTH_COLOR}
              strokeWidth={2.5}
              dot={{ r: 3, fill: PAST_MONTH_COLOR, strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}
