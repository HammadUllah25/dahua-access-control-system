"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  CreditCard,
  IdCard,
  Loader2,
  Nfc,
  Plus,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";
import { toast } from "react-toastify";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
import { AssignCard } from "@/components/cards/assign-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  listDevicesAction,
  type DeviceListRecord,
} from "@/actions/get-devices";
import {
  listStationsAction,
  type StationRecord,
} from "@/actions/stations";
import {
  createStationUserAction,
  listStationRolesAction,
  listStationUsersAction,
  type OperationalRoleRecord,
  type StationUserRecord,
} from "@/actions/station-users";

type AccessKind = "profile" | "shared_staff" | "general" | "master";

const ACCESS_TYPES: {
  id: AccessKind;
  title: string;
  description: string;
  icon: typeof Users;
}[] = [
  {
    id: "profile",
    title: "Individual profile",
    description:
      "Create a user profile. Staff can have their own card (or you can assign a card later).",
    icon: IdCard,
  },
  {
    id: "shared_staff",
    title: "Shared staff card",
    description:
      "Single card for all staff. One shared access entry with one card assigned to it.",
    icon: Users,
  },
  {
    id: "general",
    title: "General access card",
    description:
      "For walk-ins/general users who scan a general card without a personal profile.",
    icon: CreditCard,
  },
  {
    id: "master",
    title: "Master card (area)",
    description:
      "General master card allocated to an area. Intended to work only within that area.",
    icon: ShieldCheck,
  },
];

function inferAccessKind(user: StationUserRecord): {
  kind: AccessKind;
  label: string;
} {
  const name = user.name.toLowerCase();
  if (name.includes("master")) return { kind: "master", label: "Master card" };
  if (name.includes("shared") || name.includes("all staff"))
    return { kind: "shared_staff", label: "Shared staff" };
  if (name.includes("general") || name.includes("walk-in") || name.includes("walk in"))
    return { kind: "general", label: "General access" };
  return { kind: "profile", label: "Individual profile" };
}

function PeopleCardsView() {
  const [stations, setStations] = useState<StationRecord[]>([]);
  const [devices, setDevices] = useState<DeviceListRecord[]>([]);
  const [stationId, setStationId] = useState("");
  const [users, setUsers] = useState<StationUserRecord[]>([]);
  const [roles, setRoles] = useState<OperationalRoleRecord[]>([]);
  const [baseLoading, setBaseLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [addOpen, setAddOpen] = useState(false);
  const [accessKind, setAccessKind] = useState<AccessKind>("profile");
  const [form, setForm] = useState({
    name: "",
    phone: "",
    roleId: "",
    area: "",
  });
  const [saving, setSaving] = useState(false);
  const [cardUser, setCardUser] = useState<StationUserRecord | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loadBase = useCallback(async () => {
    setBaseLoading(true);
    const [stationRes, deviceRes] = await Promise.all([
      listStationsAction(),
      listDevicesAction(),
    ]);
    if (!stationRes.success || !deviceRes.success) {
      const message =
        (!stationRes.success ? stationRes.error : "") ||
        (!deviceRes.success ? deviceRes.error : "") ||
        "Could not load stations.";
      setError(message);
      toast.error(message);
    } else {
      setStations(stationRes.data);
      setDevices(deviceRes.data);
      setStationId((current) => {
        if (current && stationRes.data.some((s) => String(s.id) === current)) {
          return current;
        }
        return stationRes.data[0] ? String(stationRes.data[0].id) : "";
      });
      setError(null);
    }
    setBaseLoading(false);
  }, []);

  useEffect(() => {
    void loadBase();
  }, [loadBase]);

  useEffect(() => {
    if (!stationId) {
      setUsers([]);
      setRoles([]);
      setUsersLoading(false);
      return;
    }
    let cancelled = false;
    setUsers([]);
    setRoles([]);
    setRoleFilter("all");
    setUsersLoading(true);
    Promise.all([
      listStationRolesAction(Number(stationId)),
      listStationUsersAction(Number(stationId)),
    ]).then(([roleRes, userRes]) => {
      if (cancelled) return;
      if (!roleRes.success || !userRes.success) {
        const message =
          (!roleRes.success ? roleRes.error : "") ||
          (!userRes.success ? userRes.error : "") ||
          "Could not load station people.";
        setError(message);
        toast.error(message);
      } else {
        setRoles(roleRes.data);
        setUsers(userRes.data);
        setError(null);
      }
      setUsersLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [stationId, reloadKey]);

  const selectedStation = stations.find(
    (station) => String(station.id) === stationId
  );
  const stationDevices = devices.filter(
    (device) => device.station_id === selectedStation?.id
  );
  const cardDevice =
    stationDevices.find((device) => device.status === "online") ??
    stationDevices[0];
  const hasStation = Boolean(selectedStation);
  const canAddUser = hasStation && !usersLoading && roles.length > 0;

  const preferredRole = useMemo(() => {
    const byCode = (code: string) =>
      roles.find((role) => role.code.toUpperCase() === code);
    if (accessKind === "master" || accessKind === "general") {
      return byCode("VISITOR") ?? byCode("CUSTOMER") ?? roles[0];
    }
    if (accessKind === "shared_staff") {
      return byCode("STAFF") ?? byCode("EMPLOYEE") ?? byCode("CUSTOMER") ?? roles[0];
    }
    return byCode("STAFF") ?? byCode("CUSTOMER") ?? roles[0];
  }, [roles, accessKind]);

  const q = query.trim().toLowerCase();
  const filtered = users.filter((user) => {
    if (roleFilter !== "all" && String(user.role.id) !== roleFilter) {
      return false;
    }
    if (!q) return true;
    const access = inferAccessKind(user);
    return (
      user.name.toLowerCase().includes(q) ||
      (user.phone?.toLowerCase().includes(q) ?? false) ||
      (user.active_card?.card_number.toLowerCase().includes(q) ?? false) ||
      access.label.toLowerCase().includes(q)
    );
  });

  const activeCards = users.filter((user) => user.active_card).length;
  const profileCount = users.filter((u) => inferAccessKind(u).kind === "profile").length;
  const sharedGeneralCount = users.length - profileCount;

  const openAdd = () => {
    if (!selectedStation) return;
    setAccessKind("profile");
    setForm({
      name: "",
      phone: "",
      roleId: preferredRole ? String(preferredRole.id) : "",
      area: "",
    });
    setAddOpen(true);
  };

  useEffect(() => {
    if (!addOpen) return;
    const defaults: Record<AccessKind, string> = {
      profile: "",
      shared_staff: "All Staff - Shared Card",
      general: "General Access Card",
      master: "Master Card (Area)",
    };
    setForm((current) => ({
      ...current,
      name: accessKind === "profile" ? "" : defaults[accessKind],
      area: accessKind === "master" ? current.area : "",
      roleId: preferredRole ? String(preferredRole.id) : current.roleId,
    }));
  }, [accessKind, addOpen, preferredRole]);

  const createUser = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedStation || !form.roleId) return;
    let name = form.name.trim();
    if (accessKind === "master" && form.area.trim()) {
      name = `Master Card - ${form.area.trim()}`;
    }
    if (!name) return;
    if (accessKind === "profile" && !form.name.trim()) return;

    setSaving(true);
    try {
      const res = await createStationUserAction(selectedStation.id, {
        name,
        phone: form.phone.trim() || null,
        role_id: Number(form.roleId),
        is_billable: null,
      });
      if (!res.success) {
        toast.error(res.raw ?? res.error);
        return;
      }
      toast.success(`${res.data.name} added to ${selectedStation.name}.`);
      setAddOpen(false);
      setReloadKey((key) => key + 1);
    } finally {
      setSaving(false);
    }
  };

  const needsArea = accessKind === "master";

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            People &amp; cards
          </h2>
          <p className="text-xs text-muted-foreground">
            Manage user profiles and card access: individual, shared staff,
            general, and area master cards
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {stations.length > 0 ? (
            <Select
              value={stationId}
              onValueChange={(value) => value && setStationId(value)}
            >
              <SelectTrigger className="h-8 w-56">
                <SelectValue placeholder="Select a station" />
              </SelectTrigger>
              <SelectContent>
                {stations.map((station) => (
                  <SelectItem key={station.id} value={String(station.id)}>
                    {station.name} ({station.station_code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
          <Button
            size="sm"
            onClick={openAdd}
            disabled={!canAddUser}
            title={
              canAddUser
                ? "Add a user profile or card access"
                : !hasStation
                  ? "Create a station before adding people"
                  : usersLoading
                    ? "Loading station roles"
                    : "No operational roles available"
            }
            className="disabled:cursor-not-allowed disabled:pointer-events-auto"
          >
            <Plus aria-hidden />
            Add user / card
          </Button>
        </div>
      </div>

      {!hasStation ? (
        <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
          Add user is locked until a station exists.{" "}
          <Link href="/stations" className="font-medium text-primary hover:underline">
            Create a station first
          </Link>
          .
        </div>
      ) : null}

      {hasStation && !cardDevice ? (
        <div className="rounded-lg border border-led-amber/25 bg-led-amber/10 p-3 text-xs text-led-amber">
          This station has no controller assigned. Card assignment stays locked
          until a controller is attached in Stations.
        </div>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-led-red/25 bg-led-red/10 p-3 text-xs text-led-red">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Profiles", profileCount],
          ["Shared / general", sharedGeneralCount],
          ["Cards assigned", activeCards],
          ["Without card", Math.max(users.length - activeCards, 0)],
        ].map(([label, value]) => (
          <div key={label} className="card-glow rounded-lg border bg-card px-3 py-2">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-xl font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {ACCESS_TYPES.map((type) => {
          const Icon = type.icon;
          return (
            <Card key={type.id} size="sm" className="h-full">
              <CardContent className="flex gap-3 py-1">
                <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon aria-hidden className="size-4" />
                </span>
                <div className="space-y-0.5">
                  <p className="text-sm font-medium leading-tight">{type.title}</p>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {type.description}
                  </p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Panel
        title="Users & card access"
        description={
          selectedStation
            ? `${selectedStation.name} · ${users.length} entr${users.length === 1 ? "y" : "ies"}`
            : "Select a station to manage users and cards"
        }
        action={
          baseLoading || usersLoading ? (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 aria-hidden className="size-3.5 animate-spin" />
              Loading
            </span>
          ) : undefined
        }
      >
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="relative min-w-52 flex-1">
            <Search
              aria-hidden
              className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search name, type, phone or card number"
              className="h-8 pl-8 text-xs"
            />
          </div>
          <Select
            value={roleFilter}
            onValueChange={(value) => value && setRoleFilter(value)}
          >
            <SelectTrigger className="h-8 w-40">
              <SelectValue placeholder="All roles" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All roles</SelectItem>
              {roles.map((role) => (
                <SelectItem key={role.id} value={String(role.id)}>
                  {role.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User / access</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Phone</TableHead>
              <TableHead>Card</TableHead>
              <TableHead>Validity</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((user) => {
              const card = user.active_card;
              const canAssign = Boolean(cardDevice) && !card;
              const access = inferAccessKind(user);
              return (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">
                    {user.name}
                    <span className="block font-mono text-[11px] text-muted-foreground">
                      #{user.id}
                    </span>
                  </TableCell>
                  <TableCell>
                    <ToneBadge
                      tone={
                        access.kind === "master"
                          ? "amber"
                          : access.kind === "general" || access.kind === "shared_staff"
                            ? "blue"
                            : "grey"
                      }
                    >
                      {access.label}
                    </ToneBadge>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs font-medium">{user.role.name}</span>
                    <span className="block font-mono text-[11px] text-muted-foreground">
                      {user.role.code}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {user.phone ?? "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {card?.card_number ?? "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {card
                      ? `${card.valid_from ?? "—"} → ${card.valid_until ?? "—"}`
                      : "—"}
                  </TableCell>
                  <TableCell>
                    {card ? (
                      <ToneBadge
                        tone={
                          !card.is_valid ||
                          card.sync_status === "failed" ||
                          card.sync_status === "needs_reprovisioning"
                            ? "red"
                            : card.sync_status === "pending_verification" ||
                                card.sync_status === "pending"
                              ? "amber"
                              : "green"
                        }
                      >
                        {!card.is_valid
                          ? "Inactive"
                          : card.sync_status === "failed"
                            ? "Sync failed"
                            : card.sync_status === "needs_reprovisioning"
                              ? "Reprovision"
                              : card.sync_status === "pending_verification" ||
                                  card.sync_status === "pending"
                                ? "Pending sync"
                                : "Assigned"}
                      </ToneBadge>
                    ) : (
                      <ToneBadge tone="grey">No card</ToneBadge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!canAssign}
                      onClick={() => setCardUser(user)}
                      title={
                        card
                          ? "This entry already has a card on record"
                          : cardDevice
                            ? "Scan and assign a card"
                            : "Assign a controller to this station first"
                      }
                      className="disabled:cursor-not-allowed disabled:pointer-events-auto"
                    >
                      <Nfc aria-hidden />
                      {card ? "Card assigned" : "Assign card"}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {!baseLoading && !usersLoading && filtered.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            {hasStation
              ? "No users or card access entries match the current filters."
              : "Create a station before adding people."}
          </p>
        ) : null}
      </Panel>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add user / card access</DialogTitle>
            <DialogDescription>
              {selectedStation
                ? `${selectedStation.name} · create a profile or a shared/general/master card entry.`
                : "Create a station first."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={createUser} className="grid gap-4">
            <div className="grid gap-2 sm:grid-cols-2">
              {ACCESS_TYPES.map((type) => {
                const Icon = type.icon;
                const active = accessKind === type.id;
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setAccessKind(type.id)}
                    className={`flex items-start gap-3 rounded-xl border p-3 text-left transition-colors ${
                      active
                        ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                        : "border-border hover:bg-muted/40"
                    }`}
                  >
                    <span
                      className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg ${
                        active
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <Icon aria-hidden className="size-4" />
                    </span>
                    <span className="space-y-0.5">
                      <span className="block text-sm font-medium leading-tight">
                        {type.title}
                      </span>
                      <span className="block text-xs leading-relaxed text-muted-foreground">
                        {type.description}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1 sm:col-span-2">
                <span className="text-xs font-medium text-muted-foreground">
                  {accessKind === "profile"
                    ? "Full name"
                    : accessKind === "master"
                      ? "Area name (for master card)"
                      : "Access name"}
                </span>
                {accessKind === "master" ? (
                  <Input
                    value={form.area}
                    onChange={(event) =>
                      setForm({ ...form, area: event.target.value })
                    }
                    placeholder="e.g. Area A / North Zone"
                    className="h-9 text-sm"
                    disabled={saving}
                    required
                  />
                ) : (
                  <Input
                    value={form.name}
                    onChange={(event) =>
                      setForm({ ...form, name: event.target.value })
                    }
                    placeholder={
                      accessKind === "profile"
                        ? "Full name"
                        : "Access/card name"
                    }
                    className="h-9 text-sm"
                    disabled={saving}
                    required={accessKind === "profile"}
                  />
                )}
                {accessKind === "master" ? (
                  <span className="text-[11px] text-muted-foreground">
                    Master card will be saved as an area-allocated general card
                    entry (intended for use within this area only).
                  </span>
                ) : null}
              </label>

              {accessKind === "profile" ? (
                <label className="grid gap-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    Phone (optional)
                  </span>
                  <Input
                    value={form.phone}
                    onChange={(event) =>
                      setForm({ ...form, phone: event.target.value })
                    }
                    placeholder="+92 300 1234567"
                    className="h-9 text-sm"
                    disabled={saving}
                  />
                </label>
              ) : (
                <div className="grid gap-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    Phone
                  </span>
                  <p className="flex h-9 items-center rounded-md border border-dashed px-3 text-xs text-muted-foreground">
                    Not required for shared/general cards
                  </p>
                </div>
              )}

              <label className="grid gap-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Operational role
                </span>
                <Select
                  value={form.roleId}
                  onValueChange={(value) =>
                    value && setForm({ ...form, roleId: value })
                  }
                  disabled={saving || roles.length === 0}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    {roles.map((role) => (
                      <SelectItem key={role.id} value={String(role.id)}>
                        {role.name} ({role.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
            </div>

            <div className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
              {accessKind === "profile"
                ? "Individual profiles can have their own card. After adding the profile, assign a personal card to this user."
                : accessKind === "shared_staff"
                  ? "Create one shared entry for staff and assign a single card to it. This card can be used as the shared staff card."
                  : accessKind === "general"
                    ? "Create a general access entry for walk-in/general users and assign a general card to it (no personal profile required)."
                    : "Create a master/general card entry allocated to an area. Assign the master card to this entry; it is intended for use within the allocated area only."}
            </div>

            <DialogFooter>
              <Button
                type="submit"
                size="sm"
                disabled={
                  saving ||
                  !form.roleId ||
                  (accessKind === "profile"
                    ? !form.name.trim()
                    : accessKind === "master"
                      ? !form.area.trim()
                      : !form.name.trim())
                }
              >
                {saving ? (
                  <>
                    <Loader2 aria-hidden className="animate-spin" />
                    Adding…
                  </>
                ) : accessKind === "profile" ? (
                  "Add profile"
                ) : (
                  "Add access entry"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={cardUser !== null}
        onOpenChange={(open) => {
          if (!open) setCardUser(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Assign card</DialogTitle>
            <DialogDescription>
              {cardUser?.name}
              {selectedStation ? ` · ${selectedStation.name}` : ""}
            </DialogDescription>
          </DialogHeader>
          {cardUser && selectedStation && cardDevice ? (
            <AssignCard
              stationId={selectedStation.id}
              userId={cardUser.id}
              userName={cardUser.name}
              deviceId={cardDevice.id}
              onDone={() => {
                setCardUser(null);
                setReloadKey((key) => key + 1);
              }}
              onCancel={() => setCardUser(null)}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              This station has no controller assigned, so a card cannot be
              enrolled.
            </p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export { PeopleCardsView };
