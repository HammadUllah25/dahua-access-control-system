"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Loader2, UserPlus } from "lucide-react";
import { toast } from "react-toastify";

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
  createStationUserAction,
  listStationRolesAction,
  type OperationalRoleRecord,
  type StationUserRecord,
} from "@/actions/station-users";
import type { StationRecord } from "@/actions/stations";

type Props = {
  station: StationRecord;
  onBack: () => void;
  onCreated: (user: StationUserRecord) => void;
};

export function CreateStationUser({ station, onBack, onCreated }: Props) {
  const [roles, setRoles] = useState<OperationalRoleRecord[] | null>(null);
  const [form, setForm] = useState({ name: "", phone: "", roleId: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listStationRolesAction(station.id).then((res) => {
      if (cancelled) return;
      if (!res.success) {
        setError(res.error);
        return;
      }
      setRoles(res.data);
      const preferred =
        res.data.find((role) => role.code === "CUSTOMER") ?? res.data[0];
      if (preferred) setForm((current) => ({ ...current, roleId: String(preferred.id) }));
    });
    return () => {
      cancelled = true;
    };
  }, [station.id]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.name.trim() || !form.roleId) {
      setError("Name and role are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await createStationUserAction(station.id, {
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        role_id: Number(form.roleId),
        is_billable: null,
      });
      if (!res.success) {
        setError(res.raw ?? res.error);
        toast.error(res.raw ?? res.error);
        return;
      }
      toast.success(`${res.data.name} added to ${station.name}.`);
      onCreated(res.data);
    } finally {
      setSaving(false);
    }
  };

  const selectedRole = roles?.find((role) => String(role.id) === form.roleId);

  return (
    <section className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <div>
          <h2 className="text-base font-semibold text-foreground">
            Add the first user
          </h2>
          <p className="text-xs text-muted-foreground">
            {station.name} · {station.station_code}
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
        <UserPlus aria-hidden className="mt-0.5 size-5 text-primary" />
        <div>
          <p className="text-sm font-semibold">Station user</p>
          <p className="text-xs text-muted-foreground">
            This is an operational person at the station, not a dashboard login.
          </p>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-led-red/25 bg-led-red/10 p-3 text-xs text-led-red">
          {error}
        </div>
      ) : null}

      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-xs font-semibold">Full name</span>
            <Input
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              placeholder="Ahmed Khan"
              className="h-9 text-xs"
              disabled={saving}
              required
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs font-semibold">Phone (optional)</span>
            <Input
              value={form.phone}
              onChange={(event) =>
                setForm({ ...form, phone: event.target.value })
              }
              placeholder="+92 300 1234567"
              className="h-9 text-xs"
              disabled={saving}
            />
          </label>
        </div>

        <label className="grid gap-1">
          <span className="text-xs font-semibold">Operational role</span>
          {roles === null && !error ? (
            <span className="flex h-9 items-center gap-2 text-xs text-muted-foreground">
              <Loader2 aria-hidden className="size-3.5 animate-spin" />
              Loading roles…
            </span>
          ) : (
            <Select
              value={form.roleId}
              onValueChange={(value) =>
                value && setForm({ ...form, roleId: value })
              }
              disabled={saving || !roles || roles.length === 0}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                {(roles ?? []).map((role) => (
                  <SelectItem key={role.id} value={String(role.id)}>
                    {role.name} ({role.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {selectedRole ? (
            <span className="text-[11px] text-muted-foreground">
              {selectedRole.description ?? "Station role"}
              {selectedRole.default_is_billable ? " · billable" : ""}
            </span>
          ) : null}
        </label>

        <div className="flex justify-end pt-1">
          <Button
            type="submit"
            size="sm"
            disabled={
              saving ||
              !form.name.trim() ||
              !form.roleId ||
              !roles ||
              roles.length === 0
            }
          >
            {saving ? (
              <>
                <Loader2 aria-hidden className="animate-spin" />
                Adding user…
              </>
            ) : (
              "Add user & continue"
            )}
          </Button>
        </div>
      </form>
    </section>
  );
}
