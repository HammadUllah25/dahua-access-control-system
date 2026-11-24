"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, Wrench } from "lucide-react";
import { toast } from "react-toastify";

import {
  listAccessEventsAction,
  type AccessEventRecord,
} from "@/actions/access-events";
import { getDoorConfigAction, type DoorConfig } from "@/actions/device-control";
import { listDevicesAction, type DeviceListRecord } from "@/actions/get-devices";
import { listStationsAction, type StationRecord } from "@/actions/stations";
import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
import { DeviceActions } from "@/components/device/device-actions";
import { DoorConfigForm } from "@/components/device/door-config-form";
import { RemoteUnlock } from "@/components/device/remote-unlock";
import { Led } from "@/common/led";
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
import { eventTime, personLabel, reasonLabel, resultLabel } from "@/lib/event-format";
import { fmtDay, fmtTimeSec } from "@/lib/station-data";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b py-2 text-sm last:border-0">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

const when = (iso: string | null) =>
  iso ? <span className="font-mono text-xs">{fmtDay(iso)} {fmtTimeSec(iso)}</span> : "—";

function DeviceDoorView() {
  const [devices, setDevices] = useState<DeviceListRecord[]>([]);
  const [stations, setStations] = useState<StationRecord[]>([]);
  const [deviceId, setDeviceId] = useState<number | null>(null);
  const [doorConfig, setDoorConfig] = useState<DoorConfig | null>(null);
  const [doorError, setDoorError] = useState<string | null>(null);
  const [events, setEvents] = useState<AccessEventRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadDevices = useCallback(async () => {
    const [deviceRes, stationRes] = await Promise.all([listDevicesAction(), listStationsAction()]);
    if (!deviceRes.success) {
      setError(deviceRes.error);
      toast.error(deviceRes.error);
    } else {
      setDevices(deviceRes.data);
      setError(null);
      setDeviceId((current) => current ?? deviceRes.data[0]?.id ?? null);
    }
    if (stationRes.success) setStations(stationRes.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadDevices();
  }, [loadDevices]);

  const device = devices.find((d) => d.id === deviceId) ?? null;
  const online = device?.status === "online";

  // Door config is read live from the controller, so only ask when it is online.
  useEffect(() => {
    if (deviceId === null) return;
    void listAccessEventsAction({ device_id: deviceId, limit: 15 }).then((res) => {
      if (res.success) setEvents(res.data);
    });
    setDoorConfig(null);
    setDoorError(null);
    if (!online) return;
    void getDoorConfigAction(deviceId).then((res) => {
      if (res.success) setDoorConfig(res.data);
      else setDoorError(res.error);
    });
  }, [deviceId, online]);

  const station = stations.find((s) => s.id === device?.station_id);

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Device &amp; door</h2>
          <p className="text-xs text-muted-foreground">
            Whether the access-control hardware is connected and operating
          </p>
        </div>
        {devices.length > 1 ? (
          <Select value={String(deviceId)} onValueChange={(v) => v && setDeviceId(Number(v))}>
            <SelectTrigger size="sm" className="w-56 text-xs">
              <SelectValue placeholder="Choose controller" />
            </SelectTrigger>
            <SelectContent alignItemWithTrigger={false}>
              {devices.map((d) => (
                <SelectItem key={d.id} value={String(d.id)}>
                  {d.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {!loading && !error && !device ? (
        <Panel title="No controller registered">
          <p className="text-sm text-muted-foreground">Add a controller from Add Device first.</p>
        </Panel>
      ) : null}

      {device ? (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {/* device summary */}
            <Panel
              title="Device summary"
              description="Assigned access controller"
              action={
                <span className="inline-flex items-center gap-2 text-xs font-medium capitalize">
                  <Led status={online ? "online" : device.status === "offline" ? "offline" : "pending"} />
                  {device.status}
                </span>
              }
            >
              <dl>
                <Row label="Name" value={device.name} />
                <Row label="Model" value={device.model ?? "—"} />
                <Row label="Serial" value={<span className="font-mono text-xs">{device.serial_number ?? "—"}</span>} />
                <Row label="MAC" value={<span className="font-mono text-xs">{device.mac_address ?? "—"}</span>} />
                <Row label="Station" value={station ? `${station.station_code} · ${station.name}` : "Not assigned"} />
              </dl>
            </Panel>

            {/* connection details */}
            <Panel title="Connection" description="Credentials are stored encrypted and never displayed">
              <dl>
                <Row label="Address" value={<span className="font-mono text-xs">{device.host}:{device.port}</span>} />
                <Row label="Monitoring" value={device.monitoring_enabled ? "On" : <ToneBadge tone="amber">Paused</ToneBadge>} />
                <Row label="Last connected" value={when(device.last_connected_at)} />
                <Row label="Last reachable" value={when(device.last_tcp_reachable_at)} />
                <Row label="Failed checks in a row" value={device.consecutive_failures} />
              </dl>
              <div className="mt-3">
                <DeviceActions deviceId={device.id} online={online} onDone={() => void loadDevices()} />
              </div>
            </Panel>

            {/* door sensor config */}
            <Panel title="Door sensor & unlock" description="Read from and written to the controller">
              {online && doorConfig ? (
                <DoorConfigForm key={device.id} config={doorConfig} onSaved={setDoorConfig} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {!online
                    ? "Connect the controller to read its door settings."
                    : doorError ?? "Reading door settings from the controller…"}
                </p>
              )}
              <p className="mt-3 rounded-md bg-muted/60 p-2 text-xs text-muted-foreground">
                A relay command is not proof the door physically opened — physical
                state requires the wired door contact sensor.
              </p>
            </Panel>

            {/* card sync status */}
            <Panel title="Card sync status" description="Controller card list vs the central record">
              <dl>
                <Row label="Inventory status" value={<span className="capitalize">{device.inventory_status.replaceAll("_", " ")}</span>} />
                <Row label="Cards expected" value={device.expected_card_count ?? "—"} />
                <Row label="Cards on controller" value={device.observed_card_count ?? "—"} />
                <Row label="Last inventory check" value={when(device.last_inventory_at)} />
              </dl>
              {online ? (
                <div className="mt-3">
                  <RemoteUnlock deviceId={device.id} onDone={() => void loadDevices()} />
                </div>
              ) : null}
            </Panel>
          </div>

          {/* recent controller events */}
          <Panel
            title="Recent controller events"
            description="Latest scans and remote commands reported by this controller"
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
                {events.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell className="font-mono text-xs">
                      {fmtDay(eventTime(e))} {fmtTimeSec(eventTime(e))}
                    </TableCell>
                    <TableCell className="font-medium">
                      {e.event_type === "REMOTE_UNLOCK" ? "Remote unlock" : resultLabel(e)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {personLabel(e)}
                      {reasonLabel(e) ? ` · ${reasonLabel(e)}` : ""}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {events.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">No events from this controller yet.</p>
            ) : null}
          </Panel>

          {/* troubleshooting */}
          <Panel
            title="Troubleshooting"
            description="Last error reported by the connection monitor"
            action={<Wrench aria-hidden className="size-4 text-muted-foreground" />}
          >
            <p className="text-sm">
              {device.last_error ?? "No connection errors recorded."}
            </p>
          </Panel>
        </>
      ) : null}
    </div>
  );
}

export { DeviceDoorView };
