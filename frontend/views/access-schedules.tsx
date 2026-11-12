"use client";

import { useState } from "react";
import { CalendarCheck, CircleCheck, Clock } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CARDS,
  HOLIDAYS,
  PEOPLE,
  SCHEDULES,
  fmtDate,
  type Schedule,
} from "@/lib/station-data";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const syncTone = {
  Synced: "green",
  Pending: "amber",
  Error: "red",
} as const;

function AccessSchedulesView() {
  // shortcut: edits stay local — pushing to the controller needs the write API
  const [schedules, setSchedules] = useState<Schedule[]>(SCHEDULES);
  const [selectedId, setSelectedId] = useState(SCHEDULES[0].id);
  const [personId, setPersonId] = useState(PEOPLE[0].id);
  const [publishing, setPublishing] = useState(false);

  const selected = schedules.find((s) => s.id === selectedId) ?? schedules[0];
  const personCard = CARDS.find((c) => c.personId === personId);
  const personSchedule = schedules.find((s) => s.id === personCard?.scheduleId);

  const update = (patch: Partial<Schedule>) =>
    setSchedules(schedules.map((s) => (s.id === selectedId ? { ...s, ...patch, sync: "Pending" } : s)));

  const toggleDay = (day: number) =>
    update({
      days: selected.days.includes(day)
        ? selected.days.filter((d) => d !== day)
        : [...selected.days, day].sort((a, b) => a - b),
    });

  const publish = () => {
    setPublishing(true);
    setTimeout(() => {
      setSchedules(schedules.map((s) => (s.id === selectedId ? { ...s, sync: "Synced" } : s)));
      setPublishing(false);
    }, 800);
  };

  const previewText = selected.days.length === 0
    ? "No days selected — this schedule grants no access."
    : `${selected.days.map((d) => DAYS[d]).join(", ")} · ${selected.start}–${selected.end}`;

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Access schedules</h2>
        <p className="text-xs text-muted-foreground">
          When a credential may use the washroom · device time sections shown in plain language
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        {/* schedule list */}
        <Panel title="Schedules" className="lg:col-span-2">
          <ul className="space-y-1">
            {schedules.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(s.id)}
                  aria-pressed={s.id === selectedId}
                  className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    s.id === selectedId
                      ? "border-primary/40 bg-primary/5"
                      : "hover:bg-muted/50"
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{s.name}</span>
                    <span className="block truncate font-mono text-xs text-muted-foreground">
                      {s.start}–{s.end} · {s.days.length} day{s.days.length === 1 ? "" : "s"}/week
                    </span>
                  </span>
                  <ToneBadge tone={syncTone[s.sync]}>{s.sync}</ToneBadge>
                </button>
              </li>
            ))}
          </ul>
        </Panel>

        {/* weekly editor + preview + publish */}
        <div className="flex flex-col gap-4 lg:col-span-3">
          <Panel
            title="Weekly schedule editor"
            description="Days of week and time interval — overlaps and empty schedules are rejected"
          >
            <div className="space-y-3">
              <div className="flex flex-wrap gap-1.5">
                {DAYS.map((day, i) => (
                  <button
                    key={day}
                    type="button"
                    aria-pressed={selected.days.includes(i)}
                    onClick={() => toggleDay(i)}
                    className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                      selected.days.includes(i)
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {day}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <label className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">Start</span>
                  <Input type="time" value={selected.start} onChange={(e) => update({ start: e.target.value })} className="h-8 w-28 text-xs" />
                </label>
                <label className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">End</span>
                  <Input type="time" value={selected.end} onChange={(e) => update({ end: e.target.value })} className="h-8 w-28 text-xs" />
                </label>
                <span className="text-xs text-muted-foreground">
                  Door: {selected.door}
                </span>
              </div>
            </div>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* preview / test panel */}
            <Panel title="Preview" description="“This card can access at”">
              <p className="flex items-start gap-2 text-sm">
                <Clock aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                {previewText}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Preview mirrors the edited schedule and is an estimate until
                published to the controller.
              </p>
            </Panel>

            {/* publish */}
            <Panel title="Publish" description="Send the updated time section to the controller">
              <div className="flex items-center justify-between gap-3">
                <ToneBadge tone={syncTone[selected.sync]}>{selected.sync}</ToneBadge>
                <Button size="sm" onClick={publish} disabled={publishing || selected.sync === "Synced"}>
                  <CircleCheck aria-hidden />
                  {publishing ? "Syncing…" : "Save & publish"}
                </Button>
              </div>
            </Panel>
          </div>

          {/* credential validity summary */}
          <Panel title="Credential validity" description="Validity window is separate from the daily time schedule">
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Select value={personId} onValueChange={(v) => v && setPersonId(v)}>
                <SelectTrigger size="sm" className="w-48 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PEOPLE.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {personCard ? (
                <dl className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                  <div className="flex items-center gap-1.5">
                    <dt className="text-muted-foreground">Card</dt>
                    <dd className="font-mono">{personCard.masked}</dd>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <dt className="text-muted-foreground">Valid</dt>
                    <dd className="font-mono">
                      {personCard.validFrom} → {personCard.validTo}
                    </dd>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <dt className="text-muted-foreground">Schedule</dt>
                    <dd>{personSchedule?.name ?? "—"}</dd>
                  </div>
                </dl>
              ) : (
                <p className="text-xs text-muted-foreground">No card enrolled for this person.</p>
              )}
            </div>
          </Panel>
        </div>
      </div>

      {/* holiday calendar */}
      <Panel
        title="Holiday calendar"
        description="Special access periods on public holidays — behaviour must be validated on the installed unit"
        action={<CalendarCheck aria-hidden className="size-4 text-muted-foreground" />}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Holiday</TableHead>
              <TableHead>Access period</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {HOLIDAYS.map((h) => (
              <TableRow key={h.date}>
                <TableCell className="font-mono text-xs">{fmtDate(h.date)}</TableCell>
                <TableCell>{h.label}</TableCell>
                <TableCell className="text-muted-foreground">{h.period}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>
    </div>
  );
}

export { AccessSchedulesView };
