"use client";

import { Cpu, DoorClosed, Network, RefreshCw, Wrench } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
import { Led } from "@/common/led";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DEVICE, DEVICE_EVENTS, STATION } from "@/lib/station-data";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b py-2 text-sm last:border-0">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function DeviceDoorView() {
  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Device &amp; door</h2>
        <p className="text-xs text-muted-foreground">
          Whether the access-control hardware is connected and operating
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* device summary */}
        <Panel
          title="Device summary"
          description="Assigned access controller"
          action={
            <span className="inline-flex items-center gap-2 text-xs font-medium">
              <Led status={DEVICE.online ? "online" : "offline"} />
              {DEVICE.online ? "Online" : "Offline"}
            </span>
          }
        >
          <dl>
            <Row label="Model" value={DEVICE.model} />
            <Row label="Serial" value={<span className="font-mono text-xs">{DEVICE.serial}</span>} />
            <Row label="Station" value={STATION.name} />
            <Row label="Firmware" value={<span className="font-mono text-xs">{DEVICE.firmware}</span>} />
          </dl>
        </Panel>

        {/* connection details */}
        <Panel title="Connection" description="Credentials are stored securely and never displayed">
          <dl>
            <Row label="Method" value={DEVICE.connection} />
            <Row label="IP reference" value={<span className="font-mono text-xs">{DEVICE.ip}</span>} />
            <Row label="Client status" value={<ToneBadge tone="green">Connected</ToneBadge>} />
            <Row label="Last seen" value={<span className="font-mono text-xs">{DEVICE.lastSeen}</span>} />
          </dl>
        </Panel>

        {/* door / relay status */}
        <Panel title="Door & relay status" description="Relay command vs physical sensor state shown separately">
          <dl>
            <Row label="Door" value={DEVICE.doorName} />
            <Row label="Lock relay command" value={<span className="font-mono text-xs">{DEVICE.relayState}</span>} />
            <Row
              label="Door contact (physical)"
              value={
                DEVICE.doorContactWired ? (
                  <span className="inline-flex items-center gap-2 font-medium">
                    <DoorClosed aria-hidden className="size-4 text-muted-foreground" />
                    {DEVICE.doorContact}
                  </span>
                ) : (
                  <ToneBadge tone="grey">Unknown — no sensor wired</ToneBadge>
                )
              }
            />
          </dl>
          <p className="mt-2 rounded-md bg-muted/60 p-2 text-xs text-muted-foreground">
            A relay command is not proof the door physically opened — physical
            state requires the wired door contact sensor.
          </p>
        </Panel>

        {/* sync status */}
        <Panel title="Sync status" description="Configuration pushes to the controller">
          <dl>
            <Row label="Last successful sync" value={<span className="font-mono text-xs">{DEVICE.lastSync}</span>} />
            <Row label="Pending changes" value={DEVICE.pendingChanges === 0 ? "None" : <ToneBadge tone="amber">{DEVICE.pendingChanges} pending</ToneBadge>} />
            <Row label="Sync errors" value={DEVICE.lastError ?? <ToneBadge tone="green">None</ToneBadge>} />
          </dl>
        </Panel>
      </div>

      {/* device event history */}
      <Panel
        title="Device event history"
        description="Connectivity changes, restarts and controller events captured by the integration"
        action={<Cpu aria-hidden className="size-4 text-muted-foreground" />}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Detail</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {DEVICE_EVENTS.map((e) => (
              <TableRow key={e.ts + e.type}>
                <TableCell className="font-mono text-xs">{e.ts}</TableCell>
                <TableCell className="font-medium">{e.type}</TableCell>
                <TableCell className="text-muted-foreground">{e.detail}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>

      <div className="grid gap-4 md:grid-cols-2">
        {/* device configuration */}
        <Panel title="Device configuration" description="Supported integration settings only">
          <dl>
            <Row label="Door name" value={DEVICE.doorName} />
            <Row label="Device label" value="Washroom Access — Station 04" />
            <Row label="Reader protocol" value="Wiegand / RS-485 (documented, unvalidated)" />
          </dl>
          <p className="mt-2 text-xs text-muted-foreground">
            Low-level controller settings are not exposed to station admins.
          </p>
        </Panel>

        {/* troubleshooting */}
        <Panel
          title="Troubleshooting"
          description="Connection checklist and last error"
          action={<Wrench aria-hidden className="size-4 text-muted-foreground" />}
        >
          <ul className="space-y-2 text-sm">
            {[
              { icon: Network, text: "Controller reachable over the station network (ping 10.20.4.11)." },
              { icon: RefreshCw, text: "SmartPSS Lite client connected and logged in with a device operator account." },
              { icon: DoorClosed, text: "Door contact wiring sealed — tamper input reporting normally." },
            ].map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-2">
                <Icon aria-hidden className="mt-0.5 size-4 shrink-0 text-led-green" />
                {text}
              </li>
            ))}
          </ul>
          <p className="mt-2 rounded-md bg-muted/60 p-2 text-xs text-muted-foreground">
            {DEVICE.lastError
              ? `Last error: ${DEVICE.lastError}`
              : "No connection errors recorded. Remote repair is not available — contact the site technician."}
          </p>
        </Panel>
      </div>
    </div>
  );
}

export { DeviceDoorView };
