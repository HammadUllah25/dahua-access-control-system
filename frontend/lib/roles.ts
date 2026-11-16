import { NETWORK_STATIONS, type NetworkStation } from "@/lib/station-data";

// shortcut: this demo derives the role from the password text and stores it in
// a client-readable cookie. Replace with a server session when auth lands.
export type Role = "superadmin" | "admin" | "branch";

export type PagePermissions = { admin: string[]; branch: string[] };

export type SessionUser = { name: string; email: string };

export const ROLE_COOKIE = "washroom_role";
export const HIDDEN_COOKIE = "washroom_hidden";
export const PERMISSIONS_COOKIE = "washroom_permissions";
export const USER_COOKIE = "washroom_user";

const COOKIE_MAX_AGE = 60 * 60 * 24 * 7;
// Core monitoring pages stay reachable so dashboard links never dead-end.
const ALWAYS_VISIBLE = [
  "/overview",
  "/settings",
  "/stations",
  "/logs",
  "/device",
  "/users",
];

export const ROLE_META: Record<
  Role,
  {
    label: string;
    workspace: string;
    subtitle: string;
    commandCentre: string;
    scope: string;
    description: string;
  }
> = {
  superadmin: {
    label: "Super Admin",
    workspace: "FuelCo Network",
    subtitle: "Super Admin · all areas",
    commandCentre: "Network command centre",
    scope: "All areas · all stations",
    description:
      "Monitors every area, station and device, and controls the dashboard modules.",
  },
  admin: {
    label: "Admin",
    workspace: "Area A",
    subtitle: "Admin · area monitoring",
    commandCentre: "Area command centre",
    scope: "Area A · area and station monitoring",
    description:
      "Monitors Area A and its stations with every station feature.",
  },
  branch: {
    label: "Branch",
    workspace: "Branch 04",
    subtitle: "Branch · station monitoring",
    commandCentre: "Branch command centre",
    scope: "Branch 04 · all branch stations",
    description: "Monitors every station in Branch 04.",
  },
};

export function roleFromPassword(password: string): Role {
  const value = password.trim().toLowerCase();
  if (value.includes("super")) return "superadmin";
  if (value.includes("admin")) return "admin";
  return "branch";
}

export function normalizeRole(value?: string | null): Role | null {
  return value === "superadmin" || value === "admin" || value === "branch"
    ? value
    : null;
}

export function stationsForRole(role: Role): NetworkStation[] {
  if (role === "superadmin") return NETWORK_STATIONS;
  if (role === "admin") {
    return NETWORK_STATIONS.filter((station) => station.area === "Area A");
  }
  return NETWORK_STATIONS.filter((station) => station.branch === "Branch 04");
}

export function roleScopeLabel(role: Role): string {
  const count = stationsForRole(role).length;
  if (role === "superadmin") return `All areas · ${count} stations`;
  if (role === "admin") return `Area A · ${count} stations`;
  return `Branch 04 · ${count} stations`;
}

export function setRoleCookie(role: Role) {
  document.cookie = `${ROLE_COOKIE}=${role}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
}

export function clearRoleCookie() {
  document.cookie = `${ROLE_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

export function setHiddenModulesCookie(hidden: string[]) {
  // Delete the cookie when nothing is hidden so a reset survives every browser.
  const value = hidden.length ? encodeURIComponent(hidden.join(",")) : "";
  const maxAge = hidden.length ? COOKIE_MAX_AGE : 0;
  document.cookie = `${HIDDEN_COOKIE}=${value}; path=/; max-age=${maxAge}; samesite=lax`;
}

export function parseHidden(value?: string | null): string[] {
  if (!value) return [];
  try {
    return decodeURIComponent(value)
      .split(",")
      .filter((href) => href && !ALWAYS_VISIBLE.includes(href));
  } catch {
    return [];
  }
}

export function defaultUser(role: Role, email?: string): SessionUser {
  if (role === "superadmin") {
    return { name: "A. Rahman", email: email ?? "a.rahman@fuelco.example" };
  }
  if (role === "admin") {
    return { name: "S. Khan", email: email ?? "s.khan@fuelco.example" };
  }
  return { name: "M. Ali", email: email ?? "m.ali@fuelco.example" };
}

export function setPermissionsCookie(permissions: PagePermissions) {
  const value = encodeURIComponent(JSON.stringify(permissions));
  document.cookie = `${PERMISSIONS_COOKIE}=${value}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
}

export function parsePermissions(value?: string | null): PagePermissions | null {
  if (!value) return null;
  try {
    const parsed = JSON.parse(decodeURIComponent(value)) as Partial<PagePermissions>;
    if (!Array.isArray(parsed.admin) || !Array.isArray(parsed.branch)) return null;
    return {
      admin: parsed.admin.filter((href): href is string => typeof href === "string"),
      branch: parsed.branch.filter((href): href is string => typeof href === "string"),
    };
  } catch {
    return null;
  }
}

export function setUserCookie(user: SessionUser) {
  const value = encodeURIComponent(JSON.stringify(user));
  document.cookie = `${USER_COOKIE}=${value}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
}

export function clearUserCookie() {
  document.cookie = `${USER_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

export function parseUser(value?: string | null): SessionUser | null {
  if (!value) return null;
  try {
    const parsed = JSON.parse(decodeURIComponent(value)) as Partial<SessionUser>;
    if (typeof parsed.name !== "string" || typeof parsed.email !== "string") {
      return null;
    }
    return { name: parsed.name, email: parsed.email };
  } catch {
    return null;
  }
}
