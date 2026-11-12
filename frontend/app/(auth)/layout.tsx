import { ScanLine } from "lucide-react";

import { AuthBrandPanel } from "@/components/auth/auth-brand-panel";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      {/* constant left-side brand panel — visible until the dashboard */}
      <AuthBrandPanel />
      <main className="flex items-center justify-center bg-background p-6 sm:p-10">
        {/* forms size themselves (max-w-sm) */}
        <div className="w-full">
          {/* compact brand row for small screens where the panel is hidden */}
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground [&_svg]:size-4">
              <ScanLine aria-hidden />
            </span>
            <span className="text-sm font-semibold tracking-tight">
              Washroom Access
            </span>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
