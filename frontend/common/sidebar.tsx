"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ScanLine } from "lucide-react"

import { Led } from "@/common/led"
import { useSession } from "@/components/role-provider"
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
import { navForRole } from "@/lib/nav"
import { ROLE_META } from "@/lib/roles"

function AppSidebar() {
  const pathname = usePathname()
  const { role, hidden, permissions } = useSession()
  const meta = ROLE_META[role]
  const nav = navForRole(role, hidden, permissions)

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2.5 px-1 py-1.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground [&_svg]:size-4">
            <ScanLine aria-hidden />
          </span>
          <div className="grid leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold tracking-tight">
              {meta.workspace}
            </span>
            <span className="text-xs text-sidebar-foreground/60">
              {meta.subtitle}
            </span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {nav.map((group) => (
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
            {meta.label} · {meta.scope}
          </p>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}

export { AppSidebar }
