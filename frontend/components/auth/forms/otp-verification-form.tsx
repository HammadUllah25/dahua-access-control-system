"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { OtpInput } from "@/components/auth/forms/otp-input";

const DEMO_CODE = "123456";
const RESEND_SECONDS = 30;

// One OTP page serves both flows: signup verification and password reset.
// shortcut: fixed demo code — real codes come from the backend mailer
function OtpVerificationForm() {
  const router = useRouter();
  const params = useSearchParams();
  const purpose = params.get("purpose") === "reset" ? "reset" : "signup";
  const email = params.get("email") ?? "your email";

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(RESEND_SECONDS);
  const [resent, setResent] = useState(false);

  useEffect(() => {
    if (seconds <= 0) return;
    const timer = setInterval(() => setSeconds((s) => s - 1), 1000);
    return () => clearInterval(timer);
  }, [seconds]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const entered = code.replace(/ /g, "");
    if (!/^\d{6}$/.test(entered)) {
      setError("Enter all six digits of the code.");
      return;
    }
    if (entered !== DEMO_CODE) {
      setError("That code didn't match — check it and try again.");
      return;
    }
    setError(null);
    setLoading(true);
    setTimeout(() => {
      router.push(purpose === "reset" ? "/reset-password" : "/onboarding");
    }, 700);
  };

  const resend = () => {
    setResent(true);
    setSeconds(RESEND_SECONDS);
  };

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Verify your code</h1>
        <p className="text-sm text-muted-foreground">
          We sent a 6-digit code to{" "}
          <span className="font-medium text-foreground">{email}</span>.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-4">
        <OtpInput value={code} onChange={setCode} disabled={loading} />

        {error ? (
          <p role="alert" className="text-xs font-medium text-destructive">
            {error}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? (
            <Loader2 aria-hidden className="motion-safe:animate-spin" />
          ) : null}
          {loading ? "Verifying…" : "Verify"}
        </Button>
      </form>

      <div className="space-y-1 text-center text-xs text-muted-foreground">
        {seconds > 0 ? (
          <p>
            Didn&apos;t get it? Resend available in{" "}
            <span className="font-medium tabular-nums text-foreground">{seconds}s</span>
          </p>
        ) : (
          <button
            type="button"
            onClick={resend}
            className="font-medium text-primary hover:underline"
          >
            Resend code
          </button>
        )}
        {resent ? <p>Code resent — use the latest one.</p> : null}
        <p>Demo build — the code is 123456.</p>
      </div>

      <p className="text-center text-sm text-muted-foreground">
        <Link
          href={purpose === "reset" ? "/forgot-password" : "/signup"}
          className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
        >
          <ArrowLeft aria-hidden className="size-3.5" />
          {purpose === "reset" ? "Use a different email" : "Change email"}
        </Link>
      </p>
    </div>
  );
}

export { OtpVerificationForm };
