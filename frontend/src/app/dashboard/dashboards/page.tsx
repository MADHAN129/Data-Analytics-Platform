"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { apiCache } from "@/lib/api-cache"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DataTable, type Column } from "@/components/ui/data-table"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { formatDate } from "@/lib/utils"
import type { DashboardResponse } from "@/types/api"
import type { ConnectionType } from "@/types/api"
import {
  LayoutDashboard, Plus, Trash2, Loader2, Zap, Sparkles, Wand2,
} from "lucide-react"

export default function DashboardsPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [dashboards, setDashboards] = useState<DashboardResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const perPage = 20
  const [isLoading, setIsLoading] = useState(true)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [autoGenOpen, setAutoGenOpen] = useState(false)

  const fetchDashboards = useCallback(async (forceFresh = false) => {
    const cacheKey = `dashboards:page=${page}`
    try {
      const { data } = await apiCache.swr(
        cacheKey,
        () => api.listDashboards({ page, per_page: perPage }),
        {
          ttlMs: 45000,
          forceFresh,
          onRevalidate: (fresh) => {
            setDashboards(fresh.dashboards)
            setTotal(fresh.total)
          },
        }
      )
      setDashboards(data.dashboards)
      setTotal(data.total)
      setIsLoading(false)
    } catch {
      toast({ title: "Error", description: "Failed to load dashboards", variant: "destructive" })
      setIsLoading(false)
    }
  }, [page, toast])

  useEffect(() => { fetchDashboards() }, [fetchDashboards])

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await api.deleteDashboard(deleteId)
      apiCache.invalidate("dashboards")
      toast({ title: "Dashboard deleted", variant: "success" })
      setDeleteId(null)
      fetchDashboards(true)
    } catch {
      toast({ title: "Error", description: "Failed to delete dashboard", variant: "destructive" })
    }
  }

  const columns: Column<DashboardResponse>[] = [
    {
      key: "title",
      header: "Dashboard",
      cell: (d) => (
        <button
          onClick={() => router.push(`/dashboard/dashboards/${d.id}`)}
          className="flex items-center gap-3 hover:underline"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <LayoutDashboard className="h-4 w-4 text-primary" />
          </div>
          <div className="text-left">
            <p className="font-medium">{d.title}</p>
            {d.description && (
              <p className="text-xs text-muted-foreground line-clamp-1">{d.description}</p>
            )}
          </div>
        </button>
      ),
    },
    {
      key: "widget_count",
      header: "Widgets",
      cell: (d) => <span className="text-muted-foreground">{d.widget_count}</span>,
    },
    {
      key: "is_template",
      header: "Type",
      cell: (d) => d.is_template
        ? <Badge variant="secondary">Template</Badge>
        : d.auto_generated
          ? <Badge variant="outline" className="gap-1"><Sparkles className="h-3 w-3" />Auto</Badge>
              : <Badge variant="outline">Custom</Badge>,
    },
    {
      key: "updated_at",
      header: "Updated",
      cell: (d) => <span className="text-muted-foreground text-sm">{formatDate(d.updated_at)}</span>,
    },
    {
      key: "actions",
      header: "",
      cell: (d) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => { e.stopPropagation(); setDeleteId(d.id) }}
          >
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
          <h1 className="text-2xl font-bold">Dashboards</h1>
          <p className="text-muted-foreground">{total} dashboard{total !== 1 ? "s" : ""}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setAutoGenOpen(true)}>
            <Wand2 className="mr-2 h-4 w-4" /> Auto-Generate
          </Button>
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Dashboard
          </Button>
        </div>
      </div>

      <Card>
        <CardContent>
          <DataTable
            columns={columns}
            data={dashboards}
            total={total}
            page={page}
            perPage={perPage}
            onPageChange={setPage}
            isLoading={isLoading}
          />
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Dashboard</DialogTitle>
          </DialogHeader>
          <CreateDashboardForm
            onSuccess={(id) => {
              setDialogOpen(false)
              router.push(`/dashboard/dashboards/${id}`)
            }}
            onCancel={() => setDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      <AutoGenerateDialog
        open={autoGenOpen}
        onOpenChange={setAutoGenOpen}
        onSuccess={(id) => router.push(`/dashboard/dashboards/${id}`)}
      />

      <Dialog open={!!deleteId} onOpenChange={(o) => { if (!o) setDeleteId(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Dashboard</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground">Are you sure you want to delete this dashboard? This action cannot be undone.</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function AutoGenerateDialog({
  open, onOpenChange, onSuccess,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  onSuccess: (id: number) => void
}) {
  const { toast } = useToast()
  const [databases, setDatabases] = useState<Array<{ id: number; name: string }>>([])
  const [dbId, setDbId] = useState<number | "">("")
  const [queryText, setQueryText] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [loadingDb, setLoadingDb] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoadingDb(true)
    api.listDatabases({ per_page: 100 })
      .then((data) => setDatabases(data.connections))
      .catch(() => setDatabases([]))
      .finally(() => setLoadingDb(false))
  }, [open])

  const handleGenerate = async () => {
    if (!dbId) return
    setSubmitting(true)
    try {
      const dash = await api.autoGenerateDashboard({
        database_id: Number(dbId),
        query_text: queryText.trim() || undefined,
      })
      toast({ title: "Dashboard generated", variant: "success" })
      onOpenChange(false)
      onSuccess(dash.id)
    } catch {
      toast({ title: "Error", description: "Failed to auto-generate dashboard", variant: "destructive" })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Auto-Generate Dashboard</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Database</Label>
            <Select
              value={dbId ? String(dbId) : ""}
              onValueChange={(v) => setDbId(Number(v))}
            >
              <SelectTrigger>
                <SelectValue placeholder={loadingDb ? "Loading databases..." : "Select a database"} />
              </SelectTrigger>
              <SelectContent>
                {databases.map((db) => (
                  <SelectItem key={db.id} value={String(db.id)}>{db.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="auto-query">Query Topic (optional)</Label>
            <Input
              id="auto-query"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder="e.g., sales by region"
            />
            <p className="text-xs text-muted-foreground">Leave empty to use the most popular query template</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleGenerate} disabled={submitting || !dbId}>
            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Generate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function CreateDashboardForm({
  onSuccess,
  onCancel,
}: {
  onSuccess: (id: number) => void
  onCancel: () => void
}) {
  const { toast } = useToast()
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSubmitting(true)
    try {
      const dash = await api.createDashboard({ title: title.trim(), description: description.trim() || undefined })
      toast({ title: "Dashboard created", variant: "success" })
      onSuccess(dash.id)
    } catch {
      toast({ title: "Error", description: "Failed to create dashboard", variant: "destructive" })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="My Dashboard" required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="desc">Description (optional)</Label>
        <Textarea id="desc" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Brief description..." />
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" disabled={submitting || !title.trim()}>
          {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          Create
        </Button>
      </DialogFooter>
    </form>
  )
}
