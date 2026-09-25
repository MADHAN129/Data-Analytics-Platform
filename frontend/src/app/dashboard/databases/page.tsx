"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { apiCache } from "@/lib/api-cache"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { DataTable, type Column } from "@/components/ui/data-table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type {
  DatabaseConnectionResponse,
  DatabaseCreateRequest,
  DatabaseUpdateRequest,
  ConnectionType,
} from "@/types/api"
import { formatDate } from "@/lib/utils"
import {
  CheckCircle2,
  Database,
  Loader2,
  Plus,
  Search,
  Trash2,
  Link2,
  Unlink,
  RefreshCw,
  Pencil,
  Eye,
  XCircle,
} from "lucide-react"

const connectionTypeColors: Record<ConnectionType, string> = {
  postgresql: "bg-blue-500/10 text-blue-600 border-blue-200",
  mysql: "bg-orange-500/10 text-orange-600 border-orange-200",
  sqlserver: "bg-red-500/10 text-red-600 border-red-200",
  mariadb: "bg-teal-500/10 text-teal-600 border-teal-200",
  mongodb: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
  oracle: "bg-red-600/10 text-red-600 border-red-200",
}

const defaultPorts: Record<ConnectionType, string> = {
  postgresql: "5432",
  mysql: "3306",
  sqlserver: "1433",
  mariadb: "3306",
  mongodb: "27017",
  oracle: "1521",
}

const defaultForm: DatabaseCreateRequest = {
  name: "",
  description: "",
  connection_type: "postgresql",
  host: "",
  port: 5432,
  database_name: "",
  schema_name: "public",
  username: "",
  password: "",
  ssl: false,
  pool_size: 10,
  timeout_seconds: 30,
}

export default function DatabasesPage() {
  const router = useRouter()
  const [connections, setConnections] = useState<DatabaseConnectionResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [connectionTypeFilter, setConnectionTypeFilter] = useState<string>("")
  const [isLoading, setIsLoading] = useState(true)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedConn, setSelectedConn] = useState<DatabaseConnectionResponse | null>(null)
  const [form, setForm] = useState<DatabaseCreateRequest>({ ...defaultForm })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms: number | null } | null>(null)
  const [isTestingCreated, setIsTestingCreated] = useState(false)
  const [lastHealthCheck, setLastHealthCheck] = useState<string | null>(null)
  const { toast } = useToast()

  const perPage = 20

  const fetchConnections = useCallback(async (forceFresh = false) => {
    const cacheKey = `databases:page=${page}:search=${search}:filter=${connectionTypeFilter}`
    try {
      const { data, isFromCache } = await apiCache.swr(
        cacheKey,
        () =>
          api.listDatabases({
            page,
            per_page: perPage,
            search: search || undefined,
            connection_type: connectionTypeFilter || undefined,
          }),
        {
          ttlMs: 45000,
          forceFresh,
          onRevalidate: (fresh) => {
            setConnections(fresh.connections)
            setTotal(fresh.total)
          },
        }
      )
      setConnections(data.connections)
      setTotal(data.total)
      setIsLoading(false)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to load databases", variant: "destructive" })
      setIsLoading(false)
    }
  }, [page, perPage, search, connectionTypeFilter, toast])

  useEffect(() => { fetchConnections() }, [fetchConnections])

  const pollingRef = useRef(false)
  const doHealthCheck = useCallback(async () => {
    if (pollingRef.current) return
    pollingRef.current = true
    try {
      await api.getBatchConnectionHealth()
      setLastHealthCheck(new Date().toLocaleTimeString())
    } catch {
      // silent — health check failures shouldn't disrupt UI
    } finally {
      pollingRef.current = false
    }
  }, [])

  useEffect(() => {
    const cycle = async () => {
      await doHealthCheck()
      fetchConnections()
    }
    cycle()
    const interval = setInterval(cycle, 15000)
    return () => clearInterval(interval)
  }, [doHealthCheck, fetchConnections])

  const resetForm = () => setForm({ ...defaultForm })

  const handleCreate = async () => {
    setIsSubmitting(true)
    try {
      const created = await api.createDatabase({
        ...form,
        port: Number(form.port),
      })
      apiCache.invalidate("databases")
      toast({ title: "Connection created", variant: "success" })
      setCreateDialogOpen(false)
      resetForm()
      fetchConnections(true)

      setIsTestingCreated(true)
      setTestResult(null)
      try {
        const result = await api.testDatabaseConnection(created.id)
        setTestResult({
          success: result.success,
          message: result.message,
          latency_ms: result.latency_ms,
        })
      } catch {
        setTestResult({ success: false, message: "Test failed", latency_ms: null })
      } finally {
        setIsTestingCreated(false)
        setTimeout(() => setTestResult(null), 3000)
      }
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to create connection", variant: "destructive" })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUpdate = async () => {
    if (!selectedConn) return
    setIsSubmitting(true)
    try {
      const data: DatabaseUpdateRequest = { ...form }
      data.port = Number(form.port)
      if (!data.password) delete data.password
      await api.updateDatabase(selectedConn.id, data)
      apiCache.invalidate("databases")
      toast({ title: "Connection updated", variant: "success" })
      setEditDialogOpen(false)
      setSelectedConn(null)
      fetchConnections(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to update connection", variant: "destructive" })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedConn) return
    try {
      await api.deleteDatabase(selectedConn.id)
      apiCache.invalidate("databases")
      toast({ title: "Connection deleted", variant: "success" })
      setDeleteDialogOpen(false)
      setSelectedConn(null)
      fetchConnections(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to delete connection", variant: "destructive" })
    }
  }

  const handleTest = async (id: number) => {
    setTestingId(id)
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
      toast({ title: "Error", description: error.detail || "Failed to test connection", variant: "destructive" })
    } finally {
      setTestingId(null)
    }
  }

  const openEdit = (conn: DatabaseConnectionResponse) => {
    setSelectedConn(conn)
    setForm({
      name: conn.name,
      description: conn.description || "",
      connection_type: conn.connection_type,
      host: conn.host,
      port: conn.port,
      database_name: conn.database_name,
      schema_name: conn.schema_name,
      username: conn.username,
      password: "",
      ssl: conn.ssl || false,
      pool_size: conn.pool_size,
      timeout_seconds: conn.timeout_seconds,
    })
    setEditDialogOpen(true)
  }

  const openDelete = (conn: DatabaseConnectionResponse) => {
    setSelectedConn(conn)
    setDeleteDialogOpen(true)
  }

  const columns: Column<DatabaseConnectionResponse>[] = [
    {
      key: "name",
      header: "Name",
      cell: (conn) => (
        <button
          onClick={() => router.push(`/dashboard/databases/${conn.id}`)}
          className="flex items-center gap-3 hover:underline"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Database className="h-4 w-4 text-primary" />
          </div>
          <div className="text-left">
            <p className="font-medium">{conn.name}</p>
            <p className="text-xs text-muted-foreground">{conn.description || conn.database_name}</p>
          </div>
        </button>
      ),
    },
    {
      key: "type",
      header: "Type",
      cell: (conn) => (
        <Badge variant="outline" className={`text-xs ${connectionTypeColors[conn.connection_type] || ""}`}>
          {conn.connection_type}
        </Badge>
      ),
    },
    {
      key: "host",
      header: "Host",
      cell: (conn) => (
        <span className="text-sm text-muted-foreground">
          {conn.host}:{conn.port}
        </span>
      ),
    },
    {
      key: "health_status",
      header: "Health",
      cell: (conn) => {
        if (conn.health_status === null) {
          return <span className="text-xs text-muted-foreground">Unknown</span>
        }
        return (
          <span className="flex items-center gap-1.5 text-sm">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                conn.health_status ? "bg-emerald-500" : "bg-destructive"
              }`}
            />
            {conn.health_status ? "Connected" : "Unreachable"}
            {conn.health_status && conn.health_latency_ms != null && (
              <span className="text-xs text-muted-foreground">({conn.health_latency_ms}ms)</span>
            )}
          </span>
        )
      },
    },
    {
      key: "last_sync_at",
      header: "Last Sync",
      cell: (conn) => (
        <span className="text-sm text-muted-foreground">
          {conn.last_sync_at ? formatDate(conn.last_sync_at) : "Never"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (conn) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            title="View schema"
            onClick={() => router.push(`/dashboard/databases/${conn.id}`)}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            title="Test connection"
            onClick={() => handleTest(conn.id)}
            disabled={testingId === conn.id}
          >
            {testingId === conn.id ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Link2 className="h-4 w-4" />
            )}
          </Button>
          <Button variant="ghost" size="icon" title="Edit" onClick={() => openEdit(conn)}>
            <Pencil className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="text-destructive" title="Delete" onClick={() => openDelete(conn)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Databases</h1>
          <p className="text-muted-foreground">Connect and manage your external databases</p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="mr-2 h-4 w-4" />
              Add Connection
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>New Database Connection</DialogTitle>
              <DialogDescription>Connect to an external database</DialogDescription>
            </DialogHeader>
            <ConnectionForm form={form} onChange={setForm} />
            <DialogFooter>
              <Button variant="outline" onClick={() => { setCreateDialogOpen(false); resetForm() }}>Cancel</Button>
              <Button onClick={handleCreate} disabled={isSubmitting || !form.name || !form.host || !form.database_name}>
                {isSubmitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...</> : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search databases..."
                className="pl-9"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              />
            </div>
            <Select value={connectionTypeFilter} onValueChange={(v) => { setConnectionTypeFilter(v); setPage(1) }}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All types</SelectItem>
                <SelectItem value="postgresql">PostgreSQL</SelectItem>
                <SelectItem value="mysql">MySQL</SelectItem>
                <SelectItem value="sqlserver">SQL Server</SelectItem>
                <SelectItem value="mariadb">MariaDB</SelectItem>
                <SelectItem value="mongodb">MongoDB</SelectItem>
                <SelectItem value="oracle">Oracle</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={connections}
            total={total}
            page={page}
            perPage={perPage}
            onPageChange={setPage}
            isLoading={isLoading}
          />
        </CardContent>
      </Card>

      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Connection</DialogTitle>
            <DialogDescription>Update database connection details</DialogDescription>
          </DialogHeader>
          <ConnectionForm form={form} onChange={setForm} isEdit />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdate} disabled={isSubmitting || !form.name || !form.host}>
              {isSubmitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Connection</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{selectedConn?.name}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={testResult !== null || isTestingCreated} onOpenChange={(open) => { if (!open) { setTestResult(null); setIsTestingCreated(false) } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Testing Connection</DialogTitle>
            <DialogDescription>
              {isTestingCreated ? "Attempting to connect to the database..." : "Connection test result"}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center gap-4 py-6">
            {isTestingCreated ? (
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
            ) : testResult?.success ? (
              <>
                <CheckCircle2 className="h-12 w-12 text-emerald-500" />
                <p className="text-lg font-semibold">Connected</p>
                {testResult.latency_ms != null && (
                  <p className="text-sm text-muted-foreground">{testResult.latency_ms}ms latency</p>
                )}
              </>
            ) : (
              <>
                <XCircle className="h-12 w-12 text-destructive" />
                <p className="text-lg font-semibold">Connection Failed</p>
                <p className="text-sm text-muted-foreground text-center max-w-xs">{testResult?.message}</p>
              </>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => { setTestResult(null); setIsTestingCreated(false) }}>
              {isTestingCreated ? "Cancel" : "Done"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function ConnectionForm({
  form,
  onChange,
  isEdit,
}: {
  form: DatabaseCreateRequest
  onChange: (f: DatabaseCreateRequest) => void
  isEdit?: boolean
}) {
  const update = (key: keyof DatabaseCreateRequest, value: string | number | boolean) =>
    onChange({ ...form, [key]: value })

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="conn-name">Connection Name</Label>
        <Input id="conn-name" value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="e.g., Production DB" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="conn-desc">Description (optional)</Label>
        <Input id="conn-desc" value={form.description || ""} onChange={(e) => update("description", e.target.value)} placeholder="My production database" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="conn-type">Database Type</Label>
        <Select value={form.connection_type} onValueChange={(v: ConnectionType) => {
          onChange({ ...form, connection_type: v, port: Number(defaultPorts[v]) })
        }}>
          <SelectTrigger id="conn-type">
            <SelectValue placeholder="Select type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="postgresql">PostgreSQL</SelectItem>
            <SelectItem value="mysql">MySQL</SelectItem>
            <SelectItem value="sqlserver">SQL Server</SelectItem>
            <SelectItem value="mariadb">MariaDB</SelectItem>
            <SelectItem value="mongodb">MongoDB</SelectItem>
            <SelectItem value="oracle">Oracle</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 space-y-2">
          <Label htmlFor="conn-host">Host</Label>
          <Input id="conn-host" value={form.host} onChange={(e) => update("host", e.target.value)} placeholder="localhost" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="conn-port">Port</Label>
          <Input id="conn-port" type="number" value={form.port} onChange={(e) => update("port", e.target.value)} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="conn-dbname">Database Name</Label>
          <Input id="conn-dbname" value={form.database_name} onChange={(e) => update("database_name", e.target.value)} placeholder="mydb" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="conn-schema">Schema Name</Label>
          <Input id="conn-schema" value={form.schema_name || "public"} onChange={(e) => update("schema_name", e.target.value)} placeholder="public" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="conn-user">Username</Label>
          <Input id="conn-user" value={form.username} onChange={(e) => update("username", e.target.value)} placeholder="admin" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="conn-pass">
            {isEdit ? "Password (leave blank to keep)" : "Password"}
          </Label>
          <Input id="conn-pass" type="password" value={form.password} onChange={(e) => update("password", e.target.value)} placeholder="••••••••" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input
          id="conn-ssl"
          type="checkbox"
          checked={form.ssl || false}
          onChange={(e) => update("ssl", e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
        />
        <Label htmlFor="conn-ssl" className="text-sm font-normal">Use SSL/TLS</Label>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="conn-pool">Pool Size</Label>
          <Input id="conn-pool" type="number" min={1} max={100} value={form.pool_size ?? 10} onChange={(e) => update("pool_size", Number(e.target.value))} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="conn-timeout">Timeout (seconds)</Label>
          <Input id="conn-timeout" type="number" min={5} max={300} value={form.timeout_seconds ?? 30} onChange={(e) => update("timeout_seconds", Number(e.target.value))} />
        </div>
      </div>
    </div>
  )
}
