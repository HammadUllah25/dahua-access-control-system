"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// shortcut: mock reset request — the code email lands with the backend
function ForgotPasswordForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) {
      setError("Enter the email address on your admin account.");
      return;
    }
    setError(null);
    setLoading(true);
    setTimeout(() => {
      router.push(`/verify?purpose=reset&email=${encodeURIComponent(email)}`);
    }, 700);
  };

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Forgot your password?</h1>
        <p className="text-sm text-muted-foreground">
          Enter your account email and we&apos;ll send a 6-digit reset code.
        </p>
      </div>

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

        {error ? (
          <p role="alert" className="text-xs font-medium text-destructive">
            {error}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? (
            <Loader2 aria-hidden className="motion-safe:animate-spin" />
          ) : null}
          {loading ? "Sending code…" : "Send reset code"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Remembered it?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

export { ForgotPasswordForm };
