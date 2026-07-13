"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DataTable, type Column } from "@/components/ui/data-table"
import { formatDate } from "@/lib/utils"
import type { ConversationResponse } from "@/types/api"
import {
  MessageSquare,
  Plus,
  Trash2,
  Loader2,
  Database,
} from "lucide-react"

export default function ConversationsPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [conversations, setConversations] = useState<ConversationResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  const perPage = 20

  const fetchConversations = async () => {
    setIsLoading(true)
    try {
      const data = await api.listConversations({ page, per_page: perPage })
      setConversations(data.conversations)
      setTotal(data.total)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to load conversations", variant: "destructive" })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchConversations() }, [page])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const conv = await api.createConversation()
      toast({ title: "Conversation created", variant: "success" })
      router.push(`/dashboard/conversations/${conv.id}`)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to create conversation", variant: "destructive" })
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.deleteConversation(id)
      toast({ title: "Conversation deleted", variant: "success" })
      fetchConversations()
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to delete", variant: "destructive" })
    }
  }

  const columns: Column<ConversationResponse>[] = [
    {
      key: "title",
      header: "Conversation",
      cell: (c) => (
        <button
          onClick={() => router.push(`/dashboard/conversations/${c.id}`)}
          className="flex items-center gap-3 hover:underline"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <MessageSquare className="h-4 w-4 text-primary" />
          </div>
          <div className="text-left">
            <p className="font-medium">{c.title || "Untitled"}</p>
            <p className="text-xs text-muted-foreground">{c.message_count} messages</p>
          </div>
        </button>
      ),
    },
    {
      key: "database_id",
      header: "Database",
      cell: (c) => c.database_id ? (
        <Badge variant="outline" className="text-xs">
          <Database className="mr-1 h-3 w-3" />
          DB #{c.database_id}
        </Badge>
      ) : <span className="text-xs text-muted-foreground">None</span>,
    },
    {
      key: "message_count",
      header: "Messages",
      cell: (c) => <span className="text-sm">{c.message_count}</span>,
    },
    {
      key: "total_tokens",
      header: "Tokens",
      cell: (c) => <span className="text-sm text-muted-foreground">{c.total_tokens || "—"}</span>,
    },
    {
      key: "updated_at",
      header: "Last Active",
      cell: (c) => <span className="text-sm text-muted-foreground">{formatDate(c.updated_at)}</span>,
    },
    {
      key: "actions",
      header: "",
      cell: (c) => (
        <Button
          variant="ghost"
          size="icon"
          className="text-destructive"
          title="Delete"
          onClick={(e) => { e.stopPropagation(); handleDelete(c.id) }}
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
          <h1 className="text-3xl font-bold tracking-tight">Conversations</h1>
          <p className="text-muted-foreground">Chat with your data using AI</p>
        </div>
        <Button onClick={handleCreate} disabled={creating}>
          {creating ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...</>
          ) : (
            <><Plus className="mr-2 h-4 w-4" /> New Conversation</>
          )}
        </Button>
      </div>

      <Card>
        <CardHeader />
        <CardContent>
          <DataTable
            columns={columns}
            data={conversations}
            total={total}
            page={page}
            perPage={perPage}
            onPageChange={setPage}
            isLoading={isLoading}
          />
        </CardContent>
      </Card>
    </div>
  )
}
