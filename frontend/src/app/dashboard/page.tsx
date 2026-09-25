"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth-store"
import { api } from "@/lib/api-client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/utils"
import {
  BarChart3,
  Database,
  MessageSquare,
  TrendingUp,
  Loader2,
  Sparkles,
  ArrowRight,
} from "lucide-react"

export default function DashboardPage() {
  const router = useRouter()
  const { user } = useAuthStore()

  // Dynamic States
  const [totalConnections, setTotalConnections] = useState<number | null>(null)
  const [healthyCount, setHealthyCount] = useState(0)
  const [unhealthyCount, setUnhealthyCount] = useState(0)
  const [unknownCount, setUnknownCount] = useState(0)

  const [queriesToday, setQueriesToday] = useState(0)
  const [totalQueries, setTotalQueries] = useState(0)

  const [totalDashboards, setTotalDashboards] = useState(0)
  const [totalWidgets, setTotalWidgets] = useState(0)

  const [insightsGenerated, setInsightsGenerated] = useState(0)

  const [loading, setLoading] = useState(true)
  const isRefreshingRef = useRef(false)

  const refreshOverviewStats = useCallback(async () => {
    if (isRefreshingRef.current) return
    isRefreshingRef.current = true

    try {
      const [healthData, listData, activityData, dashboardsData] = await Promise.all([
        api.getBatchConnectionHealth().catch(() => ({ connections: [] })),
        api.listDatabases({ per_page: 100 }).catch(() => ({ connections: [], total: 0 })),
        api.getActivityOverview(30).catch(() => ({ total_queries: 0, recent_queries: [], token_timeline: [] })),
        api.listDashboards({ per_page: 100 }).catch(() => ({ dashboards: [], total: 0 })),
      ])

      // 1. Connected Databases
      const conns = healthData.connections || []
      const hc = conns.filter((c) => c.healthy).length
      const uc = conns.filter((c) => !c.healthy).length
      const totalDb = listData.total ?? conns.length
      setTotalConnections(totalDb)
      setHealthyCount(hc)
      setUnhealthyCount(uc)
      setUnknownCount(Math.max(0, totalDb - hc - uc))

      // 2. Queries Today
      const todayStr = new Date().toISOString().slice(0, 10)
      const localToday = new Date()
      localToday.setHours(0, 0, 0, 0)

      let todayCount = 0
      const recent = activityData.recent_queries || []
      if (recent.length > 0) {
        todayCount = recent.filter((q) => {
          if (!q.created_at) return false
          const qDate = new Date(q.created_at)
          return qDate >= localToday || q.created_at.slice(0, 10) === todayStr
        }).length
      }

      // If recent queries had items or timeline has today
      if (todayCount === 0 && activityData.token_timeline) {
        const todayTimeline = activityData.token_timeline.find((t) => t.date === todayStr)
        if (todayTimeline) {
          todayCount = todayTimeline.queries_count || 0
        }
      }

      const totQ = activityData.total_queries ?? recent.length
      setQueriesToday(todayCount > 0 ? todayCount : totQ)
      setTotalQueries(totQ)

      // 3. Active Dashboards
      const dashes = dashboardsData.dashboards || []
      const dashTotal = dashboardsData.total ?? dashes.length
      const widgetsSum = dashes.reduce((acc, d) => acc + (d.widget_count || 0), 0)
      setTotalDashboards(dashTotal)
      setTotalWidgets(widgetsSum)

      // 4. Insights Generated (strictly scoped to this user's company)
      let storedReportsCount = 0
      if (typeof window !== "undefined") {
        const companyKey = user?.company_id
          ? `generated_reports_company_${user.company_id}`
          : user?.id
          ? `generated_reports_user_${user.id}`
          : null
        const stored = companyKey ? localStorage.getItem(companyKey) : null
        if (stored) {
          try {
            storedReportsCount = JSON.parse(stored).length
          } catch {
            storedReportsCount = 0
          }
        }
      }

      // Insights count aggregates AI queries, dashboard widget analytics, and executive reports for this company only
      const calculatedInsights = totQ + widgetsSum + storedReportsCount
      setInsightsGenerated(calculatedInsights)
    } catch {
      // Silently ignore failures to prevent breaking dashboard layout
    } finally {
      setLoading(false)
      isRefreshingRef.current = false
    }
  }, [user])

  useEffect(() => {
    refreshOverviewStats()
    const interval = setInterval(refreshOverviewStats, 15000)
    return () => clearInterval(interval)
  }, [refreshOverviewStats])

  const userRoles = user?.roles?.map((r) => r.name)
  const hasElevatedAccess = userRoles?.some(
    (r) => r === "SuperAdmin" || r === "Admin" || r === "Analyst"
  )
  const isViewer = !hasElevatedAccess || (userRoles?.includes("Viewer") && !hasElevatedAccess)

  const allStats = [
    {
      title: "Connected Databases",
      value: loading ? "—" : String(totalConnections ?? 0),
      description:
        totalConnections && totalConnections > 0
          ? `${healthyCount} healthy, ${unhealthyCount} unreachable${unknownCount > 0 ? `, ${unknownCount} pending` : ""}`
          : "No databases connected",
      icon: Database,
      href: "/dashboard/databases",
      highlight: healthyCount > 0,
      hideForViewer: true,
    },
    {
      title: "Queries Today",
      value: loading ? "—" : String(queriesToday),
      description:
        queriesToday > 0
          ? `${queriesToday} quer${queriesToday > 1 ? "ies" : "y"} executed today (${totalQueries} total)`
          : totalQueries > 0
          ? `${totalQueries} total queries run`
          : "Start querying your data",
      icon: MessageSquare,
      href: "/dashboard/analytics",
      highlight: queriesToday > 0,
      hideForViewer: true,
    },
    {
      title: "Active Dashboards",
      value: loading ? "—" : String(totalDashboards),
      description:
        totalDashboards > 0
          ? `${totalDashboards} dashboard${totalDashboards > 1 ? "s" : ""} (${totalWidgets} widget${totalWidgets !== 1 ? "s" : ""})`
          : "Explore dashboards",
      icon: BarChart3,
      href: "/dashboard/dashboards",
      highlight: totalDashboards > 0,
    },
    {
      title: "Executive Reports",
      value: loading ? "—" : String(insightsGenerated),
      description:
        insightsGenerated > 0
          ? `${insightsGenerated} reports and analytical insights`
          : "View executive reports",
      icon: TrendingUp,
      href: "/dashboard/reports",
      highlight: insightsGenerated > 0,
    },
  ]

  const stats = allStats.filter((s) => !isViewer || !s.hideForViewer)

  const quickActions = isViewer
    ? [
        { label: "Browse shared dashboards", href: "/dashboard/dashboards", badge: "Popular" },
        { label: "View executive reports", href: "/dashboard/reports", badge: "New" },
        { label: "Update profile & settings", href: "/dashboard/profile", badge: null },
      ]
    : [
        { label: "Connect a database", href: "/dashboard/databases", badge: "New" },
        { label: "Ask a question about your data", href: "/dashboard/analytics", badge: "Popular" },
        { label: "Create a new dashboard", href: "/dashboard/dashboards", badge: null },
        { label: "Generate executive reports", href: "/dashboard/reports", badge: "New" },
        { label: "View recent activity", href: "/dashboard/activity", badge: null },
      ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Welcome, {user?.full_name?.split(" ")[0] || "User"}
        </h1>
        <p className="text-muted-foreground">
          Here&apos;s your analytics overview. Last login:{" "}
          {user?.updated_at ? formatDate(user.updated_at) : "N/A"}
        </p>
      </div>

      {/* DYNAMIC TOP STAT CARDS */}
      <div className={`grid gap-4 md:grid-cols-2 ${isViewer ? "lg:grid-cols-2" : "lg:grid-cols-4"}`}>
        {stats.map((stat) => (
          <Card
            key={stat.title}
            onClick={() => router.push(stat.href)}
            className="group cursor-pointer transition-all hover:shadow-md hover:border-primary/50 relative overflow-hidden"
          >
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                {stat.title}
              </CardTitle>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : (
                <stat.icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              )}
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight flex items-baseline justify-between">
                <span>{stat.value}</span>
                <ArrowRight className="h-4 w-4 text-muted-foreground/30 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
              </div>
              <p className="mt-1 text-xs text-muted-foreground group-hover:text-foreground/80 transition-colors">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* BOTTOM SECTION */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* QUICK ACTIONS */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {quickActions.map((action) => (
              <a
                key={action.label}
                href={action.href}
                className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50 hover:border-primary/40"
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

        {/* ACCOUNT DETAILS */}
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
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Role</span>
              <div className="flex flex-wrap gap-1.5 justify-end">
                {user?.roles && user.roles.length > 0 ? (
                  user.roles.map((r) => (
                    <Badge
                      key={r.id}
                      variant="secondary"
                      className={`text-xs font-semibold ${
                        r.name === "SuperAdmin"
                          ? "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-200"
                          : r.name === "Admin"
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200"
                          : r.name === "Analyst"
                          ? "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-200"
                          : "bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-200"
                      }`}
                    >
                      {r.name === "SuperAdmin" ? "★ SuperAdmin" : r.name}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm font-medium">N/A</span>
                )}
              </div>
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
