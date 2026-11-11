"use client";

import * as React from "react";
import { CreditCardIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// shortcut: static options shaped like /persons and /devices API results;
// swap for fetched data when the API is wired.
const PEOPLE = [
  "Sahil Mehmood · EMP-0001",
  "Ayesha Khan · EMP-0021",
  "Bilal Ahmed · EMP-0007",
  "Usman Tariq · EMP-0013",
];

const WASHROOMS = [
  "Washroom A · Ground floor",
  "Washroom B · Ground floor",
  "Washroom C · First floor",
  "Washroom D · First floor",
  "Staff washroom · Facilities",
];

function AllocateCardDialog() {
  const [open, setOpen] = React.useState(false);
  const [person, setPerson] = React.useState<string | null>(null);
  const [washroom, setWashroom] = React.useState<string | null>(null);
  const [cardNumber, setCardNumber] = React.useState("");

  const canAssign = Boolean(person && washroom && cardNumber.trim());

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>
        <CreditCardIcon data-icon="inline-start" />
        Assign card
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign a card</DialogTitle>
          <DialogDescription>
            Allocate an IC card to a person for one washroom controller.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          <div className="grid gap-2">
            <span className="text-sm font-medium" id="person-label">
              Person
            </span>
            <Select value={person} onValueChange={setPerson}>
              <SelectTrigger
                aria-labelledby="person-label"
                className="w-full"
              >
                <SelectValue placeholder="Choose a person" />
              </SelectTrigger>
              <SelectContent>
                {PEOPLE.map((person) => (
                  <SelectItem key={person} value={person}>
                    {person}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label htmlFor="card-number" className="text-sm font-medium">
              Card number
            </label>
            <Input
              id="card-number"
              value={cardNumber}
              onChange={(event) => setCardNumber(event.target.value)}
              placeholder="FB66983B"
              className="font-mono uppercase"
              autoComplete="off"
            />
          </div>
          <div className="grid gap-2">
            <span className="text-sm font-medium" id="washroom-label">
              Washroom
            </span>
            <Select value={washroom} onValueChange={setWashroom}>
              <SelectTrigger
                aria-labelledby="washroom-label"
                className="w-full"
              >
                <SelectValue placeholder="Choose a washroom" />
              </SelectTrigger>
              <SelectContent>
                {WASHROOMS.map((washroom) => (
                  <SelectItem key={washroom} value={washroom}>
                    {washroom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label htmlFor="valid-until" className="text-sm font-medium">
              Valid until
            </label>
            <Input
              id="valid-until"
              type="date"
              defaultValue="2036-11-09"
              className="bg-transparent dark:bg-transparent"
            />
          </div>
        </div>
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
          <Button disabled={!canAssign}>Assign card</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export { AllocateCardDialog };
