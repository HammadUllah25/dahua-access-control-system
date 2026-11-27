"use client";

import { useCallback, useEffect, useState } from "react";
import { DoorClosed, RefreshCw, ServerCog } from "lucide-react";
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
import { CardSyncActions } from "@/components/device/card-sync-actions";
import { DeviceActions } from "@/components/device/device-actions";
import { DoorConfigForm } from "@/components/device/door-config-form";
import { RemoteUnlock } from "@/components/device/remote-unlock";
import { Led } from "@/common/led";
import { Button } from "@/components/ui/button";
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

const onOff = (value: boolean) => (
  <ToneBadge tone={value ? "green" : "grey"}>{value ? "On" : "Off"}</ToneBadge>
);

function DeviceDoorView() {
  const [devices, setDevices] = useState<DeviceListRecord[]>([]);
  const [stations, setStations] = useState<StationRecord[]>([]);
  const [deviceId, setDeviceId] = useState<number | null>(null);
  const [doorConfig, setDoorConfig] = useState<DoorConfig | null>(null);
  const [doorError, setDoorError] = useState<string | null>(null);
  const [doorReload, setDoorReload] = useState(0);
  const [events, setEvents] = useState<AccessEventRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadDevices = useCallback(async () => {
    const [deviceRes, stationRes] = await Promise.all([listDevicesAction(), listStationsAction()]);
    if (!deviceRes.success) {
      setError(deviceRes.error);
      toast.error(deviceRes.error);
    } else {
      // Only controllers installed at a station have a door to manage.
      const installed = deviceRes.data.filter((d) => d.station_id !== null);
      setDevices(installed);
      setError(null);
      setDeviceId((current) =>
        installed.some((d) => d.id === current) ? current : installed[0]?.id ?? null
      );
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
    let current = true; // ignore late answers after switching controller
    void listAccessEventsAction({ device_id: deviceId, limit: 15 }).then((res) => {
      if (current && res.success) setEvents(res.data);
    });
    setDoorConfig(null);
    setDoorError(null);
    if (online) {
      void getDoorConfigAction(deviceId).then((res) => {
        if (!current) return;
        if (res.success) setDoorConfig(res.data);
        else setDoorError(res.error);
      });
    }
    return () => {
      current = false;
    };
  }, [deviceId, online, doorReload]);

  const station = stations.find((s) => s.id === device?.station_id);
  const stationLabel = (d: DeviceListRecord) =>
    stations.find((s) => s.id === d.station_id)?.name ?? `Station ${d.station_id}`;
  const alarms = doorConfig
    ? [
        doorConfig.door_not_closed_alarm_enable && "Left open",
        doorConfig.forced_entry_alarm_enable && "Forced entry",
        doorConfig.duress_alarm_enable && "Duress",
      ].filter(Boolean)
    : [];

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Door &amp; sensor</h2>
          <p className="text-xs text-muted-foreground">
            Lock, door contact and alarm settings on the station controller
          </p>
        </div>
        <div className="flex items-center gap-2">
          {devices.length > 1 ? (
            <Select value={String(deviceId)} onValueChange={(v) => v && setDeviceId(Number(v))}>
              <SelectTrigger size="sm" className="w-56 text-xs">
                <SelectValue placeholder="Choose door" />
              </SelectTrigger>
              <SelectContent alignItemWithTrigger={false}>
                {devices.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    {stationLabel(d)} · {d.host}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
          {device ? (
            <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium capitalize">
              <Led status={online ? "online" : device.status === "offline" ? "offline" : "pending"} />
              {online ? "Controller online" : `Controller ${device.status}`}
            </span>
          ) : null}
        </div>
      </div>

      {error ? (
        <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {!loading && !error && !device ? (
        <Panel title="No door controller installed">
          <p className="text-sm text-muted-foreground">
            Add a controller and assign it to a station from Add Device.
          </p>
        </Panel>
      ) : null}

      {device ? (
        <div className="grid gap-4 lg:grid-cols-3">
          {/* door summary + unlock */}
          <Panel
            title="Door"
            description={station ? `${station.name} · washroom door` : "Washroom door"}
            action={<DoorClosed aria-hidden className="size-4 text-muted-foreground" />}
          >
            {online && doorConfig ? (
              <dl>
                <Row label="Contact sensor" value={onOff(doorConfig.sensor_enabled)} />
                <Row label="Close check" value={onOff(doorConfig.close_check_sensor)} />
                <Row label="Unlock time" value={`${doorConfig.unlock_duration_seconds} s`} />
                <Row label="Open timeout" value={`${doorConfig.close_timeout} s`} />
                <Row
                  label="Alarms"
                  value={
                    alarms.length ? (
                      <span className="flex flex-wrap justify-end gap-1">
                        {alarms.map((a) => (
                          <ToneBadge key={String(a)} tone="amber">{a}</ToneBadge>
                        ))}
                      </span>
                    ) : (
                      <ToneBadge tone="grey">None</ToneBadge>
                    )
                  }
                />
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">
                {online ? "Door settings appear once the controller answers." : "Controller is offline."}
              </p>
            )}
            {online ? (
              <div className="mt-3">
                <RemoteUnlock deviceId={device.id} onDone={() => setDoorReload((n) => n + 1)} />
              </div>
            ) : null}
            <p className="mt-3 rounded-md bg-muted/60 p-2 text-xs text-muted-foreground">
              Live open/closed state is not reported yet; an accepted unlock is not proof the door opened.
            </p>
          </Panel>

          {/* sensor & alarm settings */}
          <Panel
            title="Sensor & alarm settings"
            description="Read from the controller; saving writes and reads back to confirm"
            className="lg:col-span-2"
          >
            {online && doorConfig ? (
              <DoorConfigForm key={device.id} config={doorConfig} onSaved={setDoorConfig} />
            ) : (
              <div className="flex flex-col items-start gap-2">
                <p className={doorError ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
                  {!online
                    ? "Connect the controller to read its door settings."
                    : doorError ?? "Reading door settings from the controller…"}
                </p>
                {online && doorError ? (
                  <Button size="sm" variant="outline" onClick={() => setDoorReload((n) => n + 1)}>
                    <RefreshCw aria-hidden />
                    Retry
                  </Button>
                ) : null}
              </div>
            )}
          </Panel>

          {/* door activity */}
          <Panel
            title="Door activity"
            description="Latest scans and remote unlocks at this door"
            className="lg:col-span-2"
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
              <p className="py-6 text-center text-sm text-muted-foreground">No activity at this door yet.</p>
            ) : null}
          </Panel>

          {/* controller */}
          <Panel
            title="Controller"
            description={device.model ?? "Access controller"}
            action={<ServerCog aria-hidden className="size-4 text-muted-foreground" />}
          >
            <dl>
              <Row label="Address" value={<span className="font-mono text-xs">{device.host}:{device.port}</span>} />
              <Row label="Serial" value={<span className="font-mono text-xs">{device.serial_number ?? "—"}</span>} />
              <Row label="Last reachable" value={when(device.last_tcp_reachable_at)} />
              <Row label="Card sync" value={<span className="capitalize">{device.inventory_status.replaceAll("_", " ")}</span>} />
            </dl>
            {device.last_error ? (
              <p className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
                {device.last_error}
              </p>
            ) : null}
            <div className="mt-3 flex flex-col gap-3">
              <DeviceActions deviceId={device.id} online={online} onDone={() => void loadDevices()} />
              {online ? (
                <CardSyncActions
                  deviceId={device.id}
                  inventoryStatus={device.inventory_status}
                  onDone={() => void loadDevices()}
                />
              ) : null}
            </div>
          </Panel>
        </div>
      ) : null}
    </div>
  );
}

export { DeviceDoorView };
