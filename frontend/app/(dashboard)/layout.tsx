import { Suspense } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AppSidebar } from "@/common/sidebar";
import { Header } from "@/common/header";
import { RoleGuard } from "@/components/role-guard";
import { RoleProvider } from "@/components/role-provider";
import { SidebarProvider } from "@/components/ui/sidebar";
import { DEFAULT_PERMISSIONS } from "@/lib/nav";
import {
  HIDDEN_COOKIE,
  PERMISSIONS_COOKIE,
  ROLE_COOKIE,
  USER_COOKIE,
  defaultUser,
  normalizeRole,
  parseHidden,
  parsePermissions,
  parseUser,
} from "@/lib/roles";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-svh items-center justify-center bg-background text-sm text-muted-foreground">
          Loading console…
        </div>
      }
    >
      <DashboardShell>{children}</DashboardShell>
    </Suspense>
  );
}

// The session cookie is read inside the Suspense boundary so Cache Components
// can keep the rest of the route out of the request path.
async function DashboardShell({ children }: { children: React.ReactNode }) {
  const store = await cookies();
  const role = normalizeRole(store.get(ROLE_COOKIE)?.value);
  if (!role) redirect("/login");
  const hidden = parseHidden(store.get(HIDDEN_COOKIE)?.value);
  const permissions =
    parsePermissions(store.get(PERMISSIONS_COOKIE)?.value) ??
    DEFAULT_PERMISSIONS;
  const user = parseUser(store.get(USER_COOKIE)?.value) ?? defaultUser(role);

  return (
    <RoleProvider
      role={role}
      hidden={hidden}
      permissions={permissions}
      user={user}
    >
      <SidebarProvider>
        <AppSidebar />
        <div className="relative flex min-w-0 flex-1 flex-col bg-background">
          <Header />
          <main className="relative isolate flex flex-1 flex-col">
            {/* ambient accent glow behind the page content */}
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
            >
              <div className="absolute -top-40 right-[-10%] size-[36rem] rounded-full bg-primary/10 blur-3xl" />
              <div className="absolute bottom-[-12rem] left-[-8rem] size-[30rem] rounded-full bg-primary/[0.06] blur-3xl" />
            </div>
            <RoleGuard>{children}</RoleGuard>
          </main>
        </div>
      </SidebarProvider>
    </RoleProvider>
  );
}
