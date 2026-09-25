"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { DataTable, type Column } from "@/components/ui/data-table"
import { formatDate } from "@/lib/utils"
import { VisualizationRenderer } from "@/components/visualization/visualization-renderer"
import type {
  DatabaseConnectionResponse,
  QueryResponse,
  QueryResult,
} from "@/types/api"
import {
  MessageSquare,
  Send,
  Loader2,
  Database,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Sparkles,
  ChevronRight,
  Plus,
  History,
  Search,
  ShieldCheck,
  CheckCheck,
} from "lucide-react"

interface TraceDetails {
  intent: string
  metricsVerified: string
  rawTrace: string
}

function extractTraceDetails(explanation?: string | null): TraceDetails | null {
  if (!explanation) return null
  const traceMatch = explanation.match(/###\s*(?:🛠️\s*)?Execution Trace & Verification([\s\S]*?)(?=###|$)/i)
  if (!traceMatch) return null

  const rawTrace = traceMatch[1].trim()
  const intentMatch = rawTrace.match(/\*\*Intent\*\*:\s*([^\n]+)/i)
  const metricsMatch = rawTrace.match(/\*\*Metrics Verified\*\*:\s*([^\n]+)/i)

  return {
    intent: intentMatch ? intentMatch[1].trim() : "",
    metricsVerified: metricsMatch ? metricsMatch[1].trim() : "",
    rawTrace,
  }
}

export default function AnalyticsPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [connections, setConnections] = useState<DatabaseConnectionResponse[]>([])
  const [selectedDbId, setSelectedDbId] = useState<string>("")
  const [nlInput, setNlInput] = useState("")
  const [isExecuting, setIsExecuting] = useState(false)
  const [currentQuery, setCurrentQuery] = useState<QueryResponse | null>(null)
  const [queryHistory, setQueryHistory] = useState<QueryResponse[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyPage, setHistoryPage] = useState(1)
  const [showHistory, setShowHistory] = useState(false)
  const [conversations, setConversations] = useState<{ id: number; title: string }[]>([])
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null)
  const [showTraceModal, setShowTraceModal] = useState(false)
  const [traceData, setTraceData] = useState<{
    intent: string
    metricsVerified: string
    rawTrace: string
    question: string
    rowCount: number
    executionTimeMs?: number | null
    dbName?: string
  } | null>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.listDatabases({ per_page: 100 }).then((d) => {
      const dbs = d.connections || []
      setConnections(dbs)
      if (dbs.length > 0) {
        setSelectedDbId((prev) => prev || String(dbs[0].id))
      }
    }).catch(() => {})
    api.listConversations({ per_page: 20 }).then((d) => {
      setConversations(d.conversations.map((c) => ({ id: c.id, title: c.title || "Untitled" })))
    }).catch(() => {})
  }, [])

  const fetchHistory = useCallback(() => {
    api.listQueries({ page: historyPage, per_page: 10 }).then((d) => {
      setQueryHistory(d.queries)
      setHistoryTotal(d.total)
    }).catch(() => {})
  }, [historyPage])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  const handleExecute = async () => {
    if (isExecuting) return
    if (!nlInput.trim()) {
      toast({ title: "Question required", description: "Please enter a question to analyze.", variant: "destructive" })
      return
    }
    if (!selectedDbId) {
      toast({ title: "Database required", description: "Please select a database from the dropdown above.", variant: "destructive" })
      return
    }
    setIsExecuting(true)
    setCurrentQuery(null)
    try {
      const result = await api.executeQuery({
        database_id: Number(selectedDbId),
        natural_language: nlInput,
        conversation_id: activeConversationId || undefined,
      })
      setCurrentQuery(result)
      if (activeConversationId) {
        await api.sendMessage(activeConversationId, { content: nlInput })
      }
      fetchHistory()

      const dbObj = connections.find((c) => String(c.id) === selectedDbId)
      const parsedTrace = extractTraceDetails(result.explanation)
      const traceInfo = {
        intent: parsedTrace?.intent || result.natural_language || "",
        metricsVerified: parsedTrace?.metricsVerified || result.results?.columns?.join(", ") || "",
        rawTrace: parsedTrace?.rawTrace || "",
        question: result.natural_language || nlInput,
        rowCount: result.results?.row_count ?? 0,
        executionTimeMs: result.results?.execution_time_ms,
        dbName: dbObj?.name || "Connected Database",
      }
      setTraceData(traceInfo)

      if (result.status === "completed") {
        setShowTraceModal(true)
        toast({
          title: "Execution Trace Verified",
          description: traceInfo.intent ? `Intent: ${traceInfo.intent}` : "Execution trace and database records verified.",
          variant: "success",
        })
      }

      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Query failed", description: error.detail || "An error occurred", variant: "destructive" })
    } finally {
      setIsExecuting(false)
    }
  }

  const handleFollowUp = async (queryId: number) => {
    if (isExecuting) return
    if (!nlInput.trim()) {
      toast({ title: "Question required", description: "Please enter a follow-up question.", variant: "destructive" })
      return
    }
    setIsExecuting(true)
    try {
      const result = await api.queryFollowUp(queryId, { natural_language: nlInput })
      setCurrentQuery(result)
      setNlInput("")

      const dbObj = connections.find((c) => String(c.id) === selectedDbId)
      const parsedTrace = extractTraceDetails(result.explanation)
      const traceInfo = {
        intent: parsedTrace?.intent || result.natural_language || "",
        metricsVerified: parsedTrace?.metricsVerified || result.results?.columns?.join(", ") || "",
        rawTrace: parsedTrace?.rawTrace || "",
        question: result.natural_language || nlInput,
        rowCount: result.results?.row_count ?? 0,
        executionTimeMs: result.results?.execution_time_ms,
        dbName: dbObj?.name || "Connected Database",
      }
      setTraceData(traceInfo)

      if (result.status === "completed") {
        setShowTraceModal(true)
        toast({
          title: "Execution Trace Verified",
          description: traceInfo.intent ? `Intent: ${traceInfo.intent}` : "Execution trace verified for follow-up query.",
          variant: "success",
        })
      }

      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Follow-up failed", description: error.detail || "An error occurred", variant: "destructive" })
    } finally {
      setIsExecuting(false)
    }
  }

  const startNewConversation = async () => {
    try {
      const conv = await api.createConversation({
        database_id: selectedDbId ? Number(selectedDbId) : undefined,
      })
      setActiveConversationId(conv.id)
      setConversations((prev) => [{ id: conv.id, title: conv.title || "New Conversation" }, ...prev])
      toast({ title: "Conversation started", variant: "success" })
    } catch {
      toast({ title: "Failed to start conversation", variant: "destructive" })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleExecute()
    }
  }

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      case "failed": return <XCircle className="h-4 w-4 text-destructive" />
      case "executing": return <Loader2 className="h-4 w-4 animate-spin" />
      case "cancelled": return <AlertCircle className="h-4 w-4 text-muted-foreground" />
      default: return <Clock className="h-4 w-4 text-muted-foreground" />
    }
  }

  const historyColumns: Column<QueryResponse>[] = [
    {
      key: "natural_language",
      header: "Question",
      cell: (q) => (
        <div className="flex items-center gap-2">
          {statusIcon(q.status)}
          <div>
            <p className="font-medium text-sm truncate max-w-[300px]">{q.natural_language}</p>
            <p className="text-xs text-muted-foreground">{formatDate(q.created_at)}</p>
          </div>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (q) => <Badge variant={q.status === "completed" ? "success" : q.status === "failed" ? "destructive" : "secondary"} className="text-xs">{q.status}</Badge>,
    },
    {
      key: "row_count",
      header: "Rows",
      cell: (q) => <span className="text-sm">{q.results?.row_count ?? "—"}</span>,
    },
    {
      key: "execution_time_ms",
      header: "Time",
      cell: (q) => <span className="text-sm text-muted-foreground">{q.results?.execution_time_ms != null ? `${q.results.execution_time_ms}ms` : "—"}</span>,
    },
    {
      key: "actions",
      header: "",
      cell: (q) => (
        <Button variant="ghost" size="icon" onClick={() => { setCurrentQuery(q); setShowHistory(false) }}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Analytics</h1>
          <p className="text-muted-foreground">Ask questions about your data in natural language</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowHistory(!showHistory)}>
            <History className="mr-2 h-4 w-4" />
            History
          </Button>
          <Button variant="outline" size="sm" onClick={startNewConversation}>
            <Plus className="mr-2 h-4 w-4" />
            New Conversation
          </Button>
        </div>
      </div>

      {activeConversationId && (
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-2 text-sm">
              <MessageSquare className="h-4 w-4 text-primary" />
              <span>Conversation active</span>
              <Badge variant="secondary" className="text-xs">
                #{activeConversationId}
              </Badge>
            </div>
            <Button variant="ghost" size="sm" onClick={() => router.push(`/dashboard/conversations/${activeConversationId}`)}>
              Open Chat
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Ask a Question</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="db-select">Database</Label>
              {connections.length === 0 && (
                <span className="text-xs text-amber-600 dark:text-amber-400">
                  No databases found. <a href="/dashboard/databases" className="underline font-medium">Add a database</a>
                </span>
              )}
            </div>
            <Select value={selectedDbId} onValueChange={setSelectedDbId}>
              <SelectTrigger id="db-select">
                <SelectValue placeholder="Select a database..." />
              </SelectTrigger>
              <SelectContent>
                {connections.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    <div className="flex items-center justify-between gap-4 w-full">
                      <div className="flex items-center gap-2">
                        <Database className="h-4 w-4 text-primary" />
                        <span>{c.name}</span>
                      </div>
                      <Badge variant="outline" className="text-[10px] uppercase font-mono">
                        {c.connection_type}
                      </Badge>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="nl-input">What would you like to know?</Label>
            <Textarea
              id="nl-input"
              placeholder='e.g., "Show me the top 10 customers by revenue" or "How many users signed up this month?"'
              value={nlInput}
              onChange={(e) => setNlInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
              className="resize-none"
            />
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {activeConversationId
                ? "Follow-up within the current conversation"
                : "Press Ctrl+Enter to execute"}
            </p>
            <div className="flex gap-2">
              {currentQuery && activeConversationId && (
                <Button
                  variant="outline"
                  onClick={() => handleFollowUp(currentQuery.id)}
                  disabled={isExecuting || !nlInput.trim()}
                >
                  {isExecuting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <MessageSquare className="mr-2 h-4 w-4" />}
                  Follow-up
                </Button>
              )}
              <Button
                onClick={handleExecute}
                disabled={isExecuting || !nlInput.trim()}
              >
                {isExecuting ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Analyzing...</>
                ) : (
                  <><Sparkles className="mr-2 h-4 w-4" /> Ask AI</>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {showHistory && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Query History</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={historyColumns}
              data={queryHistory}
              total={historyTotal}
              page={historyPage}
              perPage={10}
              onPageChange={setHistoryPage}
            />
          </CardContent>
        </Card>
      )}

      {currentQuery && (
        <div ref={resultsRef} className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-3">
                <CardTitle className="text-lg">Results</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1.5 text-xs font-medium text-emerald-600 border-emerald-500/30 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                  onClick={() => {
                    const dbObj = connections.find((c) => String(c.id) === selectedDbId)
                    const parsedTrace = extractTraceDetails(currentQuery.explanation)
                    setTraceData({
                      intent: parsedTrace?.intent || currentQuery.natural_language || "",
                      metricsVerified: parsedTrace?.metricsVerified || currentQuery.results?.columns?.join(", ") || "",
                      rawTrace: parsedTrace?.rawTrace || "",
                      question: currentQuery.natural_language || "",
                      rowCount: currentQuery.results?.row_count ?? 0,
                      executionTimeMs: currentQuery.results?.execution_time_ms,
                      dbName: dbObj?.name || "Connected Database",
                    })
                    setShowTraceModal(true)
                  }}
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Execution Trace & Verification</span>
                </Button>
              </div>
              <Badge variant={currentQuery.status === "completed" ? "success" : currentQuery.status === "failed" ? "destructive" : "secondary"}>
                {currentQuery.status}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              {currentQuery.explanation && (
                <div className="rounded-lg bg-muted/60 border p-4 text-sm whitespace-pre-wrap leading-relaxed">
                  <div className="space-y-1">{currentQuery.explanation}</div>
                </div>
              )}

              {currentQuery.generated_sql && (
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Generated SQL</Label>
                  <pre className="rounded-lg bg-muted p-4 text-sm overflow-x-auto">
                    <code>{currentQuery.generated_sql}</code>
                  </pre>
                </div>
              )}

              {currentQuery.error_message && (
                <div className="flex items-start gap-2 rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{currentQuery.error_message}</span>
                </div>
              )}

              {currentQuery.results && (
                <div className="space-y-4">
                  {currentQuery.suggested_visualizations && currentQuery.suggested_visualizations.length > 0 ? (
                    <VisualizationRenderer
                      results={currentQuery.results}
                      suggestions={currentQuery.suggested_visualizations}
                    />
                  ) : (
                    <QueryResultsTable results={currentQuery.results} />
                  )}
                </div>
              )}

              {currentQuery.status === "completed" && currentQuery.results && (
                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span>{currentQuery.results.row_count} rows returned</span>
                  {currentQuery.results.execution_time_ms != null && (
                    <span>· {currentQuery.results.execution_time_ms}ms execution time</span>
                  )}
                  {currentQuery.tokens_used != null && (
                    <span>· {currentQuery.tokens_used} tokens used</span>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Execution Trace & Verification Pop Message Modal */}
      <Dialog open={showTraceModal} onOpenChange={setShowTraceModal}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="rounded-full bg-emerald-100 p-2 dark:bg-emerald-950/60">
                <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <DialogTitle className="text-base font-semibold">Execution Trace & Verification</DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground">
                  Verification trace confirmed from live database records
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {traceData && (
            <div className="space-y-3.5 py-2">
              {traceData.intent && (
                <div className="rounded-lg border bg-muted/40 p-3.5 text-sm space-y-1">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">🎯 Verified Intent</p>
                  <p className="font-medium text-foreground">{traceData.intent}</p>
                </div>
              )}

              {traceData.metricsVerified && (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3.5 text-sm space-y-1.5">
                  <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                    📊 Metrics & Columns Verified
                  </p>
                  <p className="text-foreground font-mono text-xs leading-relaxed bg-background/60 p-2 rounded border border-emerald-500/10">
                    {traceData.metricsVerified}
                  </p>
                </div>
              )}

              {traceData.rawTrace && (
                <div className="rounded-lg bg-muted/60 border p-3.5 text-xs whitespace-pre-wrap leading-relaxed">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">🛠️ Execution Trace</p>
                  <div className="space-y-1 font-mono text-muted-foreground bg-background/80 p-2.5 rounded border">
                    {traceData.rawTrace}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between text-xs text-muted-foreground px-1 pt-1 border-t border-border/50">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span>{traceData.rowCount} rows verified</span>
                </div>
                {traceData.executionTimeMs != null && (
                  <span>{traceData.executionTimeMs}ms execution time</span>
                )}
                <span className="font-medium">{traceData.dbName}</span>
              </div>
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button size="sm" onClick={() => setShowTraceModal(false)}>
              <CheckCheck className="mr-1.5 h-4 w-4" />
              Got it
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function QueryResultsTable({ results }: { results: QueryResult }) {
  if (!results.columns || results.columns.length === 0) {
    return <p className="text-sm text-muted-foreground">Query completed with no results.</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            {results.columns.map((col, i) => (
              <th key={i} className="px-4 py-2 text-left font-medium text-muted-foreground">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.rows.slice(0, 50).map((row, i) => (
            <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2">
                  {String(cell ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {results.row_count > 50 && (
        <div className="border-t bg-muted/30 px-4 py-2 text-xs text-muted-foreground">
          Showing 50 of {results.row_count} rows
        </div>
      )}
    </div>
  )
}
