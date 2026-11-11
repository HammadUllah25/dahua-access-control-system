"use client"

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type TrafficPoint = {
  time: string
  granted: number
  denied: number
}

const tooltipStyle = {
  background: "var(--popover)",
  border: "none",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
  color: "var(--popover-foreground)",
  fontSize: "0.75rem",
} as const

function TrafficChart({ data }: { data: TrafficPoint[] }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Washroom traffic</CardTitle>
        <CardDescription>
          Card reads per hour today, granted vs denied
        </CardDescription>
        <CardAction>
          <span className="font-mono text-xs text-muted-foreground">
            07:00 to 19:00
          </span>
        </CardAction>
      </CardHeader>
      <CardContent className="px-2 pt-0 sm:px-4">
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 8, left: 0 }}>
              <defs>
                <linearGradient id="fillGranted" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="var(--chart-1)"
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="95%"
                    stopColor="var(--chart-1)"
                    stopOpacity={0.1}
                  />
                </linearGradient>
                <linearGradient id="fillDenied" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="var(--chart-3)"
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="95%"
                    stopColor="var(--chart-3)"
                    stopOpacity={0.1}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="time"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              />
              <YAxis
                width={28}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ stroke: "var(--border)" }}
              />
              <Area
                dataKey="granted"
                type="monotone"
                stackId="a"
                stroke="var(--chart-1)"
                strokeWidth={2}
                fill="url(#fillGranted)"
                name="Granted"
              />
              <Area
                dataKey="denied"
                type="monotone"
                stackId="a"
                stroke="var(--chart-3)"
                strokeWidth={2}
                fill="url(#fillDenied)"
                name="Denied"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center gap-4 px-2 pt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span
              aria-hidden
              className="size-2 rounded-[2px] bg-[var(--chart-1)]"
            />
            Granted
          </span>
          <span className="flex items-center gap-1.5">
            <span
              aria-hidden
              className="size-2 rounded-[2px] bg-[var(--chart-3)]"
            />
            Denied
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export { TrafficChart, type TrafficPoint }
