"use client";

import { useRef } from "react";

// Six single-digit boxes with auto-advance, backspace and paste support.
// Value is a string of up to 6 digits (spaces mark skipped boxes).
function OtpInput({
  value,
  onChange,
  disabled,
  autoComplete = "one-time-code",
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  autoComplete?: string;
}) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);

  const digits = Array.from({ length: 6 }, (_, i) => value[i] ?? "");
  const code = value.replace(/ /g, "");
  const complete = /^\d{6}$/.test(code);

  const applyDigit = (index: number, digit: string) => {
    const chars = Array.from({ length: 6 }, (_, j) => value[j] ?? " ");
    chars[index] = digit || " ";
    onChange(chars.join("").replace(/ +$/, ""));
    if (digit && index < 5) refs.current[index + 1]?.focus();
  };

  const handleKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      e.preventDefault();
      applyDigit(index - 1, "");
      refs.current[index - 1]?.focus();
    }
    if (e.key === "ArrowLeft" && index > 0) refs.current[index - 1]?.focus();
    if (e.key === "ArrowRight" && index < 5) refs.current[index + 1]?.focus();
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (pasted) {
      onChange(pasted);
      refs.current[pasted.length - 1]?.focus();
    }
  };

  return (
    <div
      role="group"
      aria-label="6-digit verification code"
      className="flex justify-between gap-2"
    >
      {digits.map((digit, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          value={digit}
          onChange={(e) => applyDigit(i, e.target.value.replace(/\D/g, "").slice(-1))}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
          type="text"
          inputMode="numeric"
          autoComplete={i === 0 ? autoComplete : "off"}
          autoFocus={i === 0}
          disabled={disabled}
          aria-label={`Digit ${i + 1}`}
          className={`h-12 w-full rounded-lg border text-center font-mono text-lg font-medium tabular-nums transition-colors focus:outline-none focus:ring-[3px] focus:ring-ring/50 disabled:opacity-50 ${
            i === 5 && complete
              ? "border-primary/50 bg-primary/5"
              : "border-input bg-background"
          }`}
        />
      ))}
    </div>
  );
}

export { OtpInput };
