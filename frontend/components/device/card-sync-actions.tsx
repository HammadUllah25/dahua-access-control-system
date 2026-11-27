"use client";

import { useState } from "react";
import { ListChecks, UploadCloud } from "lucide-react";
import { toast } from "react-toastify";

import {
  inventoryCheckAction,
  reprovisionDeviceAction,
  type InventoryCheckResult,
} from "@/actions/device-control";
import { Button } from "@/components/ui/button";

// POST /devices/{id}/inventory-check and POST /devices/{id}/reprovision.
function CardSyncActions({
  deviceId,
  inventoryStatus,
  onDone,
}: {
  deviceId: number;
  inventoryStatus: string;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState<"check" | "reprovision" | null>(null);
  const [result, setResult] = useState<InventoryCheckResult | null>(null);

  const check = async () => {
    setBusy("check");
    const res = await inventoryCheckAction(deviceId);
    setBusy(null);
    if (!res.success) {
      toast.error(res.raw ?? res.error);
    } else {
      setResult(res.data);
      toast.success(
        res.data.missing_cards.length
          ? `${res.data.missing_cards.length} card(s) missing on the controller.`
          : "Controller cards match the database."
      );
    }
    onDone();
  };

  const reprovision = async () => {
    const missing = result?.missing_cards ?? [];
    const list = missing.length ? `\n\n${missing.join(", ")}` : "";
    if (!window.confirm(`Write the missing card(s) from the database to the controller?${list}`)) return;
    setBusy("reprovision");
    const res = await reprovisionDeviceAction(deviceId);
    setBusy(null);
    if (!res.success) {
      toast.error(res.raw ?? res.error);
    } else if (res.data.failed_cards.length) {
      toast.error(`${res.data.failed_cards.length} card(s) could not be written; see the controller event history.`);
    } else {
      toast.success(`${res.data.restored_cards.length} card(s) written to the controller.`);
    }
    setResult(null);
    onDone();
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" disabled={busy !== null} onClick={() => void check()}>
          <ListChecks aria-hidden />
          {busy === "check" ? "Reading controller…" : "Check inventory"}
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={busy !== null || inventoryStatus !== "needs_reprovisioning"}
          onClick={() => void reprovision()}
          title={
            inventoryStatus === "needs_reprovisioning"
              ? "Write missing cards from the database to the controller"
              : "Run Check inventory first; enabled when cards are missing"
          }
          className="disabled:cursor-not-allowed disabled:pointer-events-auto"
        >
          <UploadCloud aria-hidden />
          {busy === "reprovision" ? "Writing cards…" : "Reprovision from cloud"}
        </Button>
      </div>
      {result ? (
        <ul className="space-y-1 text-xs text-muted-foreground">
          <li>Missing on controller: {result.missing_cards.join(", ") || "none"}</li>
          <li>Only on controller: {result.unexpected_cards.join(", ") || "none"}</li>
          {result.repaired_record_numbers.length ? (
            <li>Record numbers repaired: {result.repaired_record_numbers.join(", ")}</li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}

export { CardSyncActions };
