import { cn } from "cn"

const LED_STYLES = {
  online:
    "bg-led-green text-led-green shadow-[0_0_8px_-1px_currentColor] animate-led-pulse motion-reduce:animate-none",
  pending: "bg-led-amber text-led-amber",
  offline: "bg-led-red text-led-red",
} as const

export type LedStatus = keyof typeof LED_STYLES

function Led({
  status,
  className,
}: {
  status: LedStatus
  className?: string
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block size-2 shrink-0 rounded-full",
        LED_STYLES[status],
        className
      )}
    />
  )
}

export { Led }
