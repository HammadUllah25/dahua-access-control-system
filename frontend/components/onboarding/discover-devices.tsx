"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Clock, Cpu, Loader2, Search } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  discoverDevicesAction,
  type DiscoveredDevice,
} from "@/actions/discover-devices";

export function DiscoverDevices({
  initialIp,
  onSelected,
  onBack,
}: {
  initialIp: string;
  onSelected: (device: DiscoveredDevice) => void;
  onBack: () => void;
}) {
  const [localIp, setLocalIp] = useState(initialIp || "192.168.0.10");
  const [waitSeconds, setWaitSeconds] = useState<number>(5);
  // starts in scanning state when the view auto-launches discovery on mount
  const [loading, setLoading] = useState(Boolean(initialIp));
  const [devices, setDevices] = useState<DiscoveredDevice[]>([]);
  const [hasScanned, setHasScanned] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Async core — no setState before the first await, so it is safe to call
  // from an effect. Directly calls the Server Action:
  // discoverDevicesAction({ local_ip, wait_seconds })
  const runDiscovery = async () => {
    const toastId = toast.loading(`Scanning network on ${localIp} for ${waitSeconds}s...`);

    try {
      const res = await discoverDevicesAction({
        local_ip: localIp.trim(),
        wait_seconds: Math.min(Math.max(Number(waitSeconds) || 5, 2), 15),
      });

      if (res.success) {
        setDevices(res.data.devices);
        setHasScanned(true);
        toast.update(toastId, {
          render: `Found ${res.data.count} controller(s) on ${localIp}`,
          type: "success",
          isLoading: false,
          autoClose: 3000,
        });
      } else {
        setError(res.error);
        toast.update(toastId, {
          render: res.error,
          type: "error",
          isLoading: false,
          autoClose: 5000,
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run device discovery";
      setError(msg);
      toast.update(toastId, {
        render: msg,
        type: "error",
        isLoading: false,
        autoClose: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDiscover = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!localIp.trim()) {
      toast.error("Please enter a valid local IPv4 address");
      return;
    }

    setLoading(true);
    setError(null);
    await runDiscovery();
  };

  // Run automatically once on mount with the IP passed from the view
  const autoRan = useRef(false);
  useEffect(() => {
    if (!initialIp || autoRan.current) return;
    autoRan.current = true;
    void runDiscovery();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between pb-2 border-b border-border/60">
        <div>
          <h2 className="text-base font-semibold text-foreground">Discover Uninitialized Devices</h2>
          <p className="text-xs text-muted-foreground">
            Server Action: <code className="font-mono text-primary font-medium">POST /device-initialization/discover</code>
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={onBack}
          className="h-8 gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </Button>
      </div>

      {/* Manual Input Controls for local_ip and wait_seconds */}
      <form onSubmit={handleDiscover} className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-1">
        <div className="sm:col-span-7 space-y-1">
          <label className="text-xs font-semibold text-foreground">
            Local Discovery IP (IPv4)
          </label>
          <Input
            value={localIp}
            onChange={(e) => setLocalIp(e.target.value)}
            placeholder="e.g. 192.168.0.10"
            className="font-mono text-xs h-9 bg-background"
            disabled={loading}
          />
        </div>

        <div className="sm:col-span-3 space-y-1">
          <label className="text-xs font-semibold text-foreground">
            Wait (Seconds)
          </label>
          <div className="relative">
            <Input
              type="number"
              min={2}
              max={15}
              value={waitSeconds}
              onChange={(e) =>
                setWaitSeconds(Math.min(Math.max(parseInt(e.target.value) || 5, 2), 15))
              }
              className="font-mono text-xs h-9 bg-background pr-7"
              disabled={loading}
            />
            <Clock className="w-3.5 h-3.5 text-muted-foreground absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>

        <div className="sm:col-span-2 flex items-end">
          <Button
            type="submit"
            disabled={loading || !localIp.trim()}
            className="w-full h-9 text-xs gap-1.5 font-semibold"
          >
            {loading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Search className="w-3.5 h-3.5" />
            )}
            Scan
          </Button>
        </div>
      </form>

      {/* Loading state indicator */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-10 gap-3 border border-dashed rounded-lg bg-muted/20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <div className="text-center">
            <p className="text-sm font-semibold text-foreground">Scanning Local Broadcast Network...</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Listening for Dahua beacon frames on <span className="font-mono text-foreground">{localIp}</span> ({waitSeconds}s)
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs">
          <span className="font-semibold block mb-1">Discovery Failed</span>
          <p>{error}</p>
        </div>
      )}

      {/* Results List */}
      {!loading && hasScanned && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Found {devices.length} controller(s)</span>
            <span>Click device to initialize</span>
          </div>

          {devices.length === 0 ? (
            <div className="p-6 text-center border border-dashed rounded-lg bg-muted/10 space-y-1">
              <Cpu className="w-7 h-7 mx-auto text-muted-foreground/60" />
              <p className="text-xs font-medium text-foreground">No uninitialized devices found</p>
              <p className="text-[11px] text-muted-foreground">
                Verify the Dahua controller is connected to the same LAN subnet and powered on.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {devices.map((device) => {
                const isUninit = device.initialization_state.toLowerCase().includes("uninit");
                return (
                  <button
                    key={device.mac_address}
                    type="button"
                    onClick={() => onSelected(device)}
                    className="w-full text-left p-3.5 rounded-lg border border-border/80 bg-background hover:bg-muted/40 hover:border-primary transition-all flex items-center justify-between group shadow-2xs"
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-foreground">
                          {device.model || "Dahua controller"}
                          {device.device_type ? ` (${device.device_type})` : ""}
                        </span>
                        <Badge
                          variant={isUninit ? "destructive" : "secondary"}
                          className="text-[10px] px-1.5 py-0 uppercase"
                        >
                          {device.initialization_state}
                        </Badge>
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs text-muted-foreground font-mono">
                        <span>IP: <strong className="text-foreground">{device.ip_address}</strong></span>
                        <span>MAC: <strong>{device.mac_address}</strong></span>
                        <span>TCP: <strong>{device.tcp_port}</strong></span>
                      </div>

                      <div className="text-[11px] text-muted-foreground font-mono">
                        SN: {device.serial_number || "—"} &bull; Subnet: {device.subnet_mask || "—"}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 text-primary text-xs font-semibold group-hover:translate-x-1 transition-transform pl-3">
                      <span>Setup</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
