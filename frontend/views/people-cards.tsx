"use client";

import { useMemo, useState } from "react";
import { Nfc, Plus, Search } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
import { Button } from "@/components/ui/button";
import {
  Dialog,
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CARDS,
  PEOPLE,
  SCHEDULES,
  type CardRecord,
  type Person,
  type PersonCategory,
} from "@/lib/station-data";

const CATEGORIES: PersonCategory[] = ["Normal", "VIP", "Guest", "Patrol"];

function PeopleCardsView() {
  // shortcut: local state only — writes are not pushed to the controller yet
  const [people, setPeople] = useState<Person[]>(PEOPLE);
  const [cards, setCards] = useState<CardRecord[]>(CARDS);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<"All" | PersonCategory>("All");
  const [selected, setSelected] = useState<Person | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    category: "Normal" as PersonCategory,
    validFrom: "2026-11-12",
    validTo: "2027-11-11",
  });

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return people.filter((p) => {
      if (category !== "All" && p.category !== category) return false;
      if (!q) return true;
      const card = cards.find((c) => c.personId === p.id);
      return (
        p.name.toLowerCase().includes(q) ||
        (card?.masked.toLowerCase().includes(q) ?? false)
      );
    });
  }, [people, cards, query, category]);

  const cardOf = (personId: string) =>
    cards.find((c) => c.personId === personId);

  const activeCards = cards.filter((c) => c.status === "Active").length;
  const expiredCards = cards.filter((c) => c.status === "Expired").length;
  const blockedCards = cards.filter((c) => c.status === "Blocked").length;

  const addPerson = () => {
    if (!form.name.trim()) return;
    const id = `P${String(people.length + 1).padStart(3, "0")}`;
    setPeople([...people, { id, name: form.name.trim(), category: form.category, status: "Active" }]);
    setCards([
      ...cards,
      {
        id: `C${String(cards.length + 1).padStart(3, "0")}`,
        personId: id,
        // enrolled on first MIFARE read in the real flow; placeholder number here
        masked: `0142 ···· ${String(1000 + Math.floor(Math.random() * 9000))}`,
        tech: "MIFARE 13.56 MHz",
        validFrom: form.validFrom,
        validTo: form.validTo,
        status: "Active",
        scheduleId: "SCH01",
      },
    ]);
    setAddOpen(false);
    setForm({ ...form, name: "" });
  };

  const setCardStatus = (cardId: string, status: CardRecord["status"]) =>
    setCards(cards.map((c) => (c.id === cardId ? { ...c, status } : c)));

  const selectedCard = selected ? cardOf(selected.id) : undefined;

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">People &amp; cards</h2>
          <p className="text-xs text-muted-foreground">
            People records and the card credentials that can authenticate at the washroom reader
          </p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger render={<Button size="sm"><Plus aria-hidden />Add person</Button>} />
          <DialogContent className="sm:max-w-sm">
            <DialogHeader>
              <DialogTitle>Add person</DialogTitle>
              <DialogDescription>
                Creates a person record and a placeholder card credential.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-3 py-1 text-sm">
              <label className="grid gap-1">
                <span className="text-xs font-medium text-muted-foreground">Name</span>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" />
              </label>
              <label className="grid gap-1">
                <span className="text-xs font-medium text-muted-foreground">Category</span>
                <Select value={form.category} onValueChange={(v) => v && setForm({ ...form, category: v as PersonCategory })}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="grid gap-1">
                  <span className="text-xs font-medium text-muted-foreground">Valid from</span>
                  <Input type="date" value={form.validFrom} onChange={(e) => setForm({ ...form, validFrom: e.target.value })} />
                </label>
                <label className="grid gap-1">
                  <span className="text-xs font-medium text-muted-foreground">Valid to</span>
                  <Input type="date" value={form.validTo} onChange={(e) => setForm({ ...form, validTo: e.target.value })} />
                </label>
              </div>
            </div>
            <DialogFooter>
              <Button size="sm" onClick={addPerson} disabled={!form.name.trim()}>
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* summary strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Total people", people.length],
          ["Active cards", activeCards],
          ["Expired cards", expiredCards],
          ["Blocked cards", blockedCards],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border bg-card px-3 py-2">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-xl font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      {/* search + category filter */}
      <Panel title="Directory">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="relative min-w-52 flex-1">
            <Search aria-hidden className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name or card number" className="h-8 pl-8 text-xs" />
          </div>
          <div role="group" aria-label="Category filter" className="inline-flex rounded-lg bg-muted p-0.5">
            {(["All", ...CATEGORIES] as const).map((c) => (
              <button
                key={c}
                type="button"
                aria-pressed={category === c}
                onClick={() => setCategory(c)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  category === c ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Person</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Card</TableHead>
              <TableHead>Validity</TableHead>
              <TableHead>Card status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((p) => {
              const card = cardOf(p.id);
              return (
                <TableRow key={p.id} className="cursor-pointer" onClick={() => setSelected(p)}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell>{p.category}</TableCell>
                  <TableCell className="font-mono text-xs">{card?.masked ?? "—"}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {card ? `${card.validFrom} → ${card.validTo}` : "—"}
                  </TableCell>
                  <TableCell>
                    {card ? (
                      <ToneBadge tone={card.status === "Active" ? "green" : card.status === "Blocked" ? "red" : "grey"}>
                        {card.status}
                      </ToneBadge>
                    ) : (
                      <span className="text-muted-foreground">No card</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {filtered.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No people match the current filters.</p>
        ) : null}
      </Panel>

      {/* person detail drawer */}
      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-md">
          {selected ? (
            <SheetHeader className="mt-2 gap-4 text-left">
              <SheetTitle>{selected.name}</SheetTitle>
              <SheetDescription>
                {selected.id} · {selected.category} user
              </SheetDescription>

              {selectedCard ? (
                <>
                  <section>
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Assigned credential
                    </h3>
                    <dl className="space-y-2 text-sm">
                      <div className="flex justify-between gap-4 border-b pb-2">
                        <dt className="text-muted-foreground">Card</dt>
                        <dd className="font-mono">{selectedCard.masked}</dd>
                      </div>
                      <div className="flex justify-between gap-4 border-b pb-2">
                        <dt className="text-muted-foreground">Technology</dt>
                        <dd>{selectedCard.tech}</dd>
                      </div>
                      <div className="flex justify-between gap-4 border-b pb-2">
                        <dt className="text-muted-foreground">Validity</dt>
                        <dd className="font-mono text-xs">
                          {selectedCard.validFrom} → {selectedCard.validTo}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4 border-b pb-2">
                        <dt className="text-muted-foreground">Schedule</dt>
                        <dd>
                          {SCHEDULES.find((s) => s.id === selectedCard.scheduleId)?.name ?? "—"}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-muted-foreground">Status</dt>
                        <dd>
                          <ToneBadge tone={selectedCard.status === "Active" ? "green" : selectedCard.status === "Blocked" ? "red" : "grey"}>
                            {selectedCard.status}
                          </ToneBadge>
                        </dd>
                      </div>
                    </dl>
                  </section>

                  {/* card actions */}
                  <section>
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Card actions
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedCard.status === "Active" ? (
                        <>
                          <Button variant="outline" size="sm" onClick={() => setCardStatus(selectedCard.id, "Blocked")}>
                            Block card
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => setCardStatus(selectedCard.id, "Expired")}>
                            Deactivate
                          </Button>
                        </>
                      ) : (
                        <Button size="sm" onClick={() => setCardStatus(selectedCard.id, "Active")}>
                          Activate card
                        </Button>
                      )}
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Every card change is recorded in the admin audit trail.
                    </p>
                  </section>
                </>
              ) : (
                <section>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Card enrollment
                  </h3>
                  <div className="flex items-center gap-3 rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
                    <Nfc aria-hidden className="size-5" />
                    Present a 13.56 MHz MIFARE card at the reader to enroll it
                    against this person.
                  </div>
                </section>
              )}
            </SheetHeader>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export { PeopleCardsView };
