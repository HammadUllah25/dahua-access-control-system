"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Nfc, RotateCcw } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  confirmCardEnrollmentAction,
  getCardEnrollmentAction,
  startCardEnrollmentAction,
  type CardEnrollmentRecord,
} from "@/actions/card-enrollments";

type Props = {
  stationId: number;
  userId: number;
  userName: string;
  deviceId: number;
  onDone?: () => void;
  onCancel?: () => void;
};

function AssignCard({
  stationId,
  userId,
  userName,
  deviceId,
  onDone,
  onCancel,
}: Props) {
  const [session, setSession] = useState<CardEnrollmentRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [validFrom, setValidFrom] = useState(
    () => new Date().toISOString().slice(0, 10)
  );
  const [validUntil, setValidUntil] = useState("2037-12-31");

  const start = async () => {
    setLoading(true);
    setError(null);
    setConfirmed(false);
    setSuccessMessage("");
    try {
      const res = await startCardEnrollmentAction(stationId, userId, deviceId);
      if (!res.success) {
        setError(res.raw ?? res.error);
        toast.error(res.raw ?? res.error);
        return;
      }
      setSession(res.data);
      toast.info(res.data.message);
    } finally {
      setLoading(false);
    }
  };

  const status = session?.status;
  const token = session?.session_token;

  useEffect(() => {
    if (!token || status !== "waiting") return;
    let cancelled = false;

    const tick = async () => {
      const res = await getCardEnrollmentAction(stationId, userId, token);
      if (cancelled) return;
      if (!res.success) {
        setError(res.raw ?? res.error);
        setSession(null);
        return;
      }
      setSession(res.data);
      if (res.data.status === "captured") {
        toast.success(`Card ${res.data.card_number ?? ""} captured.`);
      }
      if (res.data.status === "expired" || res.data.status === "cancelled") {
        setError(res.data.message);
      }
    };

    const timer = window.setInterval(tick, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [status, token, stationId, userId]);

  const confirm = async () => {
    if (!session?.card_number) return;
    if (!validFrom || !validUntil) {
      setError("Please select card validity dates.");
      return;
    }
    if (validUntil < validFrom) {
      setError("Valid until must be on or after valid from.");
      return;
    }
    setConfirming(true);
    setError(null);
    try {
      const res = await confirmCardEnrollmentAction(
        stationId,
        userId,
        session.session_token,
        {
          card_name: session.card_number,
          card_type: "general",
          is_valid: true,
          valid_from: validFrom,
          valid_until: validUntil,
          door_indices: [0],
          time_section_indices: [0],
        }
      );
      if (!res.success) {
        setError(res.raw ?? res.error);
        toast.error(res.raw ?? res.error);
        return;
      }
      const message =
        typeof res.data.message === "string"
          ? res.data.message
          : `Card assigned to ${userName}.`;
      setSuccessMessage(message);
      setConfirmed(true);
      toast.success(message);
    } finally {
      setConfirming(false);
    }
  };

  const reset = () => {
    setSession(null);
    setError(null);
    setConfirmed(false);
    setSuccessMessage("");
  };

  if (confirmed) {
    return (
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-lg border border-led-green/25 bg-led-green/10 p-3 text-sm">
          <CheckCircle2 aria-hidden className="mt-0.5 size-5 shrink-0 text-led-green" />
          <div>
            <p className="font-semibold">Card assigned to {userName}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {successMessage ||
                "The card is written to the controller. Run inventory verification before treating the sync as complete."}
            </p>
          </div>
        </div>
        <div className="flex justify-end">
          <Button size="sm" onClick={onDone}>
            Done
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3 rounded-lg border border-dashed p-3 text-sm">
        <Nfc aria-hidden className="mt-0.5 size-5 shrink-0 text-primary" />
        <div>
          <p className="font-medium">Present a card at the washroom reader</p>
          <p className="mt-1 text-xs text-muted-foreground">
            The controller listens for one card scan, then shows the captured
            UID for confirmation. Enrollment expires after 90 seconds.
          </p>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-led-red/25 bg-led-red/10 p-3 text-xs text-led-red">
          {error}
        </div>
      ) : null}

      {session && !confirmed ? (
        <div className="space-y-3 rounded-lg border bg-muted/30 p-3 text-sm">
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground">Status</span>
            <span className="font-medium capitalize">{session.status}</span>
          </div>
          {session.card_number ? (
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Card UID</span>
              <span className="font-mono text-xs font-semibold">
                {session.card_number}
              </span>
            </div>
          ) : null}
          {session.status === "waiting" ? (
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 aria-hidden className="size-3.5 animate-spin" />
              Waiting for a card scan…
            </p>
          ) : null}
        </div>
      ) : null}

      {!confirmed ? (
        <div className="grid gap-3 rounded-lg border p-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-xs font-medium text-muted-foreground">Valid from</span>
            <Input
              type="date"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
              className="h-9 text-sm"
              disabled={confirming}
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs font-medium text-muted-foreground">Valid until</span>
            <Input
              type="date"
              value={validUntil}
              onChange={(e) => setValidUntil(e.target.value)}
              min={validFrom || undefined}
              className="h-9 text-sm"
              disabled={confirming}
            />
          </label>
          <p className="text-[11px] text-muted-foreground sm:col-span-2">
            Card validity is written to the controller when you confirm.
          </p>
        </div>
      ) : null}

      <div className="flex flex-wrap justify-end gap-2">
        {onCancel ? (
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={confirming || loading}
          >
            Cancel
          </Button>
        ) : null}
        {session?.status === "captured" ? (
          <Button size="sm" onClick={confirm} disabled={confirming}>
            {confirming ? (
              <>
                <Loader2 aria-hidden className="animate-spin" />
                Writing card…
              </>
            ) : (
              "Confirm & write card"
            )}
          </Button>
        ) : session &&
          (session.status === "waiting" || session.status === "confirming") ? (
          <Button size="sm" disabled>
            <Loader2 aria-hidden className="animate-spin" />
            {session.status === "waiting" ? "Waiting for card…" : "Confirming…"}
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={session ? reset : start}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 aria-hidden className="animate-spin" />
                Starting listener…
              </>
            ) : session ? (
              <>
                <RotateCcw aria-hidden />
                Try again
              </>
            ) : (
              <>
                <Nfc aria-hidden />
                Start card scan
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

export { AssignCard };
