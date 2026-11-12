"use client";

import * as React from "react";
import { usePathname } from "next/navigation";

import { NAV } from "@/common/sidebar";
import { DeviceStatus } from "@/common/device-status";
import { ThemeToggle } from "@/common/theme-toggle";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

const subscribeToday = () => () => {};

function Header() {
  const pathname = usePathname();
  const section = NAV.flatMap((g) => g.items).find((item) =>
    pathname.startsWith(item.href)
  );
  // Read the clock after hydration only; prerendering must not bake in a date.
  const today = React.useSyncExternalStore(
    subscribeToday,
    () =>
      new Date().toLocaleDateString("en-GB", {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric",
      }),
    () => null
  );

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background/85 px-4 backdrop-blur">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-1 h-4" />
      <h1 className="text-sm font-medium">{section?.title ?? "Console"}</h1>
      <div className="ml-auto flex items-center gap-3">
        <DeviceStatus />
        {today ? (
          <p className="hidden font-mono text-xs text-muted-foreground sm:block">
            {today}
          </p>
        ) : null}
        <ThemeToggle />
      </div>
    </header>
  );
}

export { Header }
