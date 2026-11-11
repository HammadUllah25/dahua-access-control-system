import type { LucideIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type Kpi = {
  label: string
  value: string
  sub: string
  icon: LucideIcon
  delta?: { text: string; negative?: boolean }
}

function KpiCards({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi) => {
        const Icon = kpi.icon
        return (
          <Card key={kpi.label} size="sm">
            <CardHeader>
              <CardDescription>{kpi.label}</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums sm:text-3xl">
                {kpi.value}
              </CardTitle>
              {kpi.delta ? (
                <CardAction>
                  <Badge
                    variant={kpi.delta.negative ? "destructive" : "secondary"}
                  >
                    {kpi.delta.text}
                  </Badge>
                </CardAction>
              ) : null}
            </CardHeader>
            <CardFooter className="gap-2">
              <Icon aria-hidden className="size-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">{kpi.sub}</span>
            </CardFooter>
          </Card>
        )
      })}
    </div>
  )
}

export { KpiCards, type Kpi }
