"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Nfc, Plus, Search } from "lucide-react";
import { toast } from "react-toastify";

import { Panel } from "@/components/dashboard/panel";
import { ToneBadge } from "@/components/dashboard/badges";
import { AssignCard } from "@/components/cards/assign-card";
import { Button } from "@/components/ui/button";
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
  const [form, setForm] = useState({ name: "", phone: "", roleId: "" });
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
  const preferredRole =
    roles.find((role) => role.code === "CUSTOMER") ?? roles[0];

  const q = query.trim().toLowerCase();
  const filtered = users.filter((user) => {
    if (roleFilter !== "all" && String(user.role.id) !== roleFilter) {
      return false;
    }
    if (!q) return true;
    return (
      user.name.toLowerCase().includes(q) ||
      (user.phone?.toLowerCase().includes(q) ?? false) ||
      (user.active_card?.card_number.toLowerCase().includes(q) ?? false)
    );
  });

  const activeCards = users.filter((user) => user.active_card).length;
  const withoutCards = users.length - activeCards;

  const openAdd = () => {
    if (!selectedStation) return;
    setForm({
      name: "",
      phone: "",
      roleId: preferredRole ? String(preferredRole.id) : "",
    });
    setAddOpen(true);
  };

  const createUser = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedStation || !form.name.trim() || !form.roleId) return;
    setSaving(true);
    try {
      const res = await createStationUserAction(selectedStation.id, {
        name: form.name.trim(),
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

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            People &amp; cards
          </h2>
          <p className="text-xs text-muted-foreground">
            Station people and the physical card credentials assigned to them
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {stations.length > 0 ? (
            <Select value={stationId} onValueChange={(value) => value && setStationId(value)}>
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
                ? "Add a person to this station"
                : !hasStation
                  ? "Create a station before adding people"
                  : usersLoading
                    ? "Loading station roles"
                    : "No operational roles available"
            }
            className="disabled:cursor-not-allowed disabled:pointer-events-auto"
          >
            <Plus aria-hidden />
            Add user
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
          ["Total people", users.length],
          ["Cards assigned", activeCards],
          ["No card", withoutCards],
          ["Roles", roles.length],
        ].map(([label, value]) => (
          <div key={label} className="card-glow rounded-lg border bg-card px-3 py-2">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-xl font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      <Panel
        title="Station directory"
        description={
          selectedStation
            ? `${selectedStation.name} · ${users.length} person(s)`
            : "Select a station to see its people"
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
              placeholder="Search name, phone or card number"
              className="h-8 pl-8 text-xs"
            />
          </div>
          <Select value={roleFilter} onValueChange={(value) => value && setRoleFilter(value)}>
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
              <TableHead>Person</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Phone</TableHead>
              <TableHead>Card</TableHead>
              <TableHead>Validity</TableHead>
              <TableHead>Card status</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((user) => {
              const card = user.active_card;
              const canAssign = Boolean(cardDevice) && !card;
              return (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">
                    {user.name}
                    <span className="block font-mono text-[11px] text-muted-foreground">
                      #{user.id}
                    </span>
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
                          ? "This person already has a card on record"
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
              ? "No people match the current filters."
              : "Create a station before adding people."}
          </p>
        ) : null}
      </Panel>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Add user</DialogTitle>
            <DialogDescription>
              {selectedStation
                ? `${selectedStation.name} · this person is not a dashboard login.`
                : "Create a station first."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={createUser} className="grid gap-3">
            <label className="grid gap-1">
              <span className="text-xs font-medium text-muted-foreground">
                Full name
              </span>
              <Input
                value={form.name}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
                placeholder="Full name"
                className="h-8 text-xs"
                disabled={saving}
                required
              />
            </label>
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
                className="h-8 text-xs"
                disabled={saving}
              />
            </label>
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
            <DialogFooter>
              <Button
                type="submit"
                size="sm"
                disabled={saving || !form.name.trim() || !form.roleId}
              >
                {saving ? (
                  <>
                    <Loader2 aria-hidden className="animate-spin" />
                    Adding…
                  </>
                ) : (
                  "Add user"
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
