import { Panel } from "@/components/dashboard/panel";
import { SITE_DEVICES, STATION, type SiteDevice } from "@/lib/station-data";

// Keyless Google Maps embed, tinted with CSS so it sits inside the dashboard
// palette instead of Google's default colours.
// shortcut: reader markers are a percentage overlay, so they stay put while the
// map pans/zooms. A keyed Maps JS API is needed for anchored markers and exact
// per-feature map styling.
const MAP_SRC = `https://maps.google.com/maps?q=${STATION.lat},${STATION.lng}&z=16&output=embed`;

const TONE: Record<
  SiteDevice["status"],
  { dot: string; text: string; label: string }
> = {
  online: { dot: "bg-led-green", text: "text-led-green", label: "Online" },
  offline: { dot: "bg-led-red", text: "text-led-red", label: "Offline" },
  pending: { dot: "bg-led-amber", text: "text-led-amber", label: "Pending" },
};

// Static station map for the Overview. Markers pulse so installed readers are
// easy to spot; status is also written out so colour is never the only signal.
function StationMap() {
  return (
    <Panel
      title="Station map"
      description="Installed access readers at the station · Google Maps"
      action={
        <span className="text-xs font-medium text-muted-foreground">
          {SITE_DEVICES.length} access points
        </span>
      }
    >
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="relative h-72 overflow-hidden rounded-lg border sm:h-80 lg:col-span-2 lg:h-[420px]">
          <iframe
            title="Station location on Google Maps"
            src={MAP_SRC}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            className="absolute inset-0 h-full w-full border-0 grayscale sepia-[0.3] contrast-[0.95] dark:invert dark:hue-rotate-180 dark:brightness-90 dark:contrast-90 dark:saturate-50"
          />
          {/* amber tint + soft edges so the map reads as part of the card */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-primary/10 mix-blend-multiply"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-t from-background/40 via-transparent to-background/20"
          />

          {SITE_DEVICES.map((device) => {
            const tone = TONE[device.status];
            return (
              <div
                key={device.id}
                className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${device.x}%`, top: `${device.y}%` }}
              >
                <span
                  className="relative flex size-4 items-center justify-center"
                  title={`${device.name} — ${tone.label}`}
                >
                  <span
                    aria-hidden
                    className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 motion-reduce:animate-none ${tone.dot}`}
                  />
                  <span
                    className={`relative inline-flex size-4 rounded-full ring-2 ring-background ${tone.dot}`}
                  />
                </span>
                <span className="absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded bg-background/90 px-1.5 py-0.5 text-[10px] font-medium shadow-sm ring-1 ring-border">
                  {device.name.split(" · ")[0]}
                </span>
              </div>
            );
          })}
        </div>

        <ul className="grid gap-2 sm:grid-cols-3 lg:grid-cols-1 lg:content-start">
          {SITE_DEVICES.map((device) => {
            const tone = TONE[device.status];
            return (
              <li
                key={device.id}
                className="flex items-start gap-2 rounded-lg border bg-background/40 px-3 py-2"
              >
                <span className="relative mt-1 flex size-2.5 shrink-0">
                  <span
                    aria-hidden
                    className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 motion-reduce:animate-none ${tone.dot}`}
                  />
                  <span
                    className={`relative inline-flex size-2.5 rounded-full ${tone.dot}`}
                  />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium">{device.name}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {device.location} · {device.model}
                  </p>
                  <p className={`text-[11px] font-medium ${tone.text}`}>
                    {tone.label}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </Panel>
  );
}

export { StationMap };
