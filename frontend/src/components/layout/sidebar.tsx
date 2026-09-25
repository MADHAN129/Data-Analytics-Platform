"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  BarChart3,
  Database,
  FileBarChart,
  Home,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Users,
  FileText,
  Activity,
  MessageSquare,
  Sparkles,
  ChevronLeft,
  BookOpen,
  Code2,
} from "lucide-react"
import { useState } from "react"

interface NavItem {
  label: string
  icon: React.ReactNode
  href: string
  adminOnly?: boolean
}

const navItems: NavItem[] = [
  { label: "Home", icon: <Home className="h-4 w-4" />, href: "/dashboard" },
  { label: "Analytics", icon: <Sparkles className="h-4 w-4" />, href: "/dashboard/analytics" },
  { label: "Conversations", icon: <MessageSquare className="h-4 w-4" />, href: "/dashboard/conversations" },
  { label: "Templates", icon: <BookOpen className="h-4 w-4" />, href: "/dashboard/templates" },
  { label: "Dashboards", icon: <LayoutDashboard className="h-4 w-4" />, href: "/dashboard/dashboards" },
  { label: "Databases", icon: <Database className="h-4 w-4" />, href: "/dashboard/databases" },
  { label: "Reports", icon: <FileBarChart className="h-4 w-4" />, href: "/dashboard/reports" },
  { label: "Activity", icon: <Activity className="h-4 w-4" />, href: "/dashboard/activity" },
  { label: "API Docs", icon: <Code2 className="h-4 w-4" />, href: "/dashboard/api-docs" },
]

const adminItems: NavItem[] = [
  { label: "Users", icon: <Users className="h-4 w-4" />, href: "/admin/users", adminOnly: true },
  { label: "Roles", icon: <ShieldCheck className="h-4 w-4" />, href: "/admin/roles", adminOnly: true },
  { label: "Audit Logs", icon: <FileText className="h-4 w-4" />, href: "/admin/audit", adminOnly: true },
  { label: "Settings", icon: <Settings className="h-4 w-4" />, href: "/admin/settings", adminOnly: true },
]

interface SidebarProps {
  userRoles?: string[]
}

export function Sidebar({ userRoles }: SidebarProps) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const isAdmin = userRoles?.some((r) => r === "Admin" || r === "SuperAdmin")

  return (
    <aside
      className={cn(
        "flex flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex h-14 items-center border-b border-sidebar-border px-4">
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <BarChart3 className="h-4 w-4 text-primary-foreground" />
            </div>
            <span>Agentic AI</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className={cn("ml-auto h-8 w-8 text-sidebar-foreground", collapsed && "mx-auto")}
          onClick={() => setCollapsed(!collapsed)}
        >
          <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
        </Button>
      </div>

      <ScrollArea className="flex-1 px-3 py-2">
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <span
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  pathname === item.href && "bg-sidebar-accent text-sidebar-accent-foreground",
                  collapsed && "justify-center px-2"
                )}
              >
                {item.icon}
                {!collapsed && item.label}
              </span>
            </Link>
          ))}

          {isAdmin && (
            <>
              <div className={cn("my-2", collapsed ? "mx-auto" : "")}>
                <div className="h-px bg-sidebar-border" />
              </div>
              {collapsed ? (
                <span className="flex justify-center px-2 py-1 text-xs text-sidebar-foreground/50">
                  A
                </span>
              ) : (
                <span className="px-3 py-1 text-xs text-sidebar-foreground/50">Administration</span>
              )}
              {adminItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  <span
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                      pathname?.startsWith(item.href) && "bg-sidebar-accent text-sidebar-accent-foreground",
                      collapsed && "justify-center px-2"
                    )}
                  >
                    {item.icon}
                    {!collapsed && item.label}
                  </span>
                </Link>
              ))}
            </>
          )}
        </nav>
      </ScrollArea>

      <div className={cn("border-t border-sidebar-border p-3", collapsed && "flex justify-center")}>
        {!collapsed && (
          <p className="text-xs text-sidebar-foreground/50">
            &copy; 2026 Agentic Analytics
          </p>
        )}
      </div>
    </aside>
  )
}
