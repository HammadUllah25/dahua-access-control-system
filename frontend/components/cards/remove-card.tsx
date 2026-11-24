"use client";

import { useState } from "react";
import { CreditCard, Loader2 } from "lucide-react";
import { toast } from "react-toastify";

import { revokeStationUserCardAction } from "@/actions/station-users";
import { Button } from "@/components/ui/button";

// DELETE /stations/{sid}/users/{uid}/card: the controller stops accepting the card.
function RemoveCard({
  stationId,
  userId,
  userName,
  cardNumber,
  disabled,
  onRemoved,
}: {
  stationId: number;
  userId: number;
  userName: string;
  cardNumber: string;
  disabled?: boolean;
  onRemoved: () => void;
}) {
  const [busy, setBusy] = useState(false);

  const remove = async () => {
    if (!window.confirm(`Remove card ${cardNumber} from ${userName}? It will stop opening the door.`)) return;
    setBusy(true);
    const res = await revokeStationUserCardAction(stationId, userId);
    setBusy(false);
    if (!res.success) {
      toast.error(res.raw ?? res.error);
      return;
    }
    toast.success(`Card ${res.data.card_number} removed from ${userName}.`);
    onRemoved();
  };

  return (
    <Button
      size="sm"
      variant="outline"
      onClick={() => void remove()}
      disabled={disabled || busy}
      title="Remove this card from the user"
      className="text-destructive hover:text-destructive"
    >
      {busy ? <Loader2 aria-hidden className="animate-spin" /> : <CreditCard aria-hidden />}
      Remove card
    </Button>
  );
}

export { RemoveCard };
