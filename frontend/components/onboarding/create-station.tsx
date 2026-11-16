"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Building2, Loader2 } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { DeviceRecord } from "@/actions/add-device";
import {
  assignDeviceToStationAction,
  createStationAction,
  listStationsAction,
  type StationRecord,
} from "@/actions/stations";

type Props = {
  device: DeviceRecord;
  onBack: () => void;
  onCreated: (station: StationRecord) => void;
};

export function CreateStation({ device, onBack, onCreated }: Props) {
  const [stations, setStations] = useState<StationRecord[] | null>(null);
  const [form, setForm] = useState({
    station_code: `ST-${device.id}`,
    name: device.name,
    address: "",
    city: "",
  });
  const [saving, setSaving] = useState(false);
  const [pendingStation, setPendingStation] = useState<StationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listStationsAction().then((res) => {
      if (cancelled) return;
      if (res.success) {
        setStations(res.data);
      } else {
        setError(res.error);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const existing = device.station_id
    ? stations?.find((station) => station.id === device.station_id)
    : undefined;
  // Once the station exists, only the assignment retry may run; submitting the
  // form again would create a duplicate station.
  const locked = saving || pendingStation !== null;

  const assign = async (station: StationRecord) => {
    const res = await assignDeviceToStationAction(station.id, device.id);
    if (!res.success) {
      setPendingStation(station);
      setError(
        `Station created, but the controller could not be assigned: ${
          res.raw ?? res.error
        }`
      );
      toast.error(res.raw ?? res.error);
      return false;
    }
    toast.success(`${station.name} created and controller assigned.`);
    onCreated(station);
    return true;
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.station_code.trim() || !form.name.trim()) {
      setError("Station code and name are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await createStationAction({
        station_code: form.station_code.trim(),
        name: form.name.trim(),
        address: form.address.trim() || null,
        city: form.city.trim() || null,
        is_active: true,
      });
      if (!res.success) {
        setError(res.raw ?? res.error);
        toast.error(res.raw ?? res.error);
        return;
      }
      await assign(res.data);
    } finally {
      setSaving(false);
    }
  };

  if (!stations && !error) {
    return (
      <section className="flex items-center justify-center gap-2 rounded-xl border border-border/80 bg-card p-10 text-sm text-muted-foreground shadow-sm">
        <Loader2 aria-hidden className="size-4 animate-spin" />
        Loading stations…
      </section>
    );
  }

  if (existing) {
    return (
      <section className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-border/60 pb-2">
          <div>
            <h2 className="text-base font-semibold text-foreground">
              Controller already assigned
            </h2>
            <p className="text-xs text-muted-foreground">
              This controller belongs to a station. Continue to add the first
              user.
            </p>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={onBack}
            className="h-8 gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft aria-hidden className="size-3.5" />
            Back
          </Button>
        </div>

        <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3">
          <Building2 aria-hidden className="mt-0.5 size-5 text-primary" />
          <div>
            <p className="text-sm font-semibold">{existing.name}</p>
            <p className="font-mono text-[11px] text-muted-foreground">
              {existing.station_code}
              {existing.address ? ` · ${existing.address}` : ""}
            </p>
          </div>
        </div>

        <div className="flex justify-end">
          <Button size="sm" onClick={() => onCreated(existing)}>
            Continue to add user
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <div>
          <h2 className="text-base font-semibold text-foreground">
            Create the station
          </h2>
          <p className="text-xs text-muted-foreground">
            The connected controller is assigned to this station.
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={onBack}
          disabled={saving}
          className="h-8 gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft aria-hidden className="size-3.5" />
          Back
        </Button>
      </div>

      <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3">
        <Building2 aria-hidden className="mt-0.5 size-5 text-primary" />
        <div>
          <p className="text-sm font-semibold">{device.name}</p>
          <p className="font-mono text-[11px] text-muted-foreground">
            {device.host}:{device.port}
            {device.serial_number ? ` · ${device.serial_number}` : ""}
          </p>
        </div>
      </div>

      {error ? (
        <div className="space-y-2 rounded-lg border border-led-red/25 bg-led-red/10 p-3 text-xs text-led-red">
          <p>{error}</p>
          {pendingStation ? (
            <Button
              size="sm"
              variant="outline"
              disabled={saving}
              onClick={async () => {
                setSaving(true);
                try {
                  await assign(pendingStation);
                } finally {
                  setSaving(false);
                }
              }}
            >
              Retry controller assignment
            </Button>
          ) : null}
        </div>
      ) : null}

      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-xs font-semibold">Station code</span>
            <Input
              value={form.station_code}
              onChange={(event) =>
                setForm({ ...form, station_code: event.target.value })
              }
              placeholder="ST-04"
              className="h-9 font-mono text-xs"
              disabled={locked}
              required
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs font-semibold">Station name</span>
            <Input
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              placeholder="PumpStation 04"
              className="h-9 text-xs"
              disabled={locked}
              required
            />
          </label>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-xs font-semibold">Address</span>
            <Input
              value={form.address}
              onChange={(event) =>
                setForm({ ...form, address: event.target.value })
              }
              placeholder="Sheikh Zayed Road"
              className="h-9 text-xs"
              disabled={locked}
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs font-semibold">City</span>
            <Input
              value={form.city}
              onChange={(event) =>
                setForm({ ...form, city: event.target.value })
              }
              placeholder="Dubai"
              className="h-9 text-xs"
              disabled={locked}
            />
          </label>
        </div>

        <div className="flex justify-end pt-1">
          <Button
            type="submit"
            size="sm"
            disabled={locked || !form.station_code.trim() || !form.name.trim()}
          >
            {saving ? (
              <>
                <Loader2 aria-hidden className="animate-spin" />
                Creating station…
              </>
            ) : (
              "Create station & continue"
            )}
          </Button>
        </div>
      </form>
    </section>
  );
}
