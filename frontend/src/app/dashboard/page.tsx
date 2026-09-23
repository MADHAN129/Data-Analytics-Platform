"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useAuthStore } from "@/store/auth-store"
import { api } from "@/lib/api-client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/utils"
import { BarChart3, Database, MessageSquare, TrendingUp, Loader2 } from "lucide-react"

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [totalConnections, setTotalConnections] = useState<number | null>(null)
  const [healthyCount, setHealthyCount] = useState(0)
  const [unhealthyCount, setUnhealthyCount] = useState(0)
  const [unknownCount, setUnknownCount] = useState(0)
  const [loading, setLoading] = useState(true)

  const healthRef = useRef(false)

  const refreshHealth = useCallback(async () => {
    if (healthRef.current) return
    healthRef.current = true
    try {
      const [healthData, listData] = await Promise.all([
        api.getBatchConnectionHealth(),
        api.listDatabases({ per_page: 100 }),
      ])
      const hc = healthData.connections.filter((c) => c.healthy).length
      const uc = healthData.connections.filter((c) => !c.healthy).length
      setTotalConnections(listData.total)
      setHealthyCount(hc)
      setUnhealthyCount(uc)
      setUnknownCount(listData.total - hc - uc)
    } catch {
      // silent
    } finally {
      setLoading(false)
      healthRef.current = false
    }
  }, [])

  useEffect(() => {
    refreshHealth()
    const interval = setInterval(refreshHealth, 15000)
    return () => clearInterval(interval)
  }, [refreshHealth])

  const stats = [
    {
      title: "Connected Databases",
      value: loading ? "—" : String(totalConnections ?? 0),
      description: totalConnections
        ? `${healthyCount} healthy, ${unhealthyCount} unreachable${unknownCount > 0 ? `, ${unknownCount} unknown` : ""}`
        : "No databases connected",
      icon: Database,
    },
    {
      title: "Queries Today",
      value: "0",
      description: "Start querying your data",
      icon: MessageSquare,
    },
    {
      title: "Active Dashboards",
      value: "0",
      description: "Create your first dashboard",
      icon: BarChart3,
    },
    {
      title: "Insights Generated",
      value: "0",
      description: "AI-powered insights pending",
      icon: TrendingUp,
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Welcome, {user?.full_name?.split(" ")[0] || "User"}
        </h1>
        <p className="text-muted-foreground">
          Here&apos;s your analytics overview. Last login: {user?.updated_at ? formatDate(user.updated_at) : "N/A"}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              {stat.title === "Connected Databases" && loading ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : (
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              )}
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stat.value}</div>
              <p className="mt-1 text-xs text-muted-foreground">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Connect a database", href: "/dashboard/databases", badge: "New" },
              { label: "Ask a question about your data", href: "/dashboard/analytics", badge: "Popular" },
              { label: "Create a new dashboard", href: "/dashboard/dashboards", badge: null },
              { label: "View recent activity", href: "/dashboard/activity", badge: null },
            ].map((action) => (
              <a
                key={action.label}
                href={action.href}
                className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
              >
                <span className="text-sm font-medium">{action.label}</span>
                {action.badge && (
                  <Badge variant="secondary" className="text-xs">
                    {action.badge}
                  </Badge>
                )}
              </a>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Name</span>
              <span className="text-sm font-medium">{user?.full_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Email</span>
              <span className="text-sm font-medium">{user?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Roles</span>
              <span className="text-sm font-medium">
                {user?.roles?.map((r) => r.name).join(", ") || "N/A"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Provider</span>
              <Badge variant="outline" className="text-xs">
                {user?.auth_provider || "local"}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Status</span>
              <Badge variant={user?.is_active ? "success" : "destructive"} className="text-xs">
                {user?.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
