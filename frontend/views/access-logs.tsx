"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Download, Search } from "lucide-react";

import { DateRange } from "@/components/dashboard/date-range";
import { Panel } from "@/components/dashboard/panel";
import { ResultBadge } from "@/components/dashboard/badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
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
  DEVICE,
  OUTLET_FOOTFALL,
  PEOPLE,
  eventsForRange,
  fmtDay,
  fmtTimeSec,
  type AccessEvent,
  type RangeKey,
} from "@/lib/station-data";

const PAGE_SIZE = 25;
const NAMED_PERSON_IDS = new Set(["P001", "P002", "P003", "P004"]);

function stationName(id: string) {
  const outlet = OUTLET_FOOTFALL.find((station) => String(station.id) === id);
  return outlet ? `${outlet.outlet} · ${outlet.city}` : id;
}

function personLabel(personId: string | null) {
  if (!personId) return "Unresolved";
  const person = PEOPLE.find((p) => p.id === personId);
  if (!person) return "Unresolved";
  return NAMED_PERSON_IDS.has(person.id) ? person.name : person.role;
}

function AccessLogsView() {
  const params = useSearchParams();
  const [range, setRange] = useState<RangeKey>("30d");
  const [resultParam] = useState<"All" | "Granted" | "Denied">(
    params.get("result") === "Granted" || params.get("result") === "Denied"
      ? (params.get("result") as "Granted" | "Denied")
      : "All"
  );
  const [result, setResult] = useState<"All" | "Granted" | "Denied">(resultParam);
  const [stationId, setStationId] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [visible, setVisible] = useState(PAGE_SIZE);
  const [detail, setDetail] = useState<AccessEvent | null>(null);

  const filtered = useMemo(() => {
    const base = eventsForRange(ACCESS_EVENTS, range);
    const q = query.trim().toLowerCase();
    return base.filter((e) => {
      if (result !== "All" && e.result !== result) return false;
      if (stationId !== "all" && e.stationId !== stationId) return false;
      if (!q) return true;
      const person = PEOPLE.find((p) => p.id === e.personId);
      const station = stationName(e.stationId);
      const label = personLabel(e.personId);
      return (
        e.id.toLowerCase().includes(q) ||
        e.maskedCard.toLowerCase().includes(q) ||
        station.toLowerCase().includes(q) ||
        e.stationId.toLowerCase().includes(q) ||
        label.toLowerCase().includes(q) ||
        (person?.name.toLowerCase().includes(q) ?? false)
      );
    });
  }, [range, result, stationId, query]);

  const exportCsv = () => {
    const header = "id,timestamp,station,person,card,result,reason,device,door";
    const rows = filtered.map((e) => {
      return [
        e.id,
        e.ts,
        stationName(e.stationId),
        personLabel(e.personId),
        e.maskedCard,
        e.result,
        e.reason ?? "",
        e.device,
        e.door,
      ].join(",");
    });
    const blob = new Blob([[header, ...rows].join("\n")], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `access-logs-${range}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const shown = filtered.slice(0, visible);

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Access logs</h2>
          <p className="text-xs text-muted-foreground">
            Monitor each station&apos;s access activity · newest first
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

      {/* filters */}
      <Panel title="Filters">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-52 flex-1">
            <Search aria-hidden className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search event, station, card or person"
              className="h-8 pl-8 text-xs"
            />
          </div>
          <div
            role="group"
            aria-label="Result filter"
            className="inline-flex rounded-lg bg-muted p-0.5"
          >
            {(["All", "Granted", "Denied"] as const).map((r) => (
              <button
                key={r}
                type="button"
                aria-pressed={result === r}
                onClick={() => {
                  setResult(r);
                  setVisible(PAGE_SIZE);
                }}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  result === r
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          <Select
            value={stationId}
            onValueChange={(v) => {
              setStationId(v ?? "all");
              setVisible(PAGE_SIZE);
            }}
          >
            <SelectTrigger size="sm" className="w-52 text-xs">
              <SelectValue placeholder="All stations" />
            </SelectTrigger>
            <SelectContent alignItemWithTrigger={false}>
              <SelectItem value="all">All stations</SelectItem>
              {OUTLET_FOOTFALL.map((station) => (
                <SelectItem key={station.id} value={String(station.id)}>
                  {station.outlet} · {station.city}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Panel>

      {/* logs table */}
      <Panel
        title="Records"
        description={`${filtered.length} matching events · showing ${shown.length}`}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Station</TableHead>
              <TableHead>Person</TableHead>
              <TableHead>Card</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Device</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((e) => {
              const label = personLabel(e.personId);
              return (
                <TableRow
                  key={e.id}
                  className="cursor-pointer"
                  onClick={() => setDetail(e)}
                >
                  <TableCell className="font-mono text-xs">
                    {fmtDay(e.ts)} {fmtTimeSec(e.ts)}
                  </TableCell>
                  <TableCell>{stationName(e.stationId)}</TableCell>
                  <TableCell
                    className={
                      label === "Unresolved" ? "text-muted-foreground" : undefined
                    }
                  >
                    {label}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{e.maskedCard}</TableCell>
                  <TableCell>
                    <ResultBadge result={e.result} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {e.reason ?? "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {e.device}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {shown.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No events match the current filters.
          </p>
        ) : shown.length < filtered.length ? (
          <div className="mt-3 flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setVisible((v) => v + PAGE_SIZE)}
            >
              Show {Math.min(PAGE_SIZE, filtered.length - shown.length)} more
            </Button>
          </div>
        ) : null}
      </Panel>

      {/* record detail drawer */}
      <Sheet
        open={detail !== null}
        onOpenChange={(open) => !open && setDetail(null)}
      >
        <SheetContent className="w-full sm:max-w-md">
          {detail ? (
            <SheetHeader className="mt-2 gap-3 text-left">
              <SheetTitle>Event {detail.id}</SheetTitle>
              <SheetDescription>
                Full record captured by the controller integration
              </SheetDescription>
              <dl className="space-y-3 text-sm">
                {[
                  ["Timestamp", `${fmtDay(detail.ts)} ${fmtTimeSec(detail.ts)}`],
                  ["Station", stationName(detail.stationId)],
                  ["Person", personLabel(detail.personId)],
                  ["Card", detail.maskedCard],
                  ["Result", detail.result],
                  ["Reason", detail.reason ?? "—"],
                  ["Device", detail.device],
                  ["Door", detail.door],
                  ["Controller", DEVICE.model],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between gap-4 border-b pb-2"
                  >
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className="text-right font-medium">{value}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-2 text-xs text-muted-foreground">
                Card identifiers stay masked in list views; full values are only
                revealed to authorised roles.
              </p>
            </SheetHeader>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export { AccessLogsView };
