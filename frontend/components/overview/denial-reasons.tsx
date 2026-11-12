import {
  Bar,
  BarChart,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { denialReasons, type AccessEvent } from "@/lib/station-data";

type ReasonPoint = { reason: string; count: number; share: number };

function ReasonTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: ReasonPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-popover-foreground">{point.reason}</p>
      <p className="mt-0.5 text-muted-foreground">
        <span className="font-mono tabular-nums text-foreground">
          {point.count}
        </span>{" "}
        denied · {Math.round(point.share * 100)}% of denials
      </p>
    </div>
  );
}

export function DenialReasons({ events }: { events: AccessEvent[] }) {
  const reasons = denialReasons(events);
  const denied = reasons.reduce((sum, item) => sum + item.count, 0);
  const share = events.length ? denied / events.length : 0;

  return (
    <section className="card-glow flex flex-col rounded-xl border border-border/70 bg-card p-5 shadow-sm">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight">
            Denied by reason
          </h3>
          <p className="text-xs text-muted-foreground">
            Why the reader refused a card
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-led-red/10 px-2.5 py-1 text-[11px] font-medium text-led-red">
          {denied} denied · {(share * 100).toFixed(1)}%
        </span>
      </header>

      {reasons.length === 0 ? (
        <div className="flex h-64 items-center justify-center text-xs text-muted-foreground">
          No denied attempts in this period.
        </div>
      ) : (
        <div
          role="img"
          aria-label={`Horizontal bar chart of denied access by reason. ${reasons
            .map((item) => `${item.reason}: ${item.count}`)
            .join(", ")}.`}
          className="mt-2 h-64"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={reasons}
              layout="vertical"
              margin={{ top: 4, right: 36, bottom: 4, left: 8 }}
              barCategoryGap={10}
            >
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="reason"
                width={140}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              />
              <Tooltip
                cursor={{ fill: "var(--muted)", opacity: 0.6 }}
                content={<ReasonTooltip />}
              />
              <Bar
                dataKey="count"
                name="Denied"
                fill="var(--led-red)"
                radius={[0, 4, 4, 0]}
                barSize={16}
                background={{ fill: "var(--muted)" }}
              >
                <LabelList
                  dataKey="count"
                  position="right"
                  fill="var(--foreground)"
                  fontSize={11}
                  fontWeight={600}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <p className="mt-auto border-t border-border/60 pt-3 text-xs text-muted-foreground">
        Percentage is of all scans in the selected period.
      </p>
    </section>
  );
}
