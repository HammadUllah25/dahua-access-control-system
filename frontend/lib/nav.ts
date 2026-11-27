import {
  BarChart3,
  Bell,
  BellRing,
  Building2,
  CalendarClock,
  DoorOpen,
  LayoutDashboard,
  Plus,
  Radio,
  ScrollText,
  Settings,
  UserCog,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { PagePermissions, Role } from "@/lib/roles";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  roles: Role[];
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

const ALL: Role[] = ["superadmin", "admin", "branch"];
const ADMIN: Role[] = ["superadmin", "admin"];
const SUPER: Role[] = ["superadmin"];

export const NAV: NavGroup[] = [
  {
    label: "Operations",
    items: [
      { title: "Overview", href: "/overview", icon: LayoutDashboard, roles: ALL },
      { title: "Live Monitoring", href: "/live", icon: Radio, roles: ALL },
      { title: "Access Logs", href: "/logs", icon: ScrollText, roles: ALL },
      { title: "Notifications", href: "/notifications", icon: Bell, roles: ALL },
    ],
  },
  {
    label: "Network",
    items: [
      { title: "Stations", href: "/stations", icon: Building2, roles: ALL },
    ],
  },
  {
    label: "People & access",
    items: [
      { title: "Users & Roles", href: "/users", icon: UserCog, roles: SUPER },
      { title: "People & Cards", href: "/people", icon: Users, roles: ADMIN },
      {
        title: "Access Schedules",
        href: "/schedules",
        icon: CalendarClock,
        roles: ADMIN,
      },
    ],
  },
  {
    label: "Station",
    items: [
      { title: "Door & Sensor", href: "/device", icon: DoorOpen, roles: ALL },
      { title: "Add Device", href: "/add-device", icon: Plus, roles: ADMIN },
      { title: "Alerts & Events", href: "/alerts", icon: BellRing, roles: ALL },
    ],
  },
  {
    label: "Insights",
    items: [
      { title: "Reports", href: "/reports", icon: BarChart3, roles: ALL },
      { title: "Settings", href: "/settings", icon: Settings, roles: ALL },
    ],
  },
];

// Core pages stay available to every role so dashboard links never dead-end.
const CORE_PAGES = ["/overview", "/settings", "/stations", "/logs", "/device"];

const TOGGLEABLE_PAGES = [
  "/live",
  "/people",
  "/schedules",
  "/add-device",
  "/alerts",
  "/notifications",
  "/reports",
];

function toggleableForRole(role: "admin" | "branch"): string[] {
  return NAV.flatMap((group) => group.items)
    .filter(
      (item) =>
        item.roles.includes(role) && TOGGLEABLE_PAGES.includes(item.href)
    )
    .map((item) => item.href);
}

export const DEFAULT_PERMISSIONS: PagePermissions = {
  admin: toggleableForRole("admin"),
  branch: toggleableForRole("branch"),
};

function allows(role: Role, href: string, permissions: PagePermissions) {
  if (role === "superadmin") return true;
  if (CORE_PAGES.includes(href)) return true;
  return permissions[role].includes(href);
}

export function navForRole(
  role: Role,
  hidden: string[] = [],
  permissions: PagePermissions = DEFAULT_PERMISSIONS
): NavGroup[] {
  return NAV.map((group) => ({
    ...group,
    items: group.items.filter(
      (item) =>
        item.roles.includes(role) &&
        allows(role, item.href, permissions) &&
        !hidden.includes(item.href)
    ),
  })).filter((group) => group.items.length > 0);
}

export function canAccessPath(
  role: Role,
  pathname: string,
  hidden: string[] = [],
  permissions: PagePermissions = DEFAULT_PERMISSIONS
): boolean {
  return NAV.some((group) =>
    group.items.some(
      (item) =>
        item.roles.includes(role) &&
        allows(role, item.href, permissions) &&
        !hidden.includes(item.href) &&
        (pathname === item.href || pathname.startsWith(`${item.href}/`))
    )
  );
}

export function customisableModules(): NavItem[] {
  return NAV.flatMap((group) => group.items).filter(
    (item) => !CORE_PAGES.includes(item.href) && item.href !== "/users"
  );
}

export function permissionModules(): NavItem[] {
  return NAV.flatMap((group) => group.items).filter((item) =>
    TOGGLEABLE_PAGES.includes(item.href)
  );
}
