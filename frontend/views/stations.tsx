"use client";

import { Building2, CircleCheck, Cpu, XCircle } from "lucide-react";

import { Panel } from "@/components/dashboard/panel";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { ToneBadge } from "@/components/dashboard/badges";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSession } from "@/components/role-provider";
import { ROLE_META, roleScopeLabel, stationsForRole } from "@/lib/roles";

const STATUS_TONE = {
  online: "green",
  offline: "red",
  pending: "amber",
} as const;

const STATUS_LABEL = {
  online: "Online",
  offline: "Offline",
  pending: "Pending",
} as const;

function StationsView() {
  const { role } = useSession();
  const meta = ROLE_META[role];
  const stations = stationsForRole(role);
  const online = stations.filter((station) => station.status === "online").length;
  const offline = stations.filter((station) => station.status === "offline").length;
  const pending = stations.filter((station) => station.status === "pending").length;
  const devices = stations.reduce((total, station) => total + station.devices, 0);

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Stations</h2>
          <p className="text-xs text-muted-foreground">
            {meta.label} view · {roleScopeLabel(role)}
          </p>
        </div>
        <Badge variant="outline">{meta.label}</Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Stations"
          value={stations.length}
          hint={roleScopeLabel(role)}
          icon={Building2}
          tone="violet"
        />
        <KpiCard
          label="Online"
          value={online}
          hint="Controllers reachable"
          icon={CircleCheck}
          tone="green"
        />
        <KpiCard
          label="Offline"
          value={offline}
          hint="Needs attention"
          icon={XCircle}
          tone="red"
        />
        <KpiCard
          label="Devices"
          value={devices}
          hint={`${pending} station(s) pending setup`}
          icon={Cpu}
          tone="amber"
        />
      </div>

      <Panel
        title="Station monitoring"
        description={`Every station in ${meta.workspace} · controller health and reader count`}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Station</TableHead>
              <TableHead>Area</TableHead>
              <TableHead>Branch</TableHead>
              <TableHead>Devices</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last seen</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stations.map((station) => (
              <TableRow key={station.id}>
                <TableCell className="font-medium">
                  {station.name}
                  <span className="block font-mono text-[11px] text-muted-foreground">
                    {station.id}
                  </span>
                </TableCell>
                <TableCell>{station.area}</TableCell>
                <TableCell>{station.branch}</TableCell>
                <TableCell className="tabular-nums">{station.devices}</TableCell>
                <TableCell>
                  <ToneBadge tone={STATUS_TONE[station.status]}>
                    {STATUS_LABEL[station.status]}
                  </ToneBadge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {station.lastSeen}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>
    </div>
  );
}

export { StationsView };
