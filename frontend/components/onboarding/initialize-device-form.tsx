"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, KeyRound, Loader2, ShieldCheck, User } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/auth/forms/password-input";
import {
  initializeDeviceAction,
} from "@/actions/initialize-device";
import type { DiscoveredDevice } from "@/actions/discover-devices";

export function InitializeDeviceForm({
  device,
  onBack,
}: {
  device: DiscoveredDevice;
  onBack: () => void;
}) {
  const router = useRouter();
  const [form, setForm] = useState({
    username: "admin",
    password: "",
    confirm: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  // Directly calls the Server Action: initializeDeviceAction(payload)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (form.username.trim().length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters (Dahua security standard).");
      return;
    }
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }

    setError(null);
    setLoading(true);

    // Toast loading state
    const toastId = toast.loading("Configuring controller and creating admin account...");

    try {
      const res = await initializeDeviceAction({
        mac_address: device.mac_address,
        local_ip: device.local_ip || device.ip_address,
        username: form.username.trim(),
        password: form.password,
        confirm_password: form.confirm,
      });

      if (res.success) {
        toast.update(toastId, {
          render: res.data.message || "Device initialized successfully.",
          type: "success",
          isLoading: false,
          autoClose: 4000,
        });
        // Immediately redirect to dashboard
        router.push("/overview");
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
      const msg = err instanceof Error ? err.message : "Failed to initialize device";
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

  return (
    <section className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between pb-2 border-b border-border/60">
        <div>
          <h2 className="text-base font-semibold text-foreground">Initialize Controller Account</h2>
          <p className="text-xs text-muted-foreground">
            Server Action: <code className="font-mono text-primary font-medium">POST /device-initialization/initialize</code>
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

      {/* Target Device Summary Header */}
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
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-primary/10 text-primary uppercase">
          Ready to Init
        </span>
      </div>

      {error && (
        <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs">
          {error}
        </div>
      )}

      {/* Credentials form */}
      <form onSubmit={handleSubmit} className="space-y-3.5 pt-1">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-muted-foreground" />
            Admin Username
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-muted-foreground" />
              Password
            </label>
            <PasswordInput
              value={form.password}
              onChange={set("password")}
              placeholder="Min. 8 characters"
              disabled={loading}
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-muted-foreground" />
              Confirm Password
            </label>
            <PasswordInput
              value={form.confirm}
              onChange={set("confirm")}
              placeholder="Re-enter password"
              disabled={loading}
              required
            />
          </div>
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
                Initializing Dahua Controller...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Initialize Controller & Open Dashboard
              </>
            )}
          </Button>
        </div>
      </form>
    </section>
  );
}
