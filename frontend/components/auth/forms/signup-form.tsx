"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/auth/forms/password-input";

// shortcut: mock registration — the account + OTP email land with the backend
function SignupForm() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.name.trim().length < 2) {
      setError("Enter your full name.");
      return;
    }
    if (!form.email.includes("@")) {
      setError("Enter a valid email address.");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setLoading(true);
    setTimeout(() => {
      // Redirect directly to device onboarding after signup
      router.push("/onboarding");
    }, 700);
  };

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Create your account</h1>
        <p className="text-sm text-muted-foreground">
          Station admin access for the washroom console.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-4" noValidate>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Full name</span>
          <Input
            autoComplete="name"
            placeholder="A. Rahman"
            value={form.name}
            onChange={set("name")}
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Email</span>
          <Input
            type="email"
            autoComplete="email"
            placeholder="admin@fuelco.example"
            value={form.email}
            onChange={set("email")}
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Password</span>
          <PasswordInput
            autoComplete="new-password"
            placeholder="At least 8 characters"
            value={form.password}
            onChange={set("password")}
          />
        </label>
        <label className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Confirm password</span>
          <PasswordInput
            autoComplete="new-password"
            placeholder="Repeat your password"
            value={form.confirm}
            onChange={set("confirm")}
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
          {loading ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

export { SignupForm };
