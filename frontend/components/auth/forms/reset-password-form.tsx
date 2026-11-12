"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/auth/forms/password-input";

// shortcut: mock reset — password writes land with the backend
function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const email = params.get("email");

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setLoading(true);
    setTimeout(() => router.push("/login?reset=1"), 700);
  };

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Set a new password</h1>
        <p className="text-sm text-muted-foreground">
          {email ? (
            <>
              Resetting the password for{" "}
              <span className="font-medium text-foreground">{email}</span>.
            </>
          ) : (
            "Choose a new password for your admin account."
          )}
        </p>
      </div>

      <form onSubmit={submit} className="space-y-4" noValidate>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">New password</span>
          <PasswordInput
            autoComplete="new-password"
            placeholder="At least 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Confirm new password</span>
          <PasswordInput
            autoComplete="new-password"
            placeholder="Repeat your password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </label>

        {error ? (
          <p role="alert" className="text-xs font-medium text-destructive">
            {error}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? (
            <Loader2 aria-hidden className="motion-safe:animate-spin" />
          ) : null}
          {loading ? "Updating…" : "Update password"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Code expired or wrong email?{" "}
        <Link href="/forgot-password" className="font-medium text-primary hover:underline">
          Start over
        </Link>
      </p>
    </div>
  );
}

export { ResetPasswordForm };
