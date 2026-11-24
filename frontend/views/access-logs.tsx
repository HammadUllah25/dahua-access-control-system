"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Download, RefreshCw, Search } from "lucide-react";
import { toast } from "react-toastify";

import {
  listAccessEventsAction,
  type AccessEventRecord,
} from "@/actions/access-events";
import { listStationsAction, type StationRecord } from "@/actions/stations";
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
  eventTime,
  maskCard,
  personLabel,
  reasonLabel,
  resultLabel,
} from "@/lib/event-format";
import { fmtDay, fmtTimeSec, rangeToDates, type RangeKey } from "@/lib/station-data";

const PAGE_SIZE = 25;
// shortcut: loads the newest 500 events (backend max per request); page with offset once sites exceed that per range.
const FETCH_LIMIT = 500;

function AccessLogsView() {
  const params = useSearchParams();
  const initialResult = params.get("result");
  const [range, setRange] = useState<RangeKey>("30d");
  const [result, setResult] = useState<"All" | "Granted" | "Denied">(
    initialResult === "Granted" || initialResult === "Denied" ? initialResult : "All"
  );
  const [stationId, setStationId] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [visible, setVisible] = useState(PAGE_SIZE);
  const [detail, setDetail] = useState<AccessEventRecord | null>(null);
  const [events, setEvents] = useState<AccessEventRecord[]>([]);
  const [stations, setStations] = useState<StationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [eventRes, stationRes] = await Promise.all([
      listAccessEventsAction({
        ...rangeToDates(range),
        station_id: stationId === "all" ? undefined : Number(stationId),
        limit: FETCH_LIMIT,
      }),
      listStationsAction(),
    ]);
    if (!eventRes.success) {
      setError(eventRes.error);
      toast.error(eventRes.raw ?? eventRes.error);
    } else {
      setEvents(eventRes.data);
      setError(null);
    }
    if (stationRes.success) setStations(stationRes.data);
    setVisible(PAGE_SIZE);
    setLoading(false);
  }, [range, stationId]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return events.filter((e) => {
      if (result !== "All" && resultLabel(e) !== result) return false;
      if (!q) return true;
      return [String(e.id), e.card_number, e.station_name, personLabel(e), e.device_name]
        .some((value) => value?.toLowerCase().includes(q));
    });
  }, [events, result, query]);

  const exportCsv = () => {
    const header = "id,timestamp,station,person,card,result,reason,device,door";
    const cell = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const rows = filtered.map((e) =>
      [
        e.id,
        eventTime(e),
        e.station_name,
        personLabel(e),
        maskCard(e.card_number),
        resultLabel(e),
        reasonLabel(e),
        e.device_serial_number ?? e.device_name,
        e.door_name ?? e.door_number,
      ].map(cell).join(",")
    );
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
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw aria-hidden className={loading ? "animate-spin" : undefined} />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={filtered.length === 0}>
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
              aria-label="Search access logs"
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
          <Select value={stationId} onValueChange={(v) => setStationId(v ?? "all")}>
            <SelectTrigger size="sm" className="w-52 text-xs">
              <SelectValue placeholder="All stations" />
            </SelectTrigger>
            <SelectContent alignItemWithTrigger={false}>
              <SelectItem value="all">All stations</SelectItem>
              {stations.map((station) => (
                <SelectItem key={station.id} value={String(station.id)}>
                  {station.name}
                  {station.city ? ` · ${station.city}` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Panel>

      {/* logs table */}
      <Panel
        title="Records"
        description={
          loading
            ? "Loading events…"
            : `${filtered.length} matching events · showing ${shown.length}`
        }
      >
        {error ? (
          <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            {error}
          </p>
        ) : null}
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
              const label = personLabel(e);
              return (
                <TableRow
                  key={e.id}
                  className="cursor-pointer"
                  onClick={() => setDetail(e)}
                >
                  <TableCell className="font-mono text-xs">
                    {fmtDay(eventTime(e))} {fmtTimeSec(eventTime(e))}
                  </TableCell>
                  <TableCell>{e.station_name ?? "—"}</TableCell>
                  <TableCell
                    className={label === "Unresolved" ? "text-muted-foreground" : undefined}
                  >
                    {label}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{maskCard(e.card_number)}</TableCell>
                  <TableCell>
                    <ResultBadge result={resultLabel(e)} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {reasonLabel(e) ?? "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {e.device_serial_number ?? e.device_name ?? "—"}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {!loading && shown.length === 0 ? (
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
                  ["Timestamp", `${fmtDay(eventTime(detail))} ${fmtTimeSec(eventTime(detail))}`],
                  ["Station", detail.station_name ?? "—"],
                  ["Person", personLabel(detail)],
                  ["Card", maskCard(detail.card_number)],
                  ["Result", resultLabel(detail)],
                  ["Reason", reasonLabel(detail) ?? "—"],
                  ["Direction", detail.event_direction],
                  ["Source", `${detail.event_source} · ${detail.event_type}`],
                  ["Billable", detail.is_billable ? `Yes · ${detail.rate_applied ?? "unpriced"} ${detail.currency}` : "No"],
                  ["Device", detail.device_name ?? "—"],
                  ["Serial", detail.device_serial_number ?? "—"],
                  ["Door", detail.door_name ?? (detail.door_number ?? "—")],
                ].map(([label, value]) => (
                  <div
                    key={String(label)}
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
