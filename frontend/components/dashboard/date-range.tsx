"use client";

import type { RangeKey } from "@/lib/station-data";

const OPTIONS: { key: RangeKey; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "7d", label: "7 days" },
  { key: "30d", label: "30 days" },
];

function DateRange({
  value,
  onChange,
}: {
  value: RangeKey;
  onChange: (range: RangeKey) => void;
}) {
  return (
    <div
      role="group"
      aria-label="Date range"
      className="inline-flex rounded-lg bg-muted p-0.5"
    >
      {OPTIONS.map((option) => (
        <button
          key={option.key}
          type="button"
          aria-pressed={value === option.key}
          onClick={() => onChange(option.key)}
          className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
            value === option.key
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export { DateRange };
