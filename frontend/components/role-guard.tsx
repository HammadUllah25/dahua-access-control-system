"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useSession } from "@/components/role-provider";
import { canAccessPath } from "@/lib/nav";

function RoleGuard({ children }: { children: React.ReactNode }) {
  const { role, hidden, permissions } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const allowed = canAccessPath(role, pathname, hidden, permissions);

  useEffect(() => {
    if (!allowed) router.replace("/overview");
  }, [allowed, router]);

  if (!allowed) return null;
  return <>{children}</>;
}

export { RoleGuard };
