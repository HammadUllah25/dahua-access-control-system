"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  CircleCheck,
  Cpu,
  Loader2,
  Plus,
  XCircle,
} from "lucide-react";
import { toast } from "react-toastify";

import { Panel } from "@/components/dashboard/panel";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { ToneBadge } from "@/components/dashboard/badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { useSession } from "@/components/role-provider";
import { ROLE_META } from "@/lib/roles";
import {
  listDevicesAction,
  type DeviceListRecord,
} from "@/actions/get-devices";
import {
  assignDeviceToStationAction,
  createStationAction,
  listStationsAction,
  type StationRecord,
} from "@/actions/stations";

type StationStatus = "online" | "offline" | "pending" | "none";

const STATUS_TONE = {
  online: "green",
  offline: "red",
  pending: "amber",
  none: "grey",
} as const;

const STATUS_LABEL = {
  online: "Online",
  offline: "Offline",
  pending: "Pending",
  none: "No controller",
} as const;

function formatWhen(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function stationStatus(devices: DeviceListRecord[]): StationStatus {
  if (devices.some((device) => device.status === "online")) return "online";
  if (devices.some((device) => device.status === "pending")) return "pending";
  return devices.length > 0 ? "offline" : "none";
}

function lastSeen(devices: DeviceListRecord[]) {
  const values = devices
    .map(
      (device) =>
        device.last_connected_at ??
        device.last_tcp_reachable_at ??
        device.last_health_check_at ??
        device.updated_at
    )
    .filter(Boolean)
    .sort();
  return values.length > 0 ? values[values.length - 1] : null;
}

const EMPTY_FORM = { station_code: "", name: "", address: "", city: "" };

function StationsView() {
  const { role } = useSession();
  const meta = ROLE_META[role];
  const [stations, setStations] = useState<StationRecord[]>([]);
  const [devices, setDevices] = useState<DeviceListRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [deviceId, setDeviceId] = useState("");
  const [pendingStation, setPendingStation] = useState<StationRecord | null>(
    null
  );

  const load = useCallback(async () => {
    setLoading(true);
    const [stationRes, deviceRes] = await Promise.all([
      listStationsAction(),
      listDevicesAction(),
    ]);
    if (!stationRes.success || !deviceRes.success) {
      const message =
        (!stationRes.success ? stationRes.error : "") ||
        (!deviceRes.success ? deviceRes.error : "") ||
        "Could not load stations.";
      setError(message);
      toast.error(message);
    } else {
      setStations(stationRes.data);
      setDevices(deviceRes.data);
      setError(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const unassignedDevices = devices.filter(
    (device) => device.station_id === null
  );
  const canAddStation = unassignedDevices.length > 0;
  const online = devices.filter((device) => device.status === "online").length;
  const offline = devices.filter((device) => device.status === "offline").length;
  const pending = devices.filter((device) => device.status === "pending").length;

  const openAdd = () => {
    setForm({
      ...EMPTY_FORM,
      station_code: `ST-${String(stations.length + 1).padStart(2, "0")}`,
    });
    setDeviceId(
      unassignedDevices[0] ? String(unassignedDevices[0].id) : ""
    );
    setPendingStation(null);
    setAddOpen(true);
  };

  const retryAssign = async () => {
    if (!pendingStation || !deviceId) return;
    setSaving(true);
    try {
      const assigned = await assignDeviceToStationAction(
        pendingStation.id,
        Number(deviceId)
      );
      if (!assigned.success) {
        toast.error(assigned.raw ?? assigned.error);
        return;
      }
      toast.success(`${pendingStation.name} created and controller assigned.`);
      setPendingStation(null);
      setAddOpen(false);
      setForm(EMPTY_FORM);
      await load();
    } finally {
      setSaving(false);
    }
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.station_code.trim() || !form.name.trim() || !deviceId) {
      toast.error("Station code, name and controller are required.");
      return;
    }
    setSaving(true);
    try {
      const created = await createStationAction({
        station_code: form.station_code.trim(),
        name: form.name.trim(),
        address: form.address.trim() || null,
        city: form.city.trim() || null,
        is_active: true,
      });
      if (!created.success) {
        toast.error(created.raw ?? created.error);
        return;
      }

      const assigned = await assignDeviceToStationAction(
        created.data.id,
        Number(deviceId)
      );
      if (!assigned.success) {
        setPendingStation(created.data);
        toast.error(
          `Station created, but controller assignment failed: ${
            assigned.raw ?? assigned.error
          }`
        );
        await load();
        return;
      }

      toast.success(`${created.data.name} created and controller assigned.`);
      setPendingStation(null);
      setAddOpen(false);
      setForm(EMPTY_FORM);
      await load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Stations</h2>
          <p className="text-xs text-muted-foreground">
            {meta.label} view · registered stations and their controllers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{meta.label}</Badge>
          <Button
            size="sm"
            onClick={openAdd}
            disabled={!canAddStation}
            title={
              canAddStation
                ? "Create a station and assign a controller"
                : "Connect a controller before creating a station"
            }
            className="disabled:cursor-not-allowed disabled:pointer-events-auto"
          >
            <Plus aria-hidden />
            Add station
          </Button>
        </div>
      </div>

      {!loading && !canAddStation ? (
        <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
          {devices.length === 0 ? (
            role === "branch" ? (
              <>Add station is locked until an Admin connects a controller.</>
            ) : (
              <>
                Add station is locked until a controller is connected.{" "}
                <Link href="/add-device" className="font-medium text-primary hover:underline">
                  Connect a controller first
                </Link>
                .
              </>
            )
          ) : (
            "Every controller is already assigned. Connect another controller before creating a station."
          )}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-led-red/25 bg-led-red/10 p-3 text-xs text-led-red">
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Stations"
          value={stations.length}
          hint="Registered in the backend"
          icon={Building2}
          tone="violet"
        />
        <KpiCard
          label="Online controllers"
          value={online}
          hint="Reachable now"
          icon={CircleCheck}
          tone="green"
        />
        <KpiCard
          label="Offline controllers"
          value={offline}
          hint="Needs attention"
          icon={XCircle}
          tone="red"
        />
        <KpiCard
          label="Pending controllers"
          value={pending}
          hint="Not connected yet"
          icon={Cpu}
          tone="amber"
        />
      </div>

      <Panel
        title="Station monitoring"
        description="Every station in the backend · controller health and last contact"
        action={
          loading ? (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 aria-hidden className="size-3.5 animate-spin" />
              Loading
            </span>
          ) : undefined
        }
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Station</TableHead>
              <TableHead>City</TableHead>
              <TableHead>Controllers</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last seen</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stations.map((station) => {
              const stationDevices = devices.filter(
                (device) => device.station_id === station.id
              );
              const status = stationStatus(stationDevices);
              return (
                <TableRow key={station.id}>
                  <TableCell className="font-medium">
                    {station.name}
                    <span className="block font-mono text-[11px] text-muted-foreground">
                      {station.station_code}
                    </span>
                  </TableCell>
                  <TableCell>{station.city ?? "—"}</TableCell>
                  <TableCell className="tabular-nums">
                    {stationDevices.length}
                    {stationDevices[0] ? (
                      <span className="block font-mono text-[11px] text-muted-foreground">
                        {stationDevices[0].host}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <ToneBadge tone={STATUS_TONE[status]}>
                      {STATUS_LABEL[status]}
                    </ToneBadge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatWhen(lastSeen(stationDevices))}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {!loading && stations.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No stations yet. Connect a controller, then create the first station.
          </p>
        ) : null}
      </Panel>

      <Dialog
        open={addOpen}
        onOpenChange={(open) => {
          if (!open) {
            setPendingStation(null);
            setForm(EMPTY_FORM);
          }
          setAddOpen(open);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create station</DialogTitle>
            <DialogDescription>
              The selected controller is assigned to this station so people and
              cards can be managed against it.
            </DialogDescription>
          </DialogHeader>
          {pendingStation ? (
            <div className="space-y-3">
              <p className="rounded-lg border border-led-amber/25 bg-led-amber/10 p-3 text-xs text-led-amber">
                {pendingStation.name} was created, but the controller could not
                be assigned. Retry to attach it.
              </p>
              <DialogFooter>
                <Button
                  size="sm"
                  onClick={retryAssign}
                  disabled={saving || !deviceId}
                >
                  {saving ? (
                    <>
                      <Loader2 aria-hidden className="animate-spin" />
                      Assigning…
                    </>
                  ) : (
                    "Retry assignment"
                  )}
                </Button>
              </DialogFooter>
            </div>
          ) : (
          <form onSubmit={save} className="grid gap-3">
            <div className="grid grid-cols-2 gap-2">
              <label className="grid gap-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Station code
                </span>
                <Input
                  value={form.station_code}
                  onChange={(event) =>
                    setForm({ ...form, station_code: event.target.value })
                  }
                  placeholder="ST-04"
                  className="h-8 font-mono text-xs"
                  disabled={saving}
                  required
                />
              </label>
              <label className="grid gap-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Station name
                </span>
                <Input
                  value={form.name}
                  onChange={(event) =>
                    setForm({ ...form, name: event.target.value })
                  }
                  placeholder="PumpStation 04"
                  className="h-8 text-xs"
                  disabled={saving}
                  required
                />
              </label>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <label className="grid gap-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Address
                </span>
                <Input
                  value={form.address}
                  onChange={(event) =>
                    setForm({ ...form, address: event.target.value })
                  }
                  placeholder="Sheikh Zayed Road"
                  className="h-8 text-xs"
                  disabled={saving}
                />
              </label>
              <label className="grid gap-1">
                <span className="text-xs font-medium text-muted-foreground">
                  City
                </span>
                <Input
                  value={form.city}
                  onChange={(event) =>
                    setForm({ ...form, city: event.target.value })
                  }
                  placeholder="Dubai"
                  className="h-8 text-xs"
                  disabled={saving}
                />
              </label>
            </div>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">
                Controller
              </span>
              <Select
                value={deviceId}
                onValueChange={(value) => value && setDeviceId(value)}
                disabled={saving || unassignedDevices.length === 0}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a controller" />
                </SelectTrigger>
                <SelectContent>
                  {unassignedDevices.map((device) => (
                    <SelectItem key={device.id} value={String(device.id)}>
                      {device.name} · {device.host} ({device.status})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <DialogFooter>
              <Button
                type="submit"
                size="sm"
                disabled={
                  saving ||
                  !form.station_code.trim() ||
                  !form.name.trim() ||
                  !deviceId
                }
              >
                {saving ? (
                  <>
                    <Loader2 aria-hidden className="animate-spin" />
                    Creating…
                  </>
                ) : (
                  "Create & assign"
                )}
              </Button>
            </DialogFooter>
          </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export { StationsView };
