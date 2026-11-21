"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { GENDER_ENTRY_LOGS, GENDER_ENTRY_TOTALS } from "@/lib/station-data";

const WOMEN = "#a855f7";
const MEN = "#0ea5e9";
const GRID = "var(--border)";

function washroomBadge(washroom: "Women’s Washroom" | "Men’s Washroom") {
  const women = washroom === "Women’s Washroom";
  return (
    <span
      className="inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium"
      style={{
        color: women ? WOMEN : MEN,
        borderColor: `color-mix(in oklab, ${women ? WOMEN : MEN} 30%, transparent)`,
        background: `color-mix(in oklab, ${women ? WOMEN : MEN} 12%, transparent)`,
      }}
    >
      {washroom}
    </span>
  );
}

function resultBadge(result: "Granted" | "Denied" | "Pending") {
  if (result === "Granted") return <ToneBadge tone="green">Granted</ToneBadge>;
  if (result === "Denied") return <ToneBadge tone="red">Denied</ToneBadge>;
  return <ToneBadge tone="amber">Pending</ToneBadge>;
}

export function GenderEntries() {
  const total = GENDER_ENTRY_TOTALS.women + GENDER_ENTRY_TOTALS.men;
  const data = [
    { name: "Women’s Washroom", value: GENDER_ENTRY_TOTALS.women, color: WOMEN },
    { name: "Men’s Washroom", value: GENDER_ENTRY_TOTALS.men, color: MEN },
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-4">
      <Panel
        title="Washroom Entries (Gender-wise)"
        description="Women’s and men’s washroom entries shown separately"
        action={
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2 py-0.5">
              <span className="size-2 rounded-full" style={{ background: WOMEN }} />Women: {GENDER_ENTRY_TOTALS.women.toLocaleString()}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2 py-0.5">
              <span className="size-2 rounded-full" style={{ background: MEN }} />Men: {GENDER_ENTRY_TOTALS.men.toLocaleString()}
            </span>
          </div>
        }
        className="card-glow lg:col-span-3"
      >
        <Table containerClassName="overflow-visible">
          <TableHeader>
            <TableRow>
              <TableHead className="whitespace-normal">Time</TableHead>
              <TableHead className="whitespace-normal">Station</TableHead>
              <TableHead className="whitespace-normal">Washroom</TableHead>
              <TableHead className="whitespace-normal">Person / Type</TableHead>
              <TableHead className="whitespace-normal">Card</TableHead>
              <TableHead className="whitespace-normal">Result</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {GENDER_ENTRY_LOGS.map((e) => (
              <TableRow key={e.id}>
                <TableCell className="whitespace-normal font-mono text-xs">{e.ts}</TableCell>
                <TableCell className="whitespace-normal break-words">{e.station}</TableCell>
                <TableCell className="whitespace-nowrap">{washroomBadge(e.washroom)}</TableCell>
                <TableCell className="whitespace-normal break-words">
                  {e.person} <span className="text-xs text-muted-foreground">({e.personType})</span>
                </TableCell>
                <TableCell className="whitespace-normal font-mono text-xs">{e.card}</TableCell>
                <TableCell className="whitespace-normal">{resultBadge(e.result)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>

      <Panel
        title="Gender Entry Split"
        description="Separate totals for women’s and men’s washrooms"
        className="card-glow"
      >
        <div className="flex h-full flex-col items-center gap-4">
          <div className="relative mt-1 h-52 w-full max-w-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" innerRadius="68%" outerRadius="95%" startAngle={90} endAngle={-270} strokeWidth={0}>
                  {data.map((d) => <Cell key={d.name} fill={d.color} />)}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-semibold tabular-nums">{total.toLocaleString()}</span>
              <span className="text-xs text-muted-foreground">Total entries</span>
            </div>
          </div>
          <div className="w-full space-y-2 text-sm">
            <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2">
              <span className="inline-flex items-center gap-2"><span className="size-2 rounded-full" style={{ background: WOMEN }} />Women’s Washroom</span>
              <span className="font-semibold tabular-nums">{GENDER_ENTRY_TOTALS.women.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2">
              <span className="inline-flex items-center gap-2"><span className="size-2 rounded-full" style={{ background: MEN }} />Men’s Washroom</span>
              <span className="font-semibold tabular-nums">{GENDER_ENTRY_TOTALS.men.toLocaleString()}</span>
            </div>
            <p className="text-xs text-muted-foreground">Entries tracked separately for women’s and men’s washrooms.</p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
