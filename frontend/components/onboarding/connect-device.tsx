"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Cpu, KeyRound, Loader2, ShieldCheck, User } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/auth/forms/password-input";
import { addDeviceAction } from "@/actions/add-device";
import type { DiscoveredDevice } from "@/actions/discover-devices";

// Step 4 — registers the initialized controller with the station
// (POST /devices) so the dashboard can monitor and manage it.
export function ConnectDevice({
  device,
  credentials,
  onBack,
}: {
  device: DiscoveredDevice;
  credentials: { username: string; password: string };
  onBack: () => void;
}) {
  const router = useRouter();
  const [form, setForm] = useState({
    name: device.model
      ? `${device.model} — ${device.ip_address}`
      : `Controller — ${device.ip_address}`,
    host: device.ip_address,
    port: String(device.tcp_port || 37777),
    username: credentials.username,
    password: credentials.password,
  });
  const [connectNow, setConnectNow] = useState(true);
  const [monitoringEnabled, setMonitoringEnabled] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  // Directly calls the Server Action: addDeviceAction(payload)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!form.name.trim()) {
      setError("Give this controller a name.");
      return;
    }
    if (!form.host.trim()) {
      setError("Host is required.");
      return;
    }
    const port = Number(form.port);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      setError("Port must be between 1 and 65535.");
      return;
    }
    if (!form.username.trim()) {
      setError("Username is required.");
      return;
    }
    if (!form.password) {
      setError("Password is required.");
      return;
    }

    setError(null);
    setLoading(true);
    const toastId = toast.loading("Registering the controller with your station...");

    try {
      const res = await addDeviceAction({
        name: form.name.trim(),
        connection_type: "ip_domain",
        host: form.host.trim(),
        port,
        username: form.username.trim(),
        password: form.password,
        model: device.model,
        serial_number: device.serial_number,
        mac_address: device.mac_address,
        connect_now: connectNow,
        monitoring_enabled: monitoringEnabled,
      });

      if (!res.success) {
        setError(res.error);
        toast.update(toastId, {
          render: res.error,
          type: "error",
          isLoading: false,
          autoClose: 6000,
        });
        return;
      }

      if (res.data.status === "online") {
        toast.update(toastId, {
          render: `${res.data.name} is registered and online.`,
          type: "success",
          isLoading: false,
          autoClose: 4000,
        });
      } else {
        toast.update(toastId, {
          render: `${res.data.name} is registered, but not connected yet${
            res.data.last_error ? `: ${res.data.last_error}` : "."
          }`,
          type: "warning",
          isLoading: false,
          autoClose: 7000,
        });
      }
      router.push("/overview");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to register the device";
      setError(msg);
      toast.update(toastId, {
        render: msg,
        type: "error",
        isLoading: false,
        autoClose: 6000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between pb-2 border-b border-border/60">
        <div>
          <h2 className="text-base font-semibold text-foreground">Connect Your Controller</h2>
          <p className="text-xs text-muted-foreground">
            Server Action: <code className="font-mono text-primary font-medium">POST /devices</code>
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={onBack}
          disabled={loading}
          className="h-8 gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </Button>
      </div>

      {/* Initialized device summary */}
      <div className="p-3.5 rounded-lg border border-primary/20 bg-primary/5 flex items-center justify-between">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-primary" />
            <span className="font-semibold text-xs text-foreground">
              {device.model || "Dahua controller"}
              {device.device_type ? ` (${device.device_type})` : ""}
            </span>
          </div>
          <div className="text-[11px] font-mono text-muted-foreground">
            IP: {device.ip_address} &bull; MAC: {device.mac_address}
            {device.serial_number ? ` • SN: ${device.serial_number}` : ""}
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 uppercase">
          Initialized
        </span>
      </div>

      {error && (
        <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs">
          {error}
        </div>
      )}

      {/* Connection form */}
      <form onSubmit={handleSubmit} className="space-y-3.5 pt-1">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-muted-foreground" />
            Device Name
          </label>
          <Input
            value={form.name}
            onChange={set("name")}
            placeholder="e.g. PumpStation 04 — Washroom controller"
            className="text-xs h-9 bg-background"
            disabled={loading}
            required
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-foreground">Host (IP)</label>
            <Input
              value={form.host}
              onChange={set("host")}
              placeholder="192.168.0.10"
              className="font-mono text-xs h-9 bg-background"
              disabled={loading}
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-foreground">Port</label>
            <Input
              type="number"
              min={1}
              max={65535}
              value={form.port}
              onChange={set("port")}
              placeholder="37777"
              className="font-mono text-xs h-9 bg-background"
              disabled={loading}
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-muted-foreground" />
              Username
            </label>
            <Input
              value={form.username}
              onChange={set("username")}
              placeholder="admin"
              className="text-xs h-9 bg-background"
              disabled={loading}
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-muted-foreground" />
              Password
            </label>
            <PasswordInput
              value={form.password}
              onChange={set("password")}
              placeholder="Controller password"
              disabled={loading}
              required
            />
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-1">
          <label className="flex items-center gap-2 text-xs text-foreground">
            <input
              type="checkbox"
              checked={connectNow}
              onChange={(e) => setConnectNow(e.target.checked)}
              className="size-3.5 accent-primary"
              disabled={loading}
            />
            Connect now — verify the controller login while registering
          </label>
          <label className="flex items-center gap-2 text-xs text-foreground">
            <input
              type="checkbox"
              checked={monitoringEnabled}
              onChange={(e) => setMonitoringEnabled(e.target.checked)}
              className="size-3.5 accent-primary"
              disabled={loading}
            />
            Enable health monitoring for this controller
          </label>
        </div>

        <div className="pt-2">
          <Button
            type="submit"
            disabled={loading}
            className="w-full h-10 text-xs font-semibold gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting controller...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Connect Controller & Open Dashboard
              </>
            )}
          </Button>
        </div>
      </form>
    </section>
  );
}
