"use client"

import { useEffect, useState, useMemo } from "react"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { formatDate } from "@/lib/utils"
import type { ActivityOverviewResponse, ActivityQueryItem, ActivityDatabaseItem } from "@/types/api"
import {
  Activity,
  Zap,
  Database,
  Search,
  RefreshCw,
  Clock,
  User,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Server,
  Code2,
  Calendar,
  Globe,
  SlidersHorizontal,
  ChevronRight,
  TrendingUp,
  Cpu,
} from "lucide-react"

export default function ActivityPage() {
  const { toast } = useToast()
  const [data, setData] = useState<ActivityOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [selectedDbFilter, setSelectedDbFilter] = useState("all")
  const [selectedStatusFilter, setSelectedStatusFilter] = useState("all")
  const [selectedQueryForSql, setSelectedQueryForSql] = useState<ActivityQueryItem | null>(null)

  const fetchActivity = async () => {
    setLoading(true)
    try {
      const res = await api.getActivityOverview(30)
      setData(res)
    } catch (err: unknown) {
      const errorObj = err as { detail?: string }
      toast({
        title: "Failed to load activity",
        description: errorObj?.detail || "Could not fetch platform activity logs.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchActivity()
  }, [])

  // Filtered queries
  const filteredQueries = useMemo(() => {
    if (!data?.recent_queries) return []
    return data.recent_queries.filter((q) => {
      const matchesSearch =
        search === "" ||
        q.question.toLowerCase().includes(search.toLowerCase()) ||
        (q.user_name && q.user_name.toLowerCase().includes(search.toLowerCase())) ||
        (q.database_name && q.database_name.toLowerCase().includes(search.toLowerCase())) ||
        (q.generated_sql && q.generated_sql.toLowerCase().includes(search.toLowerCase()))

      const matchesDb =
        selectedDbFilter === "all" ||
        (q.database_name && q.database_name.toLowerCase() === selectedDbFilter.toLowerCase())

      const matchesStatus =
        selectedStatusFilter === "all" || q.status.toLowerCase() === selectedStatusFilter.toLowerCase()

      return matchesSearch && matchesDb && matchesStatus
    })
  }, [data?.recent_queries, search, selectedDbFilter, selectedStatusFilter])

  // Filtered database lifecycle items
  const filteredDatabases = useMemo(() => {
    if (!data?.database_lifecycle) return []
    return data.database_lifecycle.filter((db) => {
      return (
        search === "" ||
        db.name.toLowerCase().includes(search.toLowerCase()) ||
        db.host.toLowerCase().includes(search.toLowerCase()) ||
        db.type.toLowerCase().includes(search.toLowerCase()) ||
        (db.created_by_name && db.created_by_name.toLowerCase().includes(search.toLowerCase()))
      )
    })
  }, [data?.database_lifecycle, search])

  // Unique database names for dropdown filter
  const dbOptions = useMemo(() => {
    if (!data?.recent_queries) return []
    const names = new Set<string>()
    data.recent_queries.forEach((q) => {
      if (q.database_name) names.add(q.database_name)
    })
    return Array.from(names)
  }, [data?.recent_queries])

  // Total execution time average
  const avgExecTime = useMemo(() => {
    if (!data?.recent_queries || data.recent_queries.length === 0) return 0
    const valid = data.recent_queries.filter((q) => q.execution_time_ms != null)
    if (valid.length === 0) return 0
    const sum = valid.reduce((acc, curr) => acc + (curr.execution_time_ms || 0), 0)
    return Math.round(sum / valid.length)
  }, [data?.recent_queries])

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Activity className="h-8 w-8 text-blue-600" />
            Platform Activity & Telemetry
          </h1>
          <p className="text-muted-foreground">
            Monitor real-time AI analyzer token consumption, connected database lifecycles, and question query history.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchActivity}
            disabled={loading}
            className="flex items-center gap-2 shadow-sm"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Tokens Card */}
        <Card className="border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-transparent shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Tokens Consumed</CardTitle>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600">
              <Zap className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tracking-tight">
              {loading ? "..." : (data?.total_tokens || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <Cpu className="h-3 w-3 text-blue-500" />
              Tokens used across AI analyzer queries
            </p>
          </CardContent>
        </Card>

        {/* Questions Asked Card */}
        <Card className="border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Questions Asked</CardTitle>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600">
              <Code2 className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tracking-tight">
              {loading ? "..." : (data?.total_queries || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-emerald-500" />
              Avg. latency: <span className="font-semibold">{avgExecTime}ms</span>
            </p>
          </CardContent>
        </Card>

        {/* Connected Databases Card */}
        <Card className="border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Connected Databases</CardTitle>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600">
              <Database className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tracking-tight">
              {loading ? "..." : `${data?.active_databases || 0} Active`}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Total created: {data?.total_databases || 0} ({data?.dismissed_databases || 0} dismissed)
            </p>
          </CardContent>
        </Card>

        {/* Active Users Card */}
        <Card className="border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Platform Users</CardTitle>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600">
              <User className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tracking-tight">
              {loading ? "..." : data?.total_users || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Authorized users with workspace access
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs Section */}
      <Tabs defaultValue="queries" className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <TabsList className="bg-muted/60 p-1">
            <TabsTrigger value="queries" className="flex items-center gap-2">
              <Code2 className="h-4 w-4" />
              <span>Questions & Queries</span>
              <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-[10px]">
                {filteredQueries.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="databases" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              <span>Database Lifecycle</span>
              <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-[10px]">
                {filteredDatabases.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="tokens" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              <span>Token Consumption</span>
            </TabsTrigger>
          </TabsList>

          {/* Search & Filter Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[220px]">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search questions, users, DBs..."
                className="pl-8 h-9 text-xs"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {dbOptions.length > 0 && (
              <Select value={selectedDbFilter} onValueChange={setSelectedDbFilter}>
                <SelectTrigger className="h-9 w-[160px] text-xs">
                  <SelectValue placeholder="All Databases" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Databases</SelectItem>
                  {dbOptions.map((dbName) => (
                    <SelectItem key={dbName} value={dbName}>
                      {dbName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}

            <Select value={selectedStatusFilter} onValueChange={setSelectedStatusFilter}>
              <SelectTrigger className="h-9 w-[130px] text-xs">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="executing">Executing</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 1: QUESTIONS & QUERIES ACTIVITY */}
        {/* ========================================================================= */}
        <TabsContent value="queries" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>AI Analyzer Questions & Query Log</span>
                <span className="text-xs font-normal text-muted-foreground">
                  Showing {filteredQueries.length} recent query interactions
                </span>
              </CardTitle>
              <CardDescription className="text-xs">
                Detailed timeline of natural language questions asked, user info, target database host, timestamp, and token usage.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-muted/40 text-xs uppercase text-muted-foreground border-y">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Time & Question</th>
                      <th className="px-4 py-3 font-semibold">User</th>
                      <th className="px-4 py-3 font-semibold">Target Database</th>
                      <th className="px-4 py-3 font-semibold">Domain / Host</th>
                      <th className="px-4 py-3 font-semibold">Tokens Used</th>
                      <th className="px-4 py-3 font-semibold">Execution Time</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold text-right">SQL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredQueries.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                          <Code2 className="mx-auto h-8 w-8 mb-2 opacity-40" />
                          <p className="font-medium text-sm">No query activity found</p>
                          <p className="text-xs">Ask a question in Analytics or Conversations to see real-time logs here.</p>
                        </td>
                      </tr>
                    ) : (
                      filteredQueries.map((q) => (
                        <tr key={q.id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-3 max-w-sm">
                            <div className="flex flex-col">
                              <span className="font-medium text-foreground line-clamp-2">{q.question}</span>
                              <span className="text-[11px] text-muted-foreground flex items-center gap-1 mt-0.5">
                                <Clock className="h-3 w-3 text-blue-500" />
                                {formatDate(q.created_at)}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500/10 text-blue-600 text-xs font-bold">
                                {q.user_name ? q.user_name[0].toUpperCase() : "U"}
                              </div>
                              <div className="flex flex-col">
                                <span className="font-medium text-xs">{q.user_name || `User #${q.user_id}`}</span>
                                {q.user_email && (
                                  <span className="text-[10px] text-muted-foreground">{q.user_email}</span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <Database className="h-3.5 w-3.5 text-indigo-500" />
                              <span className="font-medium text-xs">{q.database_name}</span>
                              {q.database_type && (
                                <Badge variant="outline" className="text-[10px] px-1 py-0 uppercase">
                                  {q.database_type}
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1 text-xs text-muted-foreground font-mono">
                              <Globe className="h-3 w-3 text-slate-400" />
                              <span>{q.database_host ? `${q.database_host}:${q.database_port || ""}` : "local"}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1">
                              <Zap className="h-3.5 w-3.5 text-blue-600" />
                              <span className="font-semibold text-xs text-blue-600 dark:text-blue-400">
                                {q.tokens_used.toLocaleString()}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">
                            {q.execution_time_ms != null ? `${q.execution_time_ms} ms` : "—"}
                          </td>
                          <td className="px-4 py-3">
                            {q.status === "completed" ? (
                              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-[11px] font-medium flex items-center gap-1 w-fit">
                                <CheckCircle2 className="h-3 w-3" />
                                Success
                              </Badge>
                            ) : q.status === "failed" ? (
                              <Badge variant="destructive" className="text-[11px] font-medium flex items-center gap-1 w-fit">
                                <XCircle className="h-3 w-3" />
                                Failed
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[11px] font-medium flex items-center gap-1 w-fit">
                                <Clock className="h-3 w-3" />
                                {q.status}
                              </Badge>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {q.generated_sql ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs text-blue-600 hover:text-blue-700"
                                onClick={() => setSelectedQueryForSql(q)}
                              >
                                View SQL
                              </Button>
                            ) : (
                              <span className="text-xs text-muted-foreground">—</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ========================================================================= */}
        {/* TAB 2: DATABASE LIFECYCLE & DOMAIN INFO */}
        {/* ========================================================================= */}
        <TabsContent value="databases" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>Database Connection Lifecycle & History</span>
                <span className="text-xs font-normal text-muted-foreground">
                  {filteredDatabases.length} database target records
                </span>
              </CardTitle>
              <CardDescription className="text-xs">
                Track connected database domain names, creator username, creation timestamp, dismissal / disconnection status, and health.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-muted/40 text-xs uppercase text-muted-foreground border-y">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Database Name</th>
                      <th className="px-4 py-3 font-semibold">Engine Type</th>
                      <th className="px-4 py-3 font-semibold">Domain / Host Target</th>
                      <th className="px-4 py-3 font-semibold">DB User</th>
                      <th className="px-4 py-3 font-semibold">Connected By</th>
                      <th className="px-4 py-3 font-semibold">Created At</th>
                      <th className="px-4 py-3 font-semibold">Dismissed / Inactive At</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredDatabases.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                          <Database className="mx-auto h-8 w-8 mb-2 opacity-40" />
                          <p className="font-medium text-sm">No database connections found</p>
                          <p className="text-xs">Connect a database in Databases tab to start logging activity.</p>
                        </td>
                      </tr>
                    ) : (
                      filteredDatabases.map((db) => (
                        <tr key={db.id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div
                                className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                                  db.is_active ? "bg-emerald-500/10 text-emerald-600" : "bg-muted text-muted-foreground"
                                }`}
                              >
                                <Server className="h-4 w-4" />
                              </div>
                              <div>
                                <p className="font-semibold text-xs">{db.name}</p>
                                <p className="text-[11px] text-muted-foreground font-mono">{db.database_name}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant="outline" className="text-xs font-mono uppercase bg-muted/40">
                              {db.type}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-foreground">
                            <div className="flex items-center gap-1.5">
                              <Globe className="h-3.5 w-3.5 text-blue-500" />
                              <span>{db.host}:{db.port}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                            {db.username || "—"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <User className="h-3.5 w-3.5 text-slate-400" />
                              <div className="flex flex-col">
                                <span className="font-medium text-xs">{db.created_by_name || `User #${db.created_by_user_id}`}</span>
                                {db.created_by_email && (
                                  <span className="text-[10px] text-muted-foreground">{db.created_by_email}</span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3 text-slate-400" />
                              {formatDate(db.created_at)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs">
                            {db.dismissed_at ? (
                              <span className="text-destructive flex items-center gap-1">
                                <XCircle className="h-3 w-3" />
                                {formatDate(db.dismissed_at)}
                              </span>
                            ) : db.is_active ? (
                              <span className="text-muted-foreground">— (Active)</span>
                            ) : (
                              <span className="text-amber-500">Inactive</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {db.is_active ? (
                              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs">
                                Connected
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-xs text-muted-foreground">
                                Dismissed
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ========================================================================= */}
        {/* TAB 3: TOKEN CONSUMPTION & ANALYZER STATS */}
        {/* ========================================================================= */}
        <TabsContent value="tokens" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Token Efficiency</CardTitle>
                <CardDescription className="text-xs">Average tokens consumed per AI question</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {data?.total_queries
                    ? Math.round((data.total_tokens || 0) / data.total_queries).toLocaleString()
                    : 0}{" "}
                  <span className="text-xs font-normal text-muted-foreground">tokens/query</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Model Status</CardTitle>
                <CardDescription className="text-xs">Current AI query synthesis engine</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-base font-semibold flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-emerald-500" />
                  <span>Agentic LLM v2.4</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">Multi-provider auto fallback enabled</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Database Coverage</CardTitle>
                <CardDescription className="text-xs">Active vs total registered engines</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {data?.active_databases || 0} / {data?.total_databases || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {data?.dismissed_databases || 0} dismissed connections
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Token Activity Timeline (Past 30 Days)</CardTitle>
              <CardDescription className="text-xs">
                Visualizing daily token consumption and query frequency.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {data?.token_timeline && data.token_timeline.filter((t) => t.tokens > 0).length > 0 ? (
                  <div className="space-y-3">
                    {data.token_timeline
                      .filter((t) => t.tokens > 0)
                      .slice(-10)
                      .map((item) => (
                        <div key={item.date} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-medium">{item.date}</span>
                            <span className="text-blue-600 font-semibold">
                              {item.tokens.toLocaleString()} tokens ({item.queries_count} queries)
                            </span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full bg-blue-600 rounded-full"
                              style={{
                                width: `${Math.min(
                                  100,
                                  Math.max(10, (item.tokens / (data.total_tokens || 1)) * 100)
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                  </div>
                ) : (
                  <div className="py-8 text-center text-muted-foreground">
                    <Zap className="mx-auto h-8 w-8 mb-2 opacity-40 text-blue-500" />
                    <p className="text-sm font-medium">No recent token consumption spikes</p>
                    <p className="text-xs">Tokens will be calculated dynamically whenever natural language queries run.</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* SQL Preview Modal */}
      {selectedQueryForSql && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <Card className="w-full max-w-2xl shadow-xl">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base">Generated SQL Query</CardTitle>
                <CardDescription className="text-xs mt-1">
                  Question: &quot;{selectedQueryForSql.question}&quot;
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedQueryForSql(null)}
                className="h-8 w-8 p-0"
              >
                ✕
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg bg-slate-950 p-4 text-emerald-400 font-mono text-xs overflow-x-auto border">
                <pre>{selectedQueryForSql.generated_sql}</pre>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground bg-muted/40 p-3 rounded-md">
                <div>
                  <span className="font-semibold text-foreground">Target DB:</span>{" "}
                  {selectedQueryForSql.database_name} ({selectedQueryForSql.database_host})
                </div>
                <div>
                  <span className="font-semibold text-foreground">Tokens Used:</span>{" "}
                  {selectedQueryForSql.tokens_used.toLocaleString()}
                </div>
                <div>
                  <span className="font-semibold text-foreground">Asked By:</span>{" "}
                  {selectedQueryForSql.user_name}
                </div>
                <div>
                  <span className="font-semibold text-foreground">Executed At:</span>{" "}
                  {formatDate(selectedQueryForSql.created_at)}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
