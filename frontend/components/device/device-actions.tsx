"use client";

import { useState } from "react";
import { Activity, Plug, Unplug } from "lucide-react";
import { toast } from "react-toastify";

import {
  connectDeviceAction,
  deviceHealthCheckAction,
  disconnectDeviceAction,
} from "@/actions/device-control";
import { Button } from "@/components/ui/button";

const COMMANDS = {
  health: { label: "Run health check", icon: Activity, run: deviceHealthCheckAction, done: "Health check finished." },
  connect: { label: "Reconnect", icon: Plug, run: connectDeviceAction, done: "Controller connected." },
  disconnect: { label: "Disconnect", icon: Unplug, run: disconnectDeviceAction, done: "Controller disconnected; monitoring paused." },
} as const;

// Controller commands: POST /devices/{id}/health-check | connect | disconnect.
function DeviceActions({
  deviceId,
  online,
  onDone,
}: {
  deviceId: number;
  online: boolean;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState<keyof typeof COMMANDS | null>(null);

  const run = async (key: keyof typeof COMMANDS) => {
    setBusy(key);
    const res = await COMMANDS[key].run(deviceId);
    setBusy(null);
    if (!res.success) {
      toast.error(res.raw ?? res.error);
    } else {
      toast.success(COMMANDS[key].done);
    }
    onDone();
  };

  const keys: (keyof typeof COMMANDS)[] = online ? ["health", "disconnect"] : ["health", "connect"];
  return (
    <div className="flex flex-wrap gap-2">
      {keys.map((key) => {
        const { label, icon: Icon } = COMMANDS[key];
        return (
          <Button
            key={key}
            size="sm"
            variant="outline"
            disabled={busy !== null}
            onClick={() => void run(key)}
          >
            <Icon aria-hidden />
            {busy === key ? "Working…" : label}
          </Button>
        );
      })}
    </div>
  );
}

export { DeviceActions };
