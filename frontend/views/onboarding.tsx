"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Edit3,
  Globe,
  Loader2,
  Network,
  RefreshCw,
} from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DiscoverDevices } from "@/components/onboarding/discover-devices";
import { InitializeDeviceForm } from "@/components/onboarding/initialize-device-form";
import { ConnectDevice } from "@/components/onboarding/connect-device";
import { CreateStation } from "@/components/onboarding/create-station";
import { CreateStationUser } from "@/components/onboarding/create-station-user";
import { AssignCard } from "@/components/cards/assign-card";
import { getInterfacesAction, type InterfaceItem } from "@/actions/get-interfaces";
import type { DiscoveredDevice } from "@/actions/discover-devices";
import type { DeviceRecord } from "@/actions/add-device";
import type { StationRecord } from "@/actions/stations";
import type { StationUserRecord } from "@/actions/station-users";

const STEPS = [
  "Network",
  "Discover",
  "Initialize",
  "Connect",
  "Station",
  "User",
  "Card",
] as const;

function Stepper({
  current,
  skipped = [],
}: {
  current: number;
  skipped?: number[];
}) {
  return (
    <ol aria-label="Setup progress" className="flex items-center gap-3">
      {STEPS.map((label, i) => {
        const done = i < current || skipped.includes(i);
        const active = i === current;
        return (
          <li key={label} className="flex flex-1 items-center gap-2 last:flex-none">
            {i > 0 ? (
              <span
                aria-hidden
                className={`h-px flex-1 ${done || active ? "bg-primary/40" : "bg-border"}`}
              />
            ) : null}
            <span
              aria-current={active ? "step" : undefined}
              className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${done
                ? "bg-emerald-600 text-white"
                : active
                  ? "bg-primary text-primary-foreground"
                  : "border border-border text-muted-foreground"
                }`}
            >
              {done ? <Check aria-hidden className="size-3.5" /> : i + 1}
            </span>
            <span
              className={`hidden text-xs font-medium sm:block ${active ? "text-foreground font-semibold" : "text-muted-foreground"
                }`}
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function OnboardingView() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [skipped, setSkipped] = useState<number[]>([]);
  const [networkMode, setNetworkMode] = useState<"detected" | "manual">("detected");
  const [interfaces, setInterfaces] = useState<InterfaceItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIp, setSelectedIp] = useState<string>("");
  const [manualIp, setManualIp] = useState<string>("");

  const [selectedDevice, setSelectedDevice] = useState<DiscoveredDevice | null>(null);
  const [needsInit, setNeedsInit] = useState(true);
  const [initCredentials, setInitCredentials] = useState<{
    username: string;
    password: string;
  } | null>(null);
  const [connectedDevice, setConnectedDevice] = useState<DeviceRecord | null>(null);
  const [createdStation, setCreatedStation] = useState<StationRecord | null>(null);
  const [createdUser, setCreatedUser] = useState<StationUserRecord | null>(null);

  // Fetch GET /device-initialization/interfaces directly in the View via Server Action
  const fetchInterfaces = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getInterfacesAction();
      if (res.success) {
        setInterfaces(res.data);
        if (res.data.length > 0 && !selectedIp) {
          setSelectedIp(res.data[0].ip_address);
        }
      } else {
        setError(res.error);
        toast.error(res.error);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load interfaces";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInterfaces();
  }, []);

  // Effective IP to pass forward
  const activeIp = networkMode === "detected" ? selectedIp : manualIp.trim();

  const handleProceed = () => {
    if (!activeIp) {
      toast.error("Please select or enter a valid local IPv4 address");
      return;
    }
    const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if (!ipv4Regex.test(activeIp)) {
      toast.error("Please enter a valid IPv4 address (e.g. 192.168.0.10)");
      return;
    }

    setStep(1);
  };

  return (
    <div className="w-full max-w-xl space-y-7">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Dahua Controller Setup
        </h1>
        <p className="text-sm text-muted-foreground">
          Connect the controller, create its station, add the first station
          user, and assign a physical card.
        </p>
      </div>

      <Stepper current={step} skipped={skipped} />

      {/* STEP 1: Select the local network interface */}
      {step === 0 && (
        <section className="space-y-5 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-border/60">
            <div>
              <h2 className="text-base font-semibold text-foreground">Network adapter</h2>
              <p className="text-xs text-muted-foreground">
                Select the local adapter used to reach the Dahua controller.
              </p>
            </div>
            {networkMode === "detected" && (
              <Button
                size="sm"
                variant="outline"
                onClick={fetchInterfaces}
                disabled={loading}
                className="h-8 gap-1.5 text-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            )}
          </div>

          {/* 2 OPTIONS TAB SELECTOR */}
          <div className="grid grid-cols-2 gap-3 p-1 rounded-lg bg-muted/60 border border-border">
            <button
              type="button"
              onClick={() => setNetworkMode("detected")}
              className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${networkMode === "detected"
                ? "bg-background text-foreground shadow-xs ring-1 ring-border"
                : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <Network className="w-3.5 h-3.5 text-primary" />
              Option 1: Auto-Detected Interfaces
            </button>
            <button
              type="button"
              onClick={() => setNetworkMode("manual")}
              className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${networkMode === "manual"
                ? "bg-background text-foreground shadow-xs ring-1 ring-border"
                : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <Edit3 className="w-3.5 h-3.5 text-primary" />
              Option 2: Enter IP Manually
            </button>
          </div>

          {/* OPTION 1 CONTENT: Auto-Detected Interfaces */}
          {networkMode === "detected" && (
            <div className="space-y-3 pt-1">
              {loading && (
                <div className="flex flex-col items-center justify-center py-8 gap-2 text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <p className="text-xs font-medium">Querying local IPv4 interfaces from server...</p>
                </div>
              )}

              {error && !loading && (
                <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs flex flex-col gap-2">
                  <p className="font-semibold">{error}</p>
                  <Button size="sm" variant="secondary" onClick={fetchInterfaces} className="w-fit h-7 text-xs">
                    Retry Connection
                  </Button>
                </div>
              )}

              {!loading && !error && interfaces && interfaces.length === 0 && (
                <div className="py-6 text-center text-xs text-muted-foreground border border-dashed rounded-lg">
                  No active local IPv4 interfaces found. You can switch to Option 2 to enter your IP manually.
                </div>
              )}

              {!loading && !error && interfaces && interfaces.length > 0 && (
                <div role="radiogroup" aria-label="Available interfaces" className="space-y-2">
                  {interfaces.map((item) => {
                    const isChecked = selectedIp === item.ip_address;
                    return (
                      <button
                        key={item.ip_address}
                        type="button"
                        role="radio"
                        aria-checked={isChecked}
                        onClick={() => setSelectedIp(item.ip_address)}
                        className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-all ${isChecked
                          ? "border-primary bg-primary/5 ring-1 ring-primary shadow-xs"
                          : "border-border/70 hover:bg-muted/40 hover:border-border"
                          }`}
                      >
                        <div
                          className={`p-2 rounded-lg ${isChecked
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                            }`}
                        >
                          <Network className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className="font-mono text-sm font-semibold text-foreground block">
                            {item.ip_address}
                          </span>
                          <span className="text-[11px] text-muted-foreground">
                            Active Local Subnet Interface
                          </span>
                        </div>
                        <div
                          className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${isChecked
                            ? "border-primary bg-primary"
                            : "border-muted-foreground/40"
                            }`}
                        >
                          {isChecked && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* OPTION 2 CONTENT: Enter IP Manually */}
          {networkMode === "manual" && (
            <div className="space-y-3 pt-1">
              <div className="p-3.5 rounded-lg border border-border/80 bg-background space-y-2">
                <label className="text-xs font-semibold text-foreground block">
                  Specify Network Subnet IP (IPv4)
                </label>
                <div className="relative">
                  <Input
                    type="text"
                    value={manualIp}
                    onChange={(e) => setManualIp(e.target.value)}
                    placeholder="e.g. 192.168.0.10 or 192.168.1.100"
                    className="font-mono text-xs h-9 bg-card pl-9"
                  />
                  <Globe className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Enter the IPv4 address of the local network adapter connected to your Dahua controllers.
                </p>
              </div>

              {/* Quick Preset Buttons for easy selection */}
              <div className="flex items-center gap-2 flex-wrap text-xs">
                <span className="text-muted-foreground text-[11px]">Subnet suggestions:</span>
                {["192.168.0.10", "192.168.1.100", "192.168.100.164"].map((ip) => (
                  <button
                    key={ip}
                    type="button"
                    onClick={() => setManualIp(ip)}
                    className="px-2 py-0.5 rounded border border-border bg-muted/40 font-mono text-[11px] text-foreground hover:border-primary transition-colors"
                  >
                    {ip}
                  </button>
                ))}
              </div>
            </div>
          )}



          {/* Proceed Button */}
          <div className="pt-3 flex items-center justify-between border-t border-border/60">
            <span className="text-xs text-muted-foreground font-mono">
              Selected IP: <strong className="text-foreground">{activeIp || "None"}</strong>
            </span>
            <Button
              onClick={handleProceed}
              disabled={!activeIp}
              className="gap-2 text-xs h-9 px-4 font-semibold"
            >
              Proceed to Device Discovery
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </section>
      )}

      {/* STEP 2: Discover Devices Component (Calls POST /device-initialization/discover) */}
      {step === 1 && (
        <DiscoverDevices
          initialIp={activeIp}
          onSelected={(device) => {
            setSelectedDevice(device);
            setInitCredentials(null);
            // A controller that is already initialized only needs registering,
            // so skip the initialize step instead of hitting a guaranteed 409.
            const uninitialized = device.initialization_state
              .toLowerCase()
              .includes("uninit");
            setNeedsInit(uninitialized);
            setSkipped(uninitialized ? [] : [2]);
            setStep(uninitialized ? 2 : 3);
          }}
          onBack={() => setStep(0)}
        />
      )}

      {/* STEP 3: Initialize Device Component (Calls POST /device-initialization/initialize) */}
      {step === 2 && selectedDevice && (
        <InitializeDeviceForm
          device={selectedDevice}
          onBack={() => setStep(1)}
          onInitialized={(credentials) => {
            setInitCredentials(credentials);
            setStep(3);
          }}
        />
      )}

      {/* STEP 4: Connect Device Component (Calls POST /devices) */}
      {step === 3 && selectedDevice && (
        <ConnectDevice
          device={selectedDevice}
          credentials={initCredentials ?? undefined}
          onBack={() => setStep(needsInit ? 2 : 1)}
          onConnected={(record) => {
            setConnectedDevice(record);
            setStep(4);
          }}
        />
      )}

      {/* STEP 5: Create the station and assign the controller */}
      {step === 4 && connectedDevice && (
        <CreateStation
          device={connectedDevice}
          onBack={() => setStep(3)}
          onCreated={(station) => {
            setConnectedDevice((current) =>
              current ? { ...current, station_id: station.id } : current
            );
            setCreatedStation(station);
            setStep(5);
          }}
        />
      )}

      {/* STEP 6: Add the first station user */}
      {step === 5 && createdStation && (
        <CreateStationUser
          station={createdStation}
          onBack={() => setStep(4)}
          onCreated={(user) => {
            setCreatedUser(user);
            setStep(6);
          }}
        />
      )}

      {/* STEP 7: Assign a physical card to the station user */}
      {step === 6 && createdStation && createdUser && connectedDevice && (
        <section className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <div>
              <h2 className="text-base font-semibold text-foreground">
                Assign the first card
              </h2>
              <p className="text-xs text-muted-foreground">
                {createdUser.name} · {createdStation.name}
              </p>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setStep(5)}
              className="h-8 gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft aria-hidden className="size-3.5" />
              Back
            </Button>
          </div>

          <AssignCard
            stationId={createdStation.id}
            userId={createdUser.id}
            userName={createdUser.name}
            deviceId={connectedDevice.id}
            onDone={() => router.push("/overview")}
            onCancel={() => router.push("/overview")}
          />

          <div className="flex justify-end border-t border-border/60 pt-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/overview")}
              className="text-xs text-muted-foreground"
            >
              Skip card for now
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
