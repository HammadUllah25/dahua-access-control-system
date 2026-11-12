import { CheckCircle2, CircleHelp, TriangleAlert, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";

// Blueprint rule: never colour alone — every badge carries icon + text label.
type Tone = "green" | "red" | "amber" | "grey";

const TONES: Record<Tone, string> = {
  green: "border-led-green/25 bg-led-green/10 text-led-green",
  red: "border-led-red/25 bg-led-red/10 text-led-red",
  amber: "border-led-amber/25 bg-led-amber/10 text-led-amber",
  grey: "border-border bg-muted text-muted-foreground",
};

const ICONS: Record<Tone, typeof CheckCircle2> = {
  green: CheckCircle2,
  red: XCircle,
  amber: TriangleAlert,
  grey: CircleHelp,
};

function ToneBadge({
  tone,
  children,
}: {
  tone: Tone;
  children: React.ReactNode;
}) {
  const Icon = ICONS[tone];
  return (
    <Badge variant="outline" className={TONES[tone]}>
      <Icon aria-hidden />
      {children}
    </Badge>
  );
}

function ResultBadge({ result }: { result: "Granted" | "Denied" }) {
  return (
    <ToneBadge tone={result === "Granted" ? "green" : "red"}>{result}</ToneBadge>
  );
}

const SEVERITY_TONE = {
  Critical: "red",
  Warning: "amber",
  Info: "grey",
} as const;

function SeverityBadge({ severity }: { severity: "Critical" | "Warning" | "Info" }) {
  return <ToneBadge tone={SEVERITY_TONE[severity]}>{severity}</ToneBadge>;
}

export { ToneBadge, ResultBadge, SeverityBadge };
