"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import type { DatabaseConnectionResponse, SchemaResponse, TableSchema, ColumnInfo, ConnectionHealthResponse } from "@/types/api"
import { formatDate } from "@/lib/utils"
import {
  ArrowLeft,
  Database,
  TestTube,
  RefreshCw,
  Table2,
  Key,
  Link2,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"

const connectionTypeColors: Record<string, string> = {
  postgresql: "bg-blue-500/10 text-blue-600 border-blue-200",
  mysql: "bg-orange-500/10 text-orange-600 border-orange-200",
  sqlserver: "bg-red-500/10 text-red-600 border-red-200",
  mariadb: "bg-teal-500/10 text-teal-600 border-teal-200",
  mongodb: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
}

export default function DatabaseDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = Number(params.id)
  const { toast } = useToast()

  const [conn, setConn] = useState<DatabaseConnectionResponse | null>(null)
  const [schema, setSchema] = useState<SchemaResponse | null>(null)
  const [isLoadingConn, setIsLoadingConn] = useState(true)
  const [isLoadingSchema, setIsLoadingSchema] = useState(true)
  const [isTesting, setIsTesting] = useState(false)
  const [health, setHealth] = useState<ConnectionHealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())
  const healthIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchData = useCallback(async () => {
    setIsLoadingConn(true)
    setIsLoadingSchema(true)
    try {
      const [connData, schemaData] = await Promise.all([
        api.getDatabaseById(id),
        api.getDatabaseSchema(id),
      ])
      setConn(connData)
      setSchema(schemaData)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to load database", variant: "destructive" })
    } finally {
      setIsLoadingConn(false)
      setIsLoadingSchema(false)
    }
  }, [id, toast])

  useEffect(() => { fetchData() }, [fetchData])

  const healthRef = useRef(false)

  const checkHealth = useCallback(async () => {
    if (healthRef.current) return
    healthRef.current = true
    try {
      const result = await api.getConnectionHealth(id)
      setHealth(result)
      setHealthError(null)
    } catch {
      setHealthError("Health check failed")
    } finally {
      healthRef.current = false
    }
  }, [id])

  useEffect(() => {
    checkHealth()
    healthIntervalRef.current = setInterval(checkHealth, 5000)
    return () => {
      if (healthIntervalRef.current) clearInterval(healthIntervalRef.current)
    }
  }, [checkHealth])

  const handleTest = async () => {
    setIsTesting(true)
    try {
      const result = await api.testDatabaseConnection(id)
      if (result.success) {
        toast({
          title: "Connection successful",
          description: `Server: ${result.server_version} (${result.latency_ms}ms)`,
          variant: "success",
        })
      } else {
        toast({ title: "Connection failed", description: result.message || "Unknown error", variant: "destructive" })
      }
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Test failed", variant: "destructive" })
    } finally {
      setIsTesting(false)
    }
  }

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      const result = await api.syncDatabaseSchema(id)
      toast({
        title: "Sync completed",
        description: `${result.tables_synced} tables, ${result.columns_synced} columns synced`,
        variant: "success",
      })
      const [connData, schemaData] = await Promise.all([
        api.getDatabaseById(id),
        api.getDatabaseSchema(id),
      ])
      setConn(connData)
      setSchema(schemaData)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Sync failed", variant: "destructive" })
    } finally {
      setIsSyncing(false)
    }
  }

  const toggleTable = (tableName: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev)
      if (next.has(tableName)) next.delete(tableName)
      else next.add(tableName)
      return next
    })
  }

  if (isLoadingConn) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-1" />
          </div>
        </div>
        <Skeleton className="h-32 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    )
  }

  if (!conn) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.push("/dashboard/databases")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Databases
        </Button>
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Database connection not found
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard/databases")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <Database className="h-6 w-6 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{conn.name}</h1>
              <Badge variant="outline" className={cn("text-xs", connectionTypeColors[conn.connection_type])}>
                {conn.connection_type}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              {conn.host}:{conn.port}/{conn.database_name}
              {conn.description ? ` — ${conn.description}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleTest} disabled={isTesting}>
            {isTesting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <TestTube className="mr-2 h-4 w-4" />
            )}
            Test Connection
          </Button>
          <Button variant="outline" onClick={handleSync} disabled={isSyncing}>
            {isSyncing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Sync Schema
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Connection</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {health === null ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Checking...</span>
                </>
              ) : health.healthy ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span className="text-lg font-bold">Connected</span>
                  {health.latency_ms != null && (
                    <span className="text-xs text-muted-foreground">({health.latency_ms}ms)</span>
                  )}
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-destructive" />
                  <span className="text-lg font-bold">Unreachable</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tables</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Table2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-lg font-bold">{schema?.tables.length ?? "—"}</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Last Sync</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm font-medium">{conn.last_sync_at ? formatDate(conn.last_sync_at) : "Never"}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Created</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm font-medium">{formatDate(conn.created_at)}</span>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Schema Browser</CardTitle>
          <CardDescription>
            {schema
              ? `Tables and columns for ${schema.schema_name}`
              : "Browse database tables and their columns"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingSchema ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-md" />
              ))}
            </div>
          ) : !schema || schema.tables.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <Database className="mx-auto h-12 w-12 mb-3 opacity-20" />
              <p>No tables found. Sync the schema to discover database tables.</p>
              <Button variant="outline" className="mt-4" onClick={handleSync} disabled={isSyncing}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Sync Schema
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {schema.tables.map((table) => (
                <SchemaTableCard
                  key={table.name}
                  table={table}
                  isExpanded={expandedTables.has(table.name)}
                  onToggle={() => toggleTable(table.name)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function SchemaTableCard({
  table,
  isExpanded,
  onToggle,
}: {
  table: TableSchema
  isExpanded: boolean
  onToggle: () => void
}) {
  return (
    <Card className="overflow-hidden">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
            <Table2 className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="font-medium">{table.name}</p>
            <div className="text-xs text-muted-foreground">
              {table.schema_name}.{table.name}
              {" — "}
              <Badge variant="outline" className="text-xs px-1 py-0">{table.type}</Badge>
              {" — "}
              {table.columns.length} column{table.columns.length !== 1 ? "s" : ""}
              {table.row_count != null ? ` — ~${table.row_count.toLocaleString()} rows` : ""}
            </div>
          </div>
        </div>
        {isExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
      </button>
      {isExpanded && (
        <div className="border-t">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Column</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Type</th>
                <th className="px-4 py-2 text-center font-medium text-muted-foreground">Nullable</th>
                <th className="px-4 py-2 text-center font-medium text-muted-foreground">PK</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">Default</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">FK</th>
              </tr>
            </thead>
            <tbody>
              {table.columns.map((col) => (
                <tr key={col.name} className="border-b transition-colors hover:bg-muted/20">
                  <td className="px-4 py-2 font-medium">{col.name}</td>
                  <td className="px-4 py-2">
                    <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{col.data_type}</code>
                    {col.max_length != null && (
                      <span className="text-xs text-muted-foreground ml-1">({col.max_length})</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {col.nullable ? (
                      <CheckCircle2 className="inline h-3.5 w-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="inline h-3.5 w-3.5 text-destructive" />
                    )}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {col.is_primary_key ? (
                      <Key className="inline h-3.5 w-3.5 text-amber-500" />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">
                    {col.default_value || "—"}
                  </td>
                  <td className="px-4 py-2 text-xs">
                    {col.is_foreign_key ? (
                      <Link2 className="inline h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
