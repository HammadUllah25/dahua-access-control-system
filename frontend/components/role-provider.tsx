"use client";

import { createContext, useContext } from "react";

import { DEFAULT_PERMISSIONS } from "@/lib/nav";
import type { PagePermissions, Role, SessionUser } from "@/lib/roles";

type Session = {
  role: Role;
  hidden: string[];
  permissions: PagePermissions;
  user: SessionUser;
};

const SessionContext = createContext<Session>({
  role: "branch",
  hidden: [],
  permissions: DEFAULT_PERMISSIONS,
  user: { name: "M. Ali", email: "m.ali@fuelco.example" },
});

function RoleProvider({
  role,
  hidden,
  permissions,
  user,
  children,
}: {
  role: Role;
  hidden: string[];
  permissions: PagePermissions;
  user: SessionUser;
  children: React.ReactNode;
}) {
  return (
    <SessionContext.Provider value={{ role, hidden, permissions, user }}>
      {children}
    </SessionContext.Provider>
  );
}

function useSession() {
  return useContext(SessionContext);
}

export { RoleProvider, useSession };
