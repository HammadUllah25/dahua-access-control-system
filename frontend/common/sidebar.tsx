"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  BellRing,
  CalendarClock,
  DoorOpen,
  LayoutDashboard,
  Radio,
  ScrollText,
  ScanLine,
  Settings,
  Users,
} from "lucide-react"

import { Led } from "@/common/led"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

// Blueprint §2: the 9 station-admin pages, grouped for scanning
const NAV = [
  {
    label: "Operations",
    items: [
      { title: "Overview", href: "/overview", icon: LayoutDashboard },
      { title: "Live Monitoring", href: "/live", icon: Radio },
      { title: "Access Logs", href: "/logs", icon: ScrollText },
    ],
  },
  {
    label: "People & access",
    items: [
      { title: "People & Cards", href: "/people", icon: Users },
      { title: "Access Schedules", href: "/schedules", icon: CalendarClock },
    ],
  },
  {
    label: "Station",
    items: [
      { title: "Device & Door", href: "/device", icon: DoorOpen },
      { title: "Alerts & Events", href: "/alerts", icon: BellRing },
    ],
  },
  {
    label: "Insights",
    items: [
      { title: "Reports", href: "/reports", icon: BarChart3 },
      { title: "Settings", href: "/settings", icon: Settings },
    ],
  },
]

function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2.5 px-1 py-1.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground [&_svg]:size-4.5">
            <ScanLine aria-hidden />
          </span>
          <div className="grid leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold tracking-tight">
              PumpStation 04
            </span>
            <span className="text-xs text-sidebar-foreground/60">
              Washroom access · Station Admin
            </span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {NAV.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      isActive={pathname.startsWith(item.href)}
                      tooltip={item.title}
                      render={<Link href={item.href} />}
                    >
                      <item.icon aria-hidden />
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <div className="grid gap-1 px-2 py-1 leading-tight group-data-[collapsible=icon]:hidden">
          <div className="flex items-center gap-2 text-xs font-medium">
            <Led status="online" />
            Monitoring active
          </div>
          <p className="font-mono text-[0.6875rem] text-sidebar-foreground/50">
            DHI-ASI1201E · NetSDK 3.060
          </p>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}

export { AppSidebar, NAV }
