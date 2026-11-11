import { Led, type LedStatus } from "@/common/led";
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type WashroomDevice = {
  id: number;
  name: string;
  location: string;
  model: string;
  host: string;
  status: LedStatus;
  cards: number;
  entriesToday: number;
  lastSeen: string;
};

const STATUS_LABEL: Record<LedStatus, string> = {
  online: "Online",
  pending: "Pending",
  offline: "Offline",
};

function WashroomRack({ devices }: { devices: WashroomDevice[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Washrooms</CardTitle>
        <CardDescription>
          Controllers installed at each washroom, with live connection status
        </CardDescription>
        <CardAction>
          <span className="font-mono text-xs text-muted-foreground">
            {devices.length} registered
          </span>
        </CardAction>
      </CardHeader>
      <ul className="divide-y border-t border-border">
        {devices.map((device) => (
          <li
            key={device.id}
            className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/40"
          >
            <Led status={device.status} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{device.name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {device.location}
              </p>
            </div>
            <p className="hidden truncate font-mono text-xs text-muted-foreground md:block md:w-44">
              {device.host}
            </p>
            <div className="hidden text-right text-xs text-muted-foreground sm:block">
              <p className="font-medium tabular-nums">{device.cards} cards</p>
              <p className="tabular-nums">{device.entriesToday} entries today</p>
            </div>
            <div className="w-24 shrink-0 text-right">
              <p className="text-xs font-medium">
                {STATUS_LABEL[device.status]}
              </p>
              <p className="text-xs text-muted-foreground">{device.lastSeen}</p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export { WashroomRack, type WashroomDevice };
