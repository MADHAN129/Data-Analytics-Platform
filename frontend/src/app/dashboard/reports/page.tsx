"use client"

import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  FileText, Calendar, Clock, Download, Plus, Loader2, BarChart3,
} from "lucide-react"
import type { DashboardResponse } from "@/types/api"

type Report = {
  id: number
  title: string
  dashboard_id: number | null
  dashboard_title?: string
  schedule: string | null
  format: "csv" | "pdf"
  status: "generated" | "pending" | "error"
  created_at: string
}

export default function ReportsPage() {
  const { toast } = useToast()
  const [reports, setReports] = useState<Report[]>([])
  const [dashboards, setDashboards] = useState<DashboardResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)

  const fetchReports = useCallback(() => {
    setLoading(true)
    const stored = localStorage.getItem("reports")
    if (stored) {
      try { setReports(JSON.parse(stored)) } catch { setReports([]) }
    }
    setLoading(false)
  }, [])

  const fetchDashboards = useCallback(async () => {
    try {
      const data = await api.listDashboards({ per_page: 50 })
      setDashboards(data.dashboards)
    } catch {
      setDashboards([])
    }
  }, [])

  useEffect(() => { fetchReports(); fetchDashboards() }, [fetchReports, fetchDashboards])

  const saveReports = (updated: Report[]) => {
    setReports(updated)
    localStorage.setItem("reports", JSON.stringify(updated))
  }

  const handleDelete = (id: number) => {
    saveReports(reports.filter((r) => r.id !== id))
    toast({ title: "Report deleted", variant: "success" })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reports</h1>
          <p className="text-muted-foreground">Generate and manage scheduled reports</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Report
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : reports.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">No reports yet</p>
            <p className="text-muted-foreground mb-4">Create your first report to export dashboard data</p>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Report
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <Card key={report.id}>
              <CardHeader className="flex flex-row items-center justify-between py-3 px-4">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <CardTitle className="text-sm font-medium">{report.title}</CardTitle>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                      {report.dashboard_title && <span>From: {report.dashboard_title}</span>}
                      <span className="uppercase text-[10px]">{report.format}</span>
                      {report.schedule && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {report.schedule}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={report.status === "generated" ? "success" : report.status === "error" ? "destructive" : "secondary"}>
                    {report.status}
                  </Badge>
                  <Button variant="ghost" size="icon" className="h-7 w-7" title="Download">
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7" title="Delete" onClick={() => handleDelete(report.id)}>
                    <Loader2 className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      <CreateReportDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        dashboards={dashboards}
        onCreated={(report) => {
          saveReports([report, ...reports])
          setCreateOpen(false)
          toast({ title: "Report created", variant: "success" })
        }}
      />
    </div>
  )
}

function CreateReportDialog({
  open, onOpenChange, dashboards, onCreated,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  dashboards: DashboardResponse[]
  onCreated: (report: Report) => void
}) {
  const [title, setTitle] = useState("")
  const [dashboardId, setDashboardId] = useState<number | "">("")
  const [format, setFormat] = useState<"csv" | "pdf">("csv")
  const [schedule, setSchedule] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const handleCreate = async () => {
    if (!title.trim()) return
    setSubmitting(true)
    try {
      const db = dashboards.find((d) => d.id === dashboardId)
      const report: Report = {
        id: Date.now(),
        title: title.trim(),
        dashboard_id: dashboardId ? Number(dashboardId) : null,
        dashboard_title: db?.title,
        schedule: schedule.trim() || null,
        format,
        status: "pending",
        created_at: new Date().toISOString(),
      }
      onCreated(report)
      setTitle("")
      setDashboardId("")
      setFormat("csv")
      setSchedule("")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Report</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="report-title">Report Title</Label>
            <Input id="report-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Weekly Sales Summary" />
          </div>
          <div className="space-y-2">
            <Label>Source Dashboard</Label>
            <Select value={dashboardId ? String(dashboardId) : ""} onValueChange={(v) => setDashboardId(Number(v))}>
              <SelectTrigger>
                <SelectValue placeholder="Select a dashboard (optional)" />
              </SelectTrigger>
              <SelectContent>
                {dashboards.map((db) => (
                  <SelectItem key={db.id} value={String(db.id)}>{db.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Format</Label>
              <Select value={format} onValueChange={(v) => setFormat(v as "csv" | "pdf")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="csv">CSV</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Schedule (optional)</Label>
              <Select value={schedule} onValueChange={setSchedule}>
                <SelectTrigger>
                  <SelectValue placeholder="One-time only" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">One-time only</SelectItem>
                  <SelectItem value="Daily">Daily</SelectItem>
                  <SelectItem value="Weekly">Weekly</SelectItem>
                  <SelectItem value="Monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={submitting || !title.trim()}>
            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Create Report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
