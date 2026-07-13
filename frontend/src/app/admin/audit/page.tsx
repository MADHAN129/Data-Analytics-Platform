"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { DataTable, type Column } from "@/components/ui/data-table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { AuditLogResponse } from "@/types/api"
import { formatDate } from "@/lib/utils"
import { Search, Clock } from "lucide-react"

export default function AdminAuditPage() {
  const [logs, setLogs] = useState<AuditLogResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [action, setAction] = useState<string>("")
  const [status, setStatus] = useState<string>("")
  const [isLoading, setIsLoading] = useState(true)
  const { toast } = useToast()

  const perPage = 50

  const fetchLogs = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await api.listAuditLogs({
        page,
        per_page: perPage,
        action: action || undefined,
        status: (status as "success" | "failure") || undefined,
        sort_by: "created_at",
        sort_order: "desc",
      })
      setLogs(data.logs)
      setTotal(data.total)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to load audit logs", variant: "destructive" })
    } finally {
      setIsLoading(false)
    }
  }, [page, perPage, action, status, toast])

  useEffect(() => { fetchLogs() }, [fetchLogs])

  const actionOptions = [
    { value: "login", label: "Login" },
    { value: "logout", label: "Logout" },
    { value: "register", label: "Register" },
    { value: "user.create", label: "User Create" },
    { value: "user.update", label: "User Update" },
    { value: "user.delete", label: "User Delete" },
    { value: "role.create", label: "Role Create" },
    { value: "role.update", label: "Role Update" },
    { value: "role.delete", label: "Role Delete" },
  ]

  const columns: Column<AuditLogResponse>[] = [
    {
      key: "timestamp",
      header: "Timestamp",
      cell: (log) => (
        <div className="flex items-center gap-2">
          <Clock className="h-3 w-3 text-muted-foreground" />
          <span className="text-sm">{formatDate(log.created_at)}</span>
        </div>
      ),
    },
    {
      key: "user",
      header: "User",
      cell: (log) => <span className="text-sm font-medium">{log.user_email}</span>,
    },
    {
      key: "action",
      header: "Action",
      cell: (log) => (
        <Badge variant="outline" className="text-xs font-mono">
          {log.action}
        </Badge>
      ),
    },
    {
      key: "resource",
      header: "Resource",
      cell: (log) => (
        <div>
          <span className="text-sm">{log.resource_type}</span>
          {log.resource_id && (
            <span className="text-xs text-muted-foreground ml-1">#{log.resource_id}</span>
          )}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (log) => (
        <Badge variant={log.status === "success" ? "success" : "destructive"} className="text-xs">
          {log.status}
        </Badge>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Audit Logs</h1>
        <p className="text-muted-foreground">Track all system activities and changes</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Search by user email..." className="pl-9" />
            </div>
            <Select value={action} onValueChange={setAction}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All actions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value=" ">All actions</SelectItem>
                {actionOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value=" ">All statuses</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="failure">Failure</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={logs}
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
