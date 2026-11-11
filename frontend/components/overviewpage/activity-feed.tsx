import {
  CircleAlert,
  CircleCheck,
  UserRoundPlus,
  type LucideIcon,
} from "lucide-react"

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type FeedItem = {
  time: string
  text: string
  kind: "success" | "error" | "person"
}

const KIND_ICON: Record<FeedItem["kind"], LucideIcon> = {
  success: CircleCheck,
  error: CircleAlert,
  person: UserRoundPlus,
}

const KIND_ICON_CLASS: Record<FeedItem["kind"], string> = {
  success: "text-led-green",
  error: "text-led-red",
  person: "text-muted-foreground",
}

function ActivityFeed({ items }: { items: FeedItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent activity</CardTitle>
        <CardDescription>Sync and enrollment events from today</CardDescription>
      </CardHeader>
      <ul className="flex flex-col divide-y border-t border-border">
        {items.map((item) => {
          const Icon = KIND_ICON[item.kind]
          return (
            <li key={item.time + item.text} className="flex gap-3 px-4 py-3">
              <Icon
                aria-hidden
                className={`mt-0.5 size-4 shrink-0 ${KIND_ICON_CLASS[item.kind]}`}
              />
              <p className="min-w-0 flex-1 text-sm leading-snug">
                {item.text}
              </p>
              <time className="font-mono text-xs text-muted-foreground">
                {item.time}
              </time>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

export { ActivityFeed, type FeedItem }
