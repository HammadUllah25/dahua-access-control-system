"use client";

import { Panel } from "@/components/dashboard/panel";
import { SeverityBadge, ToneBadge } from "@/components/dashboard/badges";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SENSOR_ALERT_LOGS } from "@/lib/station-data";

function statusTone(status: "Active" | "Acknowledged" | "Resolved") {
  if (status === "Active") return "red" as const;
  if (status === "Acknowledged") return "amber" as const;
  return "green" as const;
}

export function SensorAlertLogs() {
  return (
    <Panel
      title="Sensor Alert Logs"
      description="Recent sensor and controller alerts (showing 10)"
      action={<span className="rounded-full bg-led-amber/10 px-2.5 py-1 text-[11px] font-medium text-led-amber">10 alerts</span>}
      className="card-glow"
    >
      <Table containerClassName="overflow-visible">
        <TableHeader>
          <TableRow>
            <TableHead className="whitespace-normal">Time</TableHead>
            <TableHead className="whitespace-normal">Station</TableHead>
            <TableHead className="whitespace-normal">Sensor / Alert</TableHead>
            <TableHead className="whitespace-normal">Severity</TableHead>
            <TableHead className="whitespace-normal">Status</TableHead>
            <TableHead className="whitespace-normal">Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {SENSOR_ALERT_LOGS.map((log) => (
            <TableRow key={log.id}>
              <TableCell className="whitespace-normal font-mono text-xs">{log.ts}</TableCell>
              <TableCell className="whitespace-normal break-words">{log.station}</TableCell>
              <TableCell className="whitespace-normal break-words font-medium">{log.sensor}</TableCell>
              <TableCell className="whitespace-normal"><SeverityBadge severity={log.severity} /></TableCell>
              <TableCell className="whitespace-normal"><ToneBadge tone={statusTone(log.status)}>{log.status}</ToneBadge></TableCell>
              <TableCell className="whitespace-normal break-words text-xs leading-relaxed text-muted-foreground">{log.detail}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Panel>
  );
}
