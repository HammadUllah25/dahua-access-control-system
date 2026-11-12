import Link from "next/link";
import { ScanLine } from "lucide-react";

// Onboarding has its own chrome: it is station setup, not an auth screen,
// so the constant auth brand panel must not appear here.
export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border/60 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground [&_svg]:size-4">
            <ScanLine aria-hidden />
          </span>
          <span className="text-sm font-semibold tracking-tight">
            Washroom Access
          </span>
        </Link>
        <span className="ml-auto text-xs font-medium text-muted-foreground">
          Station setup
        </span>
      </header>
      <main className="flex flex-1 justify-center px-4 py-8 sm:px-6 sm:py-12">
        {children}
      </main>
    </div>
  );
}
