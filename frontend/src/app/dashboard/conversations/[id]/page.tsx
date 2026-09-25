"use client"

import { Suspense, useEffect, useState, useRef, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { SecurityAlertModal } from "@/components/security/security-alert-modal"
import { VisualizationRenderer } from "@/components/visualization/visualization-renderer"
import { formatDate } from "@/lib/utils"
import type { ConversationMessageResponse, DatabaseConnectionResponse, SecurityAlert } from "@/types/api"
import {
  MessageSquare,
  Send,
  Loader2,
  User,
  Sparkles,
  Trash2,
  ArrowLeft,
  Database,
  AlertCircle,
  Code2,
  ChevronDown,
  ChevronUp,
  Lightbulb,
} from "lucide-react"

function ConversationDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const conversationId = Number(params.id)

  const [messages, setMessages] = useState<ConversationMessageResponse[]>([])
  const [title, setTitle] = useState("Conversation")
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [databaseId, setDatabaseId] = useState<number | null>(null)
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [editingTitle, setEditingTitle] = useState(false)
  const [newTitle, setNewTitle] = useState("")
  const [databases, setDatabases] = useState<DatabaseConnectionResponse[]>([])
  const [selectingDb, setSelectingDb] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedSuggestion, setSelectedSuggestion] = useState(-1)
  const [openSqlMsgIds, setOpenSqlMsgIds] = useState<Record<number, boolean>>({})
  const [securityAlert, setSecurityAlert] = useState<SecurityAlert | null>(null)
  const [showSecurityModal, setShowSecurityModal] = useState(false)
  const suggestRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const suggestTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, scrollToBottom])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (suggestRef.current && !suggestRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const fetchData = useCallback(async () => {
    try {
      const [convData, msgData, dbs] = await Promise.all([
        api.getConversationById(conversationId),
        api.getConversationMessages(conversationId, { per_page: 100 }),
        api.listDatabases({ per_page: 100 }).catch(() => ({ connections: [] })),
      ])
      setTitle(convData.title || "Conversation")
      setDatabaseId(convData.database_id ?? null)
      setMessages(msgData.messages)
      setDatabases(dbs.connections || [])
    } catch {
      toast({ title: "Error", description: "Failed to load conversation", variant: "destructive" })
      router.push("/dashboard/conversations")
    } finally {
      setIsLoading(false)
    }
  }, [conversationId, router, toast])

  useEffect(() => { fetchData() }, [fetchData])

  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.length < 2) { setShowSuggestions(false); return }
    try {
      const res = await api.querySuggestions(q)
      setSuggestions(res)
      setShowSuggestions(res.length > 0)
      setSelectedSuggestion(-1)
    } catch {
      setShowSuggestions(false)
    }
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setInput(val)
    if (suggestTimeoutRef.current) clearTimeout(suggestTimeoutRef.current)
    if (val.trim().length >= 2) {
      suggestTimeoutRef.current = setTimeout(() => fetchSuggestions(val.trim()), 300)
    } else {
      setShowSuggestions(false)
    }
  }

  const handleSuggestionPick = (suggestion: string) => {
    setInput(suggestion)
    setShowSuggestions(false)
  }

  const handleSuggestionKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        handleSend()
      }
      return
    }
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedSuggestion((p) => Math.min(p + 1, suggestions.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedSuggestion((p) => Math.max(p - 1, 0))
    } else if (e.key === "Enter" && selectedSuggestion >= 0) {
      e.preventDefault()
      handleSuggestionPick(suggestions[selectedSuggestion])
    } else if (e.key === "Escape") {
      setShowSuggestions(false)
    } else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleOptionClick = async (promptText: string) => {
    if (isSending || !promptText.trim()) return
    setIsSending(true)
    try {
      const tempMsg: ConversationMessageResponse = {
        id: -Date.now(),
        conversation_id: conversationId,
        role: "user",
        content: promptText,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, tempMsg])
      setInput("")
      setShowSuggestions(false)

      const result = await api.sendMessage(conversationId, { content: promptText })
      setMessages((prev) => [...prev, result])
      if (result.is_security_violation && result.security_alert) {
        setSecurityAlert(result.security_alert)
        setShowSecurityModal(true)
      }
      scrollToBottom()
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to send message", variant: "destructive" })
    } finally {
      setIsSending(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isSending) return
    await handleOptionClick(input.trim())
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
    setIsDeleting(true)
    try {
      await api.deleteConversation(conversationId)
      toast({ title: "Conversation deleted", variant: "success" })
      setDeleteConfirmOpen(false)
      router.push("/dashboard/conversations")
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to delete", variant: "destructive" })
    } finally {
      setIsDeleting(false)
    }
  }

  const handleSetDatabase = async (dbId: string) => {
    setSelectingDb(true)
    try {
      await api.updateConversation(conversationId, { database_id: Number(dbId) })
      setDatabaseId(Number(dbId))
      toast({ title: "Database set", description: "This conversation will now use the selected database.", variant: "success" })
    } catch {
      toast({ title: "Error", description: "Failed to set database", variant: "destructive" })
    } finally {
      setSelectingDb(false)
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
                  {databases.find((d) => d.id === databaseId)?.name || `DB #${databaseId}`}
                </>
              )}
            </div>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="text-destructive"
          title="Delete conversation"
          onClick={() => setDeleteConfirmOpen(true)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {!databaseId && (
        <div className="mx-6 mt-4 flex items-center gap-3 rounded-lg border bg-muted/50 px-4 py-3">
          <Database className="h-5 w-5 text-muted-foreground" />
          <div className="flex-1">
            <p className="text-sm font-medium">Select a database</p>
            <p className="text-xs text-muted-foreground">Choose a database so the AI can understand your schema and generate accurate queries.</p>
          </div>
          <Select onValueChange={handleSetDatabase} disabled={selectingDb}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Pick a database..." />
            </SelectTrigger>
            <SelectContent>
              {databases.map((db) => (
                <SelectItem key={db.id} value={String(db.id)}>
                  {db.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

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

                    {/* Interactive Clarification Cards */}
                    {msg.role === "assistant" && msg.clarification_options && msg.clarification_options.length > 0 && (
                      <div className="mt-3 space-y-2 border-t border-border/40 pt-3">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground/90">
                          <Sparkles className="h-3.5 w-3.5 text-primary" />
                          <span>Select an option to refine your request:</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {msg.clarification_options.map((opt, idx) => (
                            <button
                              key={opt.id || idx}
                              type="button"
                              disabled={isSending}
                              onClick={() => handleOptionClick(opt.prompt || opt.label)}
                              className="flex items-start gap-2.5 rounded-lg border border-border/70 bg-background/80 hover:bg-accent/80 hover:border-primary/50 p-2.5 text-left transition-all hover:shadow-sm active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none group"
                            >
                              <span className="text-base leading-none mt-0.5">{opt.icon || "📊"}</span>
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                                  {opt.label}
                                </div>
                                {opt.description && (
                                  <div className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5 leading-tight">
                                    {opt.description}
                                  </div>
                                )}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Visualizations & Executed SQL */}
                    {msg.role === "assistant" && msg.results && (
                      <div className="mt-3 border-t border-border/40 pt-3 space-y-3">
                        <VisualizationRenderer results={msg.results} />
                        
                        {/* Executed SQL accordion */}
                        {(() => {
                          const sqlQuery = Array.isArray(msg.tool_calls)
                            ? (msg.tool_calls.find((t) => t && t.tool === "execute_sql" && typeof t.query === "string")?.query as string | undefined)
                            : undefined
                          if (!sqlQuery) return null
                          return (
                            <div className="rounded-md border border-border/40 bg-muted/40 p-2">
                              <button
                                type="button"
                                onClick={() => setOpenSqlMsgIds((prev) => ({ ...prev, [msg.id]: !prev[msg.id] }))}
                                className="flex w-full items-center justify-between text-[11px] font-mono text-muted-foreground hover:text-foreground transition-colors"
                              >
                                <span className="flex items-center gap-1.5">
                                  <Code2 className="h-3.5 w-3.5" />
                                  {openSqlMsgIds[msg.id] ? "Hide executed SQL query" : "View executed SQL query"}
                                </span>
                                {openSqlMsgIds[msg.id] ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                              </button>
                              {openSqlMsgIds[msg.id] && (
                                <pre className="mt-2 rounded bg-zinc-950 p-2.5 text-xs text-zinc-100 overflow-x-auto font-mono whitespace-pre-wrap">
                                  <code>{sqlQuery}</code>
                                </pre>
                              )}
                            </div>
                          )
                        })()}

                        <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <span>{msg.results.row_count} rows returned</span>
                          {msg.results.execution_time_ms != null && (
                            <span>· {msg.results.execution_time_ms}ms execution time</span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Quick Follow-up Suggestions */}
                    {msg.role === "assistant" && msg.quick_options && msg.quick_options.length > 0 && (
                      <div className="mt-3 border-t border-border/40 pt-3">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1 mr-0.5">
                            <Lightbulb className="h-3 w-3 text-amber-500" />
                            Suggestions:
                          </span>
                          {msg.quick_options.map((opt, idx) => (
                            <button
                              key={idx}
                              type="button"
                              disabled={isSending}
                              onClick={() => handleOptionClick(opt)}
                              className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-background/90 px-2.5 py-1 text-xs text-foreground transition-all hover:bg-accent hover:border-primary/50 hover:text-primary active:scale-95 disabled:opacity-50"
                            >
                              <span>{opt}</span>
                            </button>
                          ))}
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
        <div className="relative flex gap-3">
          <div className="flex-1 relative">
            <Textarea
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleSuggestionKeyDown}
              placeholder="Ask a follow-up question..."
              rows={2}
              className="resize-none min-h-[2.5rem]"
            />
            {showSuggestions && suggestions.length > 0 && (
              <div
                ref={suggestRef}
                className="absolute bottom-full left-0 right-0 mb-1 rounded-lg border bg-popover shadow-lg"
              >
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    className={`w-full px-3 py-2 text-left text-sm hover:bg-accent ${
                      i === selectedSuggestion ? "bg-accent" : ""
                    }`}
                    onMouseDown={() => handleSuggestionPick(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
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

      {/* High-Priority Security Alert Modal */}
      <SecurityAlertModal
        open={showSecurityModal}
        onOpenChange={setShowSecurityModal}
        alert={securityAlert}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Conversation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{title}&quot;? All messages in this conversation will be permanently removed. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default function ConversationDetailPageWrapper() {
  return (
    <Suspense fallback={null}>
      <ConversationDetailPage />
    </Suspense>
  )
}
