"use client";

import { useState } from "react";
import { DoorOpen } from "lucide-react";
import { toast } from "react-toastify";

import { remoteUnlockAction } from "@/actions/device-control";
import { Button } from "@/components/ui/button";

// Sends POST /devices/{id}/remote-unlock. Two clicks: arm, then confirm.
function RemoteUnlock({
  deviceId,
  doorIndex = 0,
  onDone,
}: {
  deviceId: number;
  doorIndex?: number;
  onDone?: () => void;
}) {
  const [armed, setArmed] = useState(false);
  const [busy, setBusy] = useState(false);

  const unlock = async () => {
    setBusy(true);
    const res = await remoteUnlockAction(deviceId, {
      door_index: doorIndex,
      operator_id: "DASHBOARD",
      reason: "MANUAL",
    });
    setBusy(false);
    setArmed(false);
    if (!res.success) {
      toast.error(res.raw ?? res.error);
      return;
    }
    // The controller accepted the command; the door contact is not verified.
    toast.success("Unlock command accepted by the controller.");
    onDone?.();
  };

  return (
    <div className="flex flex-col gap-2">
      <Button
        size="sm"
        variant={armed ? "destructive" : "outline"}
        disabled={busy}
        onClick={() => (armed ? void unlock() : setArmed(true))}
      >
        <DoorOpen aria-hidden />
        {busy ? "Sending…" : armed ? "Confirm remote unlock" : "Remote unlock door"}
      </Button>
      {armed && !busy ? (
        <Button size="sm" variant="ghost" onClick={() => setArmed(false)}>
          Cancel
        </Button>
      ) : null}
    </div>
  );
}

export { RemoteUnlock };
