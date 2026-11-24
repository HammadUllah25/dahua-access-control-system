"use client";

import { useState } from "react";
import { toast } from "react-toastify";

import {
  updateDoorConfigAction,
  type DoorConfig,
} from "@/actions/device-control";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const TOGGLES = [
  ["sensor_enabled", "Door contact sensor enabled"],
  ["door_not_closed_alarm_enable", "Alarm when door left open"],
  ["forced_entry_alarm_enable", "Alarm on forced entry"],
] as const;

// Edits the door sensor settings and writes them with PUT /devices/{id}/door-config.
// The view loads the config (GET) and passes it in; the backend reads it back after writing.
function DoorConfigForm({
  config,
  onSaved,
}: {
  config: DoorConfig;
  onSaved: (config: DoorConfig) => void;
}) {
  const [draft, setDraft] = useState(config);
  const [saving, setSaving] = useState(false);
  const changed = (Object.keys(draft) as (keyof DoorConfig)[]).some((k) => draft[k] !== config[k]);

  const save = async () => {
    setSaving(true);
    const res = await updateDoorConfigAction(config.device_id, {
      door_index: config.door_index,
      sensor_enabled: draft.sensor_enabled,
      close_timeout: draft.close_timeout,
      door_not_closed_alarm_enable: draft.door_not_closed_alarm_enable,
      forced_entry_alarm_enable: draft.forced_entry_alarm_enable,
      unlock_duration_seconds: draft.unlock_duration_seconds,
    });
    setSaving(false);
    if (!res.success) {
      toast.error(res.raw ?? res.error);
      return;
    }
    toast.success(res.data.message);
    onSaved(res.data);
    setDraft(res.data);
  };

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      {TOGGLES.map(([key, label]) => (
        <label key={key} className="flex items-center justify-between gap-4 text-sm">
          {label}
          <input
            type="checkbox"
            checked={draft[key]}
            onChange={(event) => setDraft({ ...draft, [key]: event.target.checked })}
            disabled={saving}
            className="size-4 accent-[var(--primary)]"
          />
        </label>
      ))}
      <div className="grid grid-cols-2 gap-3">
        <label className="grid gap-1">
          <span className="text-xs font-medium text-muted-foreground">Door-open alarm after (s)</span>
          <Input
            type="number"
            min={0}
            value={draft.close_timeout}
            onChange={(event) => setDraft({ ...draft, close_timeout: Number(event.target.value) })}
            className="h-8 text-xs"
            disabled={saving}
            required
          />
        </label>
        <label className="grid gap-1">
          <span className="text-xs font-medium text-muted-foreground">Unlock duration (s)</span>
          <Input
            type="number"
            min={0.2}
            max={600}
            step={0.1}
            value={draft.unlock_duration_seconds}
            onChange={(event) =>
              setDraft({ ...draft, unlock_duration_seconds: Number(event.target.value) })
            }
            className="h-8 text-xs"
            disabled={saving}
            required
          />
        </label>
      </div>
      <Button type="submit" size="sm" disabled={!changed || saving} className="self-start">
        {saving ? "Writing to controller…" : "Save to controller"}
      </Button>
    </form>
  );
}

export { DoorConfigForm };
