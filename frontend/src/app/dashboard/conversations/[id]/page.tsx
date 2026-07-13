"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { formatDate } from "@/lib/utils"
import { VisualizationRenderer } from "@/components/visualization/visualization-renderer"
import type { ConversationMessageResponse } from "@/types/api"
import {
  MessageSquare,
  Send,
  Loader2,
  User,
  Sparkles,
  Trash2,
  ArrowLeft,
  Clock,
  Database,
  AlertCircle,
  BarChart3,
} from "lucide-react"

export default function ConversationDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const conversationId = Number(params.id)

  const [messages, setMessages] = useState<ConversationMessageResponse[]>([])
  const [title, setTitle] = useState("Conversation")
  const [databaseId, setDatabaseId] = useState<number | null>(null)
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [editingTitle, setEditingTitle] = useState(false)
  const [newTitle, setNewTitle] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, scrollToBottom])

  const fetchData = useCallback(async () => {
    try {
      const [convData, msgData] = await Promise.all([
        api.getConversationById(conversationId),
        api.getConversationMessages(conversationId, { per_page: 100 }),
      ])
      setTitle(convData.title || "Conversation")
      setDatabaseId(convData.database_id ?? null)
      setMessages(msgData.messages)
    } catch {
      toast({ title: "Error", description: "Failed to load conversation", variant: "destructive" })
      router.push("/dashboard/conversations")
    } finally {
      setIsLoading(false)
    }
  }, [conversationId, router, toast])

  useEffect(() => { fetchData() }, [fetchData])

  const handleSend = async () => {
    if (!input.trim() || isSending) return
    setIsSending(true)
    try {
      const tempMsg: ConversationMessageResponse = {
        id: -Date.now(),
        conversation_id: conversationId,
        role: "user",
        content: input,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, tempMsg])
      setInput("")

      const result = await api.sendMessage(conversationId, { content: input })
      setMessages((prev) => [...prev, result])
      scrollToBottom()
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to send message", variant: "destructive" })
    } finally {
      setIsSending(false)
    }
  }

  const handleTitleSave = async () => {
    setEditingTitle(false)
    if (!newTitle.trim()) return
    try {
      await api.updateConversation(conversationId, { title: newTitle.trim() })
      setTitle(newTitle.trim())
      toast({ title: "Conversation renamed", variant: "success" })
    } catch {
      toast({ title: "Error", description: "Failed to rename conversation", variant: "destructive" })
    }
  }

  const handleDelete = async () => {
    try {
      await api.deleteConversation(conversationId)
      toast({ title: "Conversation deleted", variant: "success" })
      router.push("/dashboard/conversations")
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to delete", variant: "destructive" })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard/conversations")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
              {editingTitle ? (
                <div className="flex items-center gap-2">
                  <input
                    className="rounded-md border bg-background px-2 py-1 text-lg font-semibold"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    onBlur={handleTitleSave}
                    onKeyDown={(e) => { if (e.key === "Enter") { handleTitleSave() } }}
                    autoFocus
                  />
                </div>
              ) : (
                <h1
                  className="text-lg font-semibold cursor-pointer hover:text-primary"
                  onClick={() => { setNewTitle(title); setEditingTitle(true) }}
                >
                  {title}
                </h1>
              )}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <MessageSquare className="h-3 w-3" />
              {messages.length} messages
              {databaseId && (
                <>
                  <span>·</span>
                  <Database className="h-3 w-3" />
                  DB #{databaseId}
                </>
              )}
            </div>
          </div>
        </div>
        <Button variant="ghost" size="icon" className="text-destructive" onClick={handleDelete}>
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <MessageSquare className="mb-4 h-12 w-12" />
            <p className="text-lg font-medium">Start the conversation</p>
            <p className="text-sm">Ask a question about your data</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                {msg.role !== "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Sparkles className="h-4 w-4 text-primary" />
                  </div>
                )}
                <div className={`max-w-[80%] space-y-1 ${msg.role === "user" ? "order-first" : ""}`}>
                  <div
                    className={`rounded-lg px-4 py-3 text-sm ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                    {msg.role === "assistant" && msg.results && (
                      <div className="mt-3 border-t pt-3">
                        <VisualizationRenderer results={msg.results} />
                        <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <span>{msg.results.row_count} rows returned</span>
                          {msg.results.execution_time_ms != null && (
                            <span>· {msg.results.execution_time_ms}ms execution time</span>
                          )}
                        </div>
                      </div>
                    )}
                    {msg.role === "assistant" && msg.error_message && (
                      <div className="mt-2 flex items-start gap-2 rounded bg-destructive/10 p-2 text-xs text-destructive">
                        <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
                        <span>{msg.error_message}</span>
                      </div>
                    )}
                  </div>
                  <div className={`flex items-center gap-2 px-1 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <span className="text-xs text-muted-foreground">{formatDate(msg.created_at)}</span>
                    {msg.tokens_used != null && (
                      <Badge variant="outline" className="text-[10px] px-1 py-0">
                        {msg.tokens_used} tokens
                      </Badge>
                    )}
                    {msg.model_used && (
                      <Badge variant="secondary" className="text-[10px] px-1 py-0">
                        {msg.model_used}
                      </Badge>
                    )}
                  </div>
                </div>
                {msg.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary">
                    <User className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="border-t px-6 py-4">
        <div className="flex gap-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a follow-up question..."
            rows={2}
            className="resize-none min-h-[2.5rem]"
          />
          <Button
            className="shrink-0 self-end"
            size="icon"
            onClick={handleSend}
            disabled={isSending || !input.trim()}
          >
            {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">Press Ctrl+Enter to send</p>
      </div>
    </div>
  )
}
