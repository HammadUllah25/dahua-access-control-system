import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

type Tone = "green" | "red" | "amber" | "violet" | "muted";

const ICON_TONE: Record<Tone, string> = {
  green: "text-led-green",
  red: "text-led-red",
  amber: "text-led-amber",
  violet: "text-primary",
  muted: "text-muted-foreground",
};

function KpiCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "muted",
  href,
}: {
  label: string;
  value: string | number;
  hint?: React.ReactNode;
  icon: LucideIcon;
  tone?: Tone;
  href?: string;
}) {
  const body = (
    <Card size="sm" className="gap-0 transition-colors hover:bg-muted/40">
      <CardContent className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-1 truncate text-2xl font-semibold tabular-nums tracking-tight">
            {value}
          </p>
          {hint ? (
            <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
          ) : null}
        </div>
        <Icon aria-hidden className={`size-5 shrink-0 ${ICON_TONE[tone]}`} />
      </CardContent>
    </Card>
  );
  if (!href) return body;
  return (
    <Link
      href={href}
      className="focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 rounded-xl"
    >
      {body}
    </Link>
  );
}

export { KpiCard };
