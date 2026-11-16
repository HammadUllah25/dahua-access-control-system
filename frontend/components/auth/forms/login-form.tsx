"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/auth/forms/password-input";
import { findAccountByEmail } from "@/lib/accounts";
import {
  ROLE_META,
  defaultUser,
  roleFromPassword,
  setRoleCookie,
  setUserCookie,
  type Role,
} from "@/lib/roles";

// shortcut: mock sign-in — the password text selects the demo role
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
  const [accountRole, setAccountRole] = useState<Role | null>(null);

  // Read the managed account list after hydration; SSR has no localStorage.
  useEffect(() => {
    if (!email.includes("@")) {
      setAccountRole(null);
      return;
    }
    setAccountRole(findAccountByEmail(email)?.role ?? null);
  }, [email]);

  const detectedRole =
    accountRole ??
    (password.trim().length >= 5 ? roleFromPassword(password) : null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@") || password.trim().length < 5) {
      setError("Enter a valid email and a password of at least 5 characters.");
      return;
    }
    const account = findAccountByEmail(email);
    if (account && account.password !== password) {
      setError("Incorrect password for this account.");
      return;
    }
    setError(null);
    if (account) {
      setRoleCookie(account.role);
      setUserCookie({ name: account.name, email: account.email });
    } else {
      const role = roleFromPassword(password);
      setRoleCookie(role);
      setUserCookie(defaultUser(role, email.trim()));
    }
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

        {detectedRole ? (
          <p className="text-xs text-muted-foreground">
            Signing in as{" "}
            <span className="font-medium text-foreground">
              {ROLE_META[detectedRole].label}
            </span>
          </p>
        ) : null}

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
        Demo roles — password <span className="font-mono">super admin</span>,{" "}
        <span className="font-mono">admin</span> or{" "}
        <span className="font-mono">branch</span>. Accounts created by the Super
        Admin sign in with their own email and password.
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
