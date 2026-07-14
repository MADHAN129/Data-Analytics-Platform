"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { DataTable, type Column } from "@/components/ui/data-table"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
  DialogDescription, DialogFooter,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { formatDate } from "@/lib/utils"
import type { TemplateResponse } from "@/types/api"
import {
  BookOpen, Plus, Trash2, Loader2, Search, Database, Clock, Code,
} from "lucide-react"

export default function TemplatesPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [templates, setTemplates] = useState<TemplateResponse[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchTemplates = async (searchTerm = "") => {
    setIsLoading(true)
    try {
      const data = await api.listTemplates({ search: searchTerm || undefined })
      setTemplates(data.templates)
      setTotal(data.total)
    } catch {
      toast({ title: "Error", description: "Failed to load templates", variant: "destructive" })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchTemplates() }, [])

  const handleSearch = () => fetchTemplates(search)

  const handleDelete = async () => {
    if (!deleteId) return
    setDeleting(true)
    try {
      await api.deleteTemplate(deleteId)
      toast({ title: "Template deleted", variant: "success" })
      setDeleteId(null)
      fetchTemplates(search)
    } catch {
      toast({ title: "Error", description: "Failed to delete template", variant: "destructive" })
    } finally {
      setDeleting(false)
    }
  }

  const columns: Column<TemplateResponse>[] = [
    {
      key: "title",
      header: "Template",
      cell: (t) => (
        <button
          onClick={() => router.push(`/dashboard/conversations?template=${t.id}`)}
          className="flex items-center gap-3 hover:underline"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <BookOpen className="h-4 w-4 text-primary" />
          </div>
          <div className="text-left">
            <p className="font-medium">{t.title}</p>
            <p className="text-xs text-muted-foreground line-clamp-1">{t.description || t.natural_language}</p>
          </div>
        </button>
      ),
    },
    {
      key: "natural_language",
      header: "Question",
      cell: (t) => <span className="text-sm text-muted-foreground line-clamp-2 max-w-xs">{t.natural_language}</span>,
    },
    {
      key: "generated_sql",
      header: "SQL",
      cell: (t) => t.generated_sql ? (
        <code className="text-xs text-muted-foreground line-clamp-2 max-w-xs block font-mono">{t.generated_sql}</code>
      ) : <span className="text-xs text-muted-foreground">—</span>,
    },
    {
      key: "updated_at",
      header: "Updated",
      cell: (t) => (
        <span className="flex items-center gap-1 text-sm text-muted-foreground">
          <Clock className="h-3 w-3" />
          {formatDate(t.updated_at)}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (t) => (
        <Button
          variant="ghost"
          size="icon"
          className="text-destructive"
          title="Delete"
          onClick={(e) => { e.stopPropagation(); setDeleteId(t.id) }}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Query Templates</h1>
          <p className="text-muted-foreground">Save and reuse your query patterns</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search templates..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch() }}
          />
        </div>
        <Button variant="secondary" size="sm" onClick={handleSearch}>Search</Button>
        {(total === 0 && !isLoading) && (
          <p className="text-sm text-muted-foreground ml-4">
            No templates yet. Save a query from a conversation to see it here.
          </p>
        )}
      </div>

      <Card>
        <CardHeader />
        <CardContent>
          <DataTable
            columns={columns}
            data={templates}
            total={total}
            page={1}
            perPage={50}
            onPageChange={() => {}}
            isLoading={isLoading}
          />
        </CardContent>
      </Card>

      <Dialog open={deleteId !== null} onOpenChange={(o) => { if (!o) setDeleteId(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Template</DialogTitle>
            <DialogDescription>Are you sure you want to delete this template? This cannot be undone.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Deleting...</> : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
