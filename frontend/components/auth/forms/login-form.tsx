"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/auth/forms/password-input";

// shortcut: mock sign-in — replace with the real session endpoint
function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const notice = params.get("reset")
    ? "Password updated — sign in with your new password."
    : null;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@") || password.length < 6) {
      setError("Enter a valid email and a password of at least 6 characters.");
      return;
    }
    setError(null);
    setLoading(true);
    setTimeout(() => router.push("/overview"), 700);
  };

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
        <p className="text-sm text-muted-foreground">
          Sign in to the station admin console.
        </p>
      </div>

      {notice ? (
        <p className="flex items-start gap-2 rounded-lg border border-led-green/25 bg-led-green/10 px-3 py-2 text-xs font-medium text-led-green">
          <CheckCircle2 aria-hidden className="mt-0.5 size-3.5 shrink-0" />
          {notice}
        </p>
      ) : null}

      <form onSubmit={submit} className="space-y-4" noValidate>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Email</span>
          <Input
            type="email"
            autoComplete="email"
            placeholder="admin@fuelco.example"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Password</span>
          <PasswordInput
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <div className="flex items-center justify-between text-xs">
          <label className="inline-flex cursor-pointer items-center gap-2 text-muted-foreground">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="size-3.5 accent-[var(--primary)]"
            />
            Keep me signed in
          </label>
          <Link href="/forgot-password" className="font-medium text-primary hover:underline">
            Forgot password?
          </Link>
        </div>

        {error ? (
          <p role="alert" className="text-xs font-medium text-destructive">
            {error}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? (
            <Loader2 aria-hidden className="motion-safe:animate-spin" />
          ) : null}
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="text-xs text-muted-foreground">
        Demo build — any valid-looking credentials sign in.
      </p>
      <p className="text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="font-medium text-primary hover:underline">
          Create one
        </Link>
      </p>
    </div>
  );
}

export { LoginForm };
