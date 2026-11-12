import { DoorOpen, ScanLine, ShieldCheck } from "lucide-react";

// Constant left-side brand panel shown across all auth pages
// (login → signup → OTP → reset) until the dashboard is reached.
function AuthBrandPanel() {
  return (
    <aside
      aria-hidden
      className="relative hidden flex-col justify-between overflow-hidden bg-primary p-10 text-primary-foreground lg:flex"
    >
      {/* decorative layers */}
      <div className="absolute -right-24 -top-24 size-96 rounded-full bg-white/10 blur-3xl" />
      <div className="absolute -bottom-32 -left-16 size-96 rounded-full bg-black/10 blur-3xl" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.14)_1px,transparent_0)] bg-[size:22px_22px]" />

      <div className="relative flex items-center gap-3">
        <span className="flex size-10 items-center justify-center rounded-lg bg-white/15 [&_svg]:size-5">
          <ScanLine />
        </span>
        <div className="grid leading-tight">
          <span className="text-base font-semibold tracking-tight">Washroom Access</span>
          <span className="text-xs text-primary-foreground/70">Station Admin Console</span>
        </div>
      </div>

      <div className="relative max-w-md space-y-8">
        <div className="space-y-3">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            One station. Every door. Full audit trail.
          </h2>
          <p className="text-sm leading-relaxed text-primary-foreground/80">
            Card access, people and credentials, live door events and access
            schedules for the washroom access controller.
          </p>
        </div>

        {/* mock live event preview */}
        <div className="rounded-xl border border-white/20 bg-white/10 p-4 backdrop-blur">
          <p className="mb-3 text-xs font-medium uppercase tracking-wider text-primary-foreground/60">
            Live at the reader
          </p>
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="flex items-center gap-2 font-medium">
              <span className="size-2 rounded-full bg-white shadow-[0_0_8px_-1px_currentColor] motion-safe:animate-pulse" />
              Granted · A. Rahman
            </span>
            <span className="font-mono text-xs text-primary-foreground/70">17:59</span>
          </div>
          <p className="mt-1 font-mono text-xs text-primary-foreground/60">
            0142 ···· 8871 · Washroom Entry · Reader 1
          </p>
        </div>

        <ul className="space-y-3 text-sm">
          {[
            { icon: DoorOpen, text: "Live door & controller status" },
            { icon: ScanLine, text: "MIFARE card credential management" },
            { icon: ShieldCheck, text: "Complete access audit trail" },
          ].map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-center gap-3">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/15 [&_svg]:size-4">
                <Icon />
              </span>
              {text}
            </li>
          ))}
        </ul>
      </div>

      <p className="relative font-mono text-xs text-primary-foreground/50">
        DHI-ASI1201E · NetSDK 3.060 · PumpStation 04
      </p>
    </aside>
  );
}

export { AuthBrandPanel };
