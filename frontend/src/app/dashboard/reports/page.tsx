"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  FileText,
  FileSpreadsheet,
  FileCode,
  Calendar,
  Clock,
  Download,
  Plus,
  Loader2,
  Trash2,
  Eye,
  RefreshCw,
  Printer,
  BarChart3,
  Database,
  Search,
  Sparkles,
  ChevronDown,
  Layers,
  CheckCircle2,
  Table,
} from "lucide-react"
import type { DashboardResponse, DashboardDetailResponse, QueryResponse } from "@/types/api"

export interface ReportWidgetData {
  id: number
  title: string
  widget_type: string
  natural_query?: string
  generated_sql?: string
  columns: string[]
  rows: unknown[][]
  row_count: number
  execution_time_ms?: number | null
}

export interface GeneratedReport {
  id: number
  title: string
  description?: string
  dashboard_id: number
  dashboard_title: string
  format: "pdf" | "csv" | "json" | "html"
  status: "generated" | "generating" | "error"
  created_at: string
  summary: {
    total_widgets: number
    total_records: number
    kpis: { label: string; value: string | number }[]
    insights: string[]
  }
  widgets_data: ReportWidgetData[]
}

export default function ReportsPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [reports, setReports] = useState<GeneratedReport[]>([])
  const [dashboards, setDashboards] = useState<DashboardResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [createOpen, setCreateOpen] = useState(false)
  const [previewReport, setPreviewReport] = useState<GeneratedReport | null>(null)
  const [isRegeneratingId, setIsRegeneratingId] = useState<number | null>(null)

  // Load saved reports from local storage
  const fetchReports = useCallback(() => {
    setLoading(true)
    const stored = localStorage.getItem("generated_reports")
    if (stored) {
      try {
        setReports(JSON.parse(stored))
      } catch {
        setReports([])
      }
    }
    setLoading(false)
  }, [])

  // Fetch available dashboards
  const fetchDashboards = useCallback(async () => {
    try {
      const data = await api.listDashboards({ per_page: 100 })
      setDashboards(data.dashboards || [])
    } catch {
      setDashboards([])
    }
  }, [])

  useEffect(() => {
    fetchReports()
    fetchDashboards()
  }, [fetchReports, fetchDashboards])

  const saveReports = (updated: GeneratedReport[]) => {
    setReports(updated)
    localStorage.setItem("generated_reports", JSON.stringify(updated))
  }

  const handleDelete = (id: number) => {
    saveReports(reports.filter((r) => r.id !== id))
    toast({ title: "Report deleted", variant: "success" })
    if (previewReport?.id === id) {
      setPreviewReport(null)
    }
  }

  // Generate / Regenerate a report by fetching live dashboard and widget queries
  const generateReportData = async (
    dashboardId: number,
    reportTitle: string,
    reportDesc?: string,
    preferredFormat: "pdf" | "csv" | "json" | "html" = "pdf"
  ): Promise<GeneratedReport> => {
    // 1. Fetch dashboard detail
    const dashDetail: DashboardDetailResponse = await api.getDashboardById(dashboardId)
    const widgets = dashDetail.widgets || []

    const widgetsData: ReportWidgetData[] = []
    let totalRecords = 0
    const kpis: { label: string; value: string | number }[] = []
    const insights: string[] = []

    // 2. Fetch queries for each widget
    for (const widget of widgets) {
      let columns: string[] = []
      let rows: unknown[][] = []
      let naturalQuery: string | undefined
      let generatedSql: string | undefined
      let execTime: number | null = null

      if (widget.query_id) {
        try {
          const qRes: QueryResponse = await api.getQueryById(widget.query_id)
          naturalQuery = qRes.natural_language
          generatedSql = qRes.generated_sql || undefined
          execTime = qRes.results?.execution_time_ms ?? null

          if (qRes.results?.columns) {
            columns = qRes.results.columns
          }
          if (qRes.results?.rows) {
            rows = qRes.results.rows
            totalRecords += rows.length
          }
        } catch {
          // If query fetch fails, record widget with empty rows
        }
      }

      // Check if widget acts like a KPI
      if (widget.widget_type === "kpi" || (rows.length === 1 && rows[0]?.length === 1)) {
        const val = rows[0]?.[0]
        if (val !== undefined) {
          kpis.push({
            label: widget.title,
            value: typeof val === "number" ? val.toLocaleString() : String(val),
          })
        }
      }

      widgetsData.push({
        id: widget.id,
        title: widget.title,
        widget_type: widget.widget_type,
        natural_query: naturalQuery,
        generated_sql: generatedSql,
        columns,
        rows,
        row_count: rows.length,
        execution_time_ms: execTime,
      })
    }

    // Add summary insights
    insights.push(`Dashboard contains ${widgets.length} analytics widgets and visualizations.`)
    if (totalRecords > 0) {
      insights.push(`Analyzed ${totalRecords.toLocaleString()} total tabular records across queries.`)
    }
    if (kpis.length > 0) {
      insights.push(`Generated ${kpis.length} key executive metrics and KPI benchmarks.`)
    }

    const report: GeneratedReport = {
      id: Date.now(),
      title: reportTitle.trim() || `${dashDetail.title} Executive Report`,
      description: reportDesc?.trim() || dashDetail.description || "Generated analytics dashboard summary report.",
      dashboard_id: dashboardId,
      dashboard_title: dashDetail.title,
      format: preferredFormat,
      status: "generated",
      created_at: new Date().toISOString(),
      summary: {
        total_widgets: widgets.length,
        total_records: totalRecords,
        kpis,
        insights,
      },
      widgets_data: widgetsData,
    }

    return report
  }

  // Regenerate an existing report
  const handleRegenerate = async (report: GeneratedReport) => {
    setIsRegeneratingId(report.id)
    try {
      const refreshed = await generateReportData(
        report.dashboard_id,
        report.title,
        report.description,
        report.format
      )
      refreshed.id = report.id // preserve ID
      const updatedList = reports.map((r) => (r.id === report.id ? refreshed : r))
      saveReports(updatedList)
      if (previewReport?.id === report.id) {
        setPreviewReport(refreshed)
      }
      toast({ title: "Report updated", description: "Report data refreshed with live database results", variant: "success" })
    } catch {
      toast({ title: "Regeneration failed", description: "Could not refresh dashboard report data", variant: "destructive" })
    } finally {
      setIsRegeneratingId(null)
    }
  }

  // Export handlers
  const downloadCSV = (report: GeneratedReport) => {
    let csvContent = `sep=,\n`
    csvContent += `Report Title,"${report.title.replace(/"/g, '""')}"\n`
    csvContent += `Dashboard,"${report.dashboard_title.replace(/"/g, '""')}"\n`
    csvContent += `Generated At,"${new Date(report.created_at).toLocaleString()}"\n`
    csvContent += `Total Widgets,${report.summary.total_widgets}\n`
    csvContent += `Total Records,${report.summary.total_records}\n\n`

    if (report.summary.kpis.length > 0) {
      csvContent += `--- KEY PERFORMANCE INDICATORS ---\n`
      csvContent += `Metric,Value\n`
      report.summary.kpis.forEach((kpi) => {
        csvContent += `"${String(kpi.label).replace(/"/g, '""')}","${String(kpi.value).replace(/"/g, '""')}"\n`
      })
      csvContent += `\n`
    }

    report.widgets_data.forEach((widget, idx) => {
      csvContent += `--- WIDGET ${idx + 1}: ${widget.title.toUpperCase()} (${widget.widget_type}) ---\n`
      if (widget.natural_query) {
        csvContent += `Query,"${widget.natural_query.replace(/"/g, '""')}"\n`
      }
      if (widget.columns.length > 0) {
        csvContent += widget.columns.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",") + "\n"
        widget.rows.forEach((row) => {
          csvContent += row.map((cell) => (cell === null || cell === undefined ? "" : `"${String(cell).replace(/"/g, '""')}"`)).join(",") + "\n"
        })
      } else {
        csvContent += `No tabular data\n`
      }
      csvContent += `\n`
    })

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    const filename = `${report.title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_${new Date().toISOString().slice(0, 10)}.csv`
    link.setAttribute("href", url)
    link.setAttribute("download", filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    toast({ title: "CSV Downloaded", description: `Saved as ${filename}`, variant: "success" })
  }

  const downloadJSON = (report: GeneratedReport) => {
    const jsonStr = JSON.stringify(report, null, 2)
    const blob = new Blob([jsonStr], { type: "application/json;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    const filename = `${report.title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_${new Date().toISOString().slice(0, 10)}.json`
    link.setAttribute("href", url)
    link.setAttribute("download", filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    toast({ title: "JSON Downloaded", description: `Saved as ${filename}`, variant: "success" })
  }

  const printOrDownloadPDF = (report: GeneratedReport) => {
    const printWindow = window.open("", "_blank")
    if (!printWindow) {
      toast({ title: "Popup Blocked", description: "Please allow popups to print or download PDF", variant: "destructive" })
      return
    }

    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${report.title}</title>
  <style>
    @media print {
      @page { margin: 1.5cm; }
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .no-print { display: none !important; }
      .page-break { page-break-before: always; }
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      background: #ffffff;
      padding: 24px;
      margin: 0;
      line-height: 1.5;
    }
    .header {
      border-bottom: 2px solid #3b82f6;
      padding-bottom: 16px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    .header h1 {
      margin: 0 0 6px 0;
      color: #0f172a;
      font-size: 26px;
    }
    .header p {
      margin: 0;
      color: #64748b;
      font-size: 14px;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      background: #eff6ff;
      color: #2563eb;
      border: 1px solid #bfdbfe;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .kpi-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px;
    }
    .kpi-label {
      font-size: 12px;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }
    .kpi-value {
      font-size: 24px;
      font-weight: 700;
      color: #0f172a;
    }
    .section-title {
      font-size: 18px;
      font-weight: 700;
      color: #1e293b;
      margin: 28px 0 12px 0;
      border-left: 4px solid #3b82f6;
      padding-left: 10px;
    }
    .widget-box {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }
    .widget-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .widget-title {
      font-size: 15px;
      font-weight: 600;
      color: #0f172a;
      margin: 0;
    }
    .widget-type {
      font-size: 11px;
      text-transform: uppercase;
      color: #64748b;
      background: #f1f5f9;
      padding: 2px 8px;
      border-radius: 4px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 8px;
    }
    th {
      background: #f1f5f9;
      color: #334155;
      text-align: left;
      padding: 8px 10px;
      font-weight: 600;
      border-bottom: 1px solid #cbd5e1;
    }
    td {
      padding: 8px 10px;
      border-bottom: 1px solid #f1f5f9;
      color: #334155;
    }
    tr:nth-child(even) td {
      background: #fafafa;
    }
    .footer {
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #94a3b8;
      display: flex;
      justify-content: space-between;
    }
    .print-bar {
      background: #0f172a;
      color: #ffffff;
      padding: 12px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-radius: 8px;
      margin-bottom: 20px;
    }
    .btn {
      background: #2563eb;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="print-bar no-print">
    <div><strong>Ready to Print / Save as PDF</strong></div>
    <button class="btn" onclick="window.print()">Print / Save PDF</button>
  </div>

  <div class="header">
    <div>
      <h1>${report.title}</h1>
      <p>Source Dashboard: <strong>${report.dashboard_title}</strong> • Generated on ${new Date(report.created_at).toLocaleString()}</p>
    </div>
    <div>
      <span class="badge">Executive Report</span>
    </div>
  </div>

  ${
    report.summary.kpis.length > 0
      ? `
    <div class="kpi-grid">
      ${report.summary.kpis
        .map(
          (kpi) => `
        <div class="kpi-card">
          <div class="kpi-label">${kpi.label}</div>
          <div class="kpi-value">${kpi.value}</div>
        </div>
      `
        )
        .join("")}
      <div class="kpi-card">
        <div class="kpi-label">Total Widgets</div>
        <div class="kpi-value">${report.summary.total_widgets}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total Records</div>
        <div class="kpi-value">${report.summary.total_records.toLocaleString()}</div>
      </div>
    </div>
  `
      : ""
  }

  <div class="section-title">Dashboard Widgets & Data Breakdown</div>
  ${report.widgets_data
    .map(
      (w, i) => `
    <div class="widget-box">
      <div class="widget-header">
        <h3 class="widget-title">${i + 1}. ${w.title}</h3>
        <span class="widget-type">${w.widget_type} (${w.row_count} rows)</span>
      </div>
      ${w.natural_query ? `<p style="font-size:12px;color:#64748b;margin:0 0 8px 0;"><strong>Query:</strong> ${w.natural_query}</p>` : ""}
      ${
        w.columns.length > 0
          ? `
        <table>
          <thead>
            <tr>${w.columns.map((c) => `<th>${c}</th>`).join("")}</tr>
          </thead>
          <tbody>
            ${w.rows
              .slice(0, 100)
              .map(
                (row) => `
              <tr>${row.map((val) => `<td>${val === null || val === undefined ? "-" : String(val)}</td>`).join("")}</tr>
            `
              )
              .join("")}
          </tbody>
        </table>
        ${w.rows.length > 100 ? `<p style="font-size:11px;color:#94a3b8;margin-top:4px;">Showing first 100 of ${w.rows.length} rows</p>` : ""}
      `
          : `<p style="font-size:12px;color:#94a3b8;margin:0;">No tabular data returned.</p>`
      }
    </div>
  `
    )
    .join("")}

  <div class="footer">
    <span>Data Analytics Platform • Executive Intelligence</span>
    <span>Generated: ${new Date(report.created_at).toISOString()}</span>
  </div>
</body>
</html>
`

    printWindow.document.open()
    printWindow.document.write(htmlContent)
    printWindow.document.close()
  }

  const handleDownload = (report: GeneratedReport, format: "pdf" | "csv" | "json") => {
    if (format === "csv") {
      downloadCSV(report)
    } else if (format === "json") {
      downloadJSON(report)
    } else {
      printOrDownloadPDF(report)
    }
  }

  const filteredReports = reports.filter((r) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return r.title.toLowerCase().includes(q) || r.dashboard_title.toLowerCase().includes(q)
  })

  return (
    <div className="space-y-6">
      {/* PAGE HEADER */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground">
            Generate, customize, and export executive analytics reports directly from your dashboards.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setCreateOpen(true)} className="bg-primary text-primary-foreground">
            <Plus className="mr-2 h-4 w-4" /> Generate Report
          </Button>
        </div>
      </div>

      {/* SEARCH AND FILTERS */}
      {reports.length > 0 && (
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search reports by title or dashboard..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>
      )}

      {/* CONTENT LIST */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : reports.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
              <FileText className="h-8 w-8" />
            </div>
            <h3 className="text-lg font-semibold">No reports generated yet</h3>
            <p className="text-muted-foreground text-sm max-w-md mt-1 mb-6">
              Select a dashboard to automatically aggregate widgets, queries, and KPI metrics into a downloadable PDF, CSV, or JSON report.
            </p>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" /> Generate Your First Report
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
          {filteredReports.map((report) => (
            <Card key={report.id} className="transition-shadow hover:shadow-md">
              <CardHeader className="p-4 pb-2 flex flex-row items-start justify-between gap-2">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <BarChart3 className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-base font-semibold leading-tight line-clamp-1">
                      {report.title}
                    </CardTitle>
                    <CardDescription className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                      <span className="flex items-center gap-1 font-medium text-foreground/80">
                        <Database className="h-3 w-3" /> {report.dashboard_title}
                      </span>
                      <span>•</span>
                      <span>{new Date(report.created_at).toLocaleDateString()}</span>
                    </CardDescription>
                  </div>
                </div>

                <Badge
                  variant="outline"
                  className="capitalize bg-emerald-500/10 text-emerald-600 border-emerald-300 text-[11px] font-medium shrink-0"
                >
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Ready
                </Badge>
              </CardHeader>

              <CardContent className="p-4 pt-2 space-y-3">
                {report.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {report.description}
                  </p>
                )}

                {/* Metrics Summary Strip */}
                <div className="grid grid-cols-3 gap-2 rounded-md bg-muted/40 p-2 text-center text-xs">
                  <div>
                    <span className="text-[10px] text-muted-foreground block uppercase font-medium">Widgets</span>
                    <span className="font-semibold text-sm">{report.summary.total_widgets}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block uppercase font-medium">Records</span>
                    <span className="font-semibold text-sm">{report.summary.total_records.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block uppercase font-medium">KPIs</span>
                    <span className="font-semibold text-sm">{report.summary.kpis.length}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-1 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs gap-1.5"
                    onClick={() => setPreviewReport(report)}
                  >
                    <Eye className="h-3.5 w-3.5 text-muted-foreground" /> View Report
                  </Button>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-foreground"
                      title="Refresh live data"
                      onClick={() => handleRegenerate(report)}
                      disabled={isRegeneratingId === report.id}
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${isRegeneratingId === report.id ? "animate-spin text-primary" : ""}`} />
                    </Button>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button size="sm" className="h-8 text-xs gap-1">
                          <Download className="h-3.5 w-3.5" /> Download <ChevronDown className="h-3 w-3 ml-0.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuLabel className="text-xs">Select Format</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleDownload(report, "pdf")} className="cursor-pointer text-xs">
                          <Printer className="mr-2 h-3.5 w-3.5 text-blue-600" /> Print / Save as PDF
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDownload(report, "csv")} className="cursor-pointer text-xs">
                          <FileSpreadsheet className="mr-2 h-3.5 w-3.5 text-emerald-600" /> Export CSV Spreadsheet
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDownload(report, "json")} className="cursor-pointer text-xs">
                          <FileCode className="mr-2 h-3.5 w-3.5 text-purple-600" /> Export JSON Payload
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      title="Delete report"
                      onClick={() => handleDelete(report.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* CREATE / GENERATE REPORT MODAL */}
      <CreateReportDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        dashboards={dashboards}
        onGenerate={generateReportData}
        onCreated={(newReport) => {
          saveReports([newReport, ...reports])
          setCreateOpen(false)
          setPreviewReport(newReport)
          toast({
            title: "Report Generated!",
            description: `Successfully created "${newReport.title}" with ${newReport.summary.total_widgets} widgets.`,
            variant: "success",
          })
        }}
      />

      {/* VIEW / PREVIEW REPORT MODAL */}
      {previewReport && (
        <ReportPreviewModal
          report={previewReport}
          open={!!previewReport}
          onOpenChange={(open) => !open && setPreviewReport(null)}
          onDownload={handleDownload}
          onRegenerate={handleRegenerate}
          isRegenerating={isRegeneratingId === previewReport.id}
        />
      )}
    </div>
  )
}

// Dialog for selecting dashboard and generating report
function CreateReportDialog({
  open,
  onOpenChange,
  dashboards,
  onGenerate,
  onCreated,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  dashboards: DashboardResponse[]
  onGenerate: (
    dbId: number,
    title: string,
    desc?: string,
    format?: "pdf" | "csv" | "json" | "html"
  ) => Promise<GeneratedReport>
  onCreated: (report: GeneratedReport) => void
}) {
  const [selectedDbId, setSelectedDbId] = useState<string>("")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [generating, setGenerating] = useState(false)

  // Auto-populate title when dashboard changes
  const handleDashboardSelect = (dbId: string) => {
    setSelectedDbId(dbId)
    const target = dashboards.find((d) => String(d.id) === dbId)
    if (target) {
      setTitle(`${target.title} - Analytics Report`)
      if (target.description) {
        setDescription(target.description)
      }
    }
  }

  const handleGenerate = async () => {
    if (!selectedDbId || !title.trim()) return
    setGenerating(true)
    try {
      const report = await onGenerate(Number(selectedDbId), title.trim(), description.trim(), "pdf")
      onCreated(report)
      setSelectedDbId("")
      setTitle("")
      setDescription("")
    } finally {
      setGenerating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" /> Generate Dashboard Report
          </DialogTitle>
          <DialogDescription>
            Select a dashboard to automatically compile its charts, KPIs, and data tables into an executive report.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Dashboard Selector */}
          <div className="space-y-2">
            <Label htmlFor="report-dashboard">Source Dashboard <span className="text-destructive">*</span></Label>
            <Select value={selectedDbId} onValueChange={handleDashboardSelect}>
              <SelectTrigger id="report-dashboard">
                <SelectValue placeholder="Choose a dashboard..." />
              </SelectTrigger>
              <SelectContent>
                {dashboards.map((db) => (
                  <SelectItem key={db.id} value={String(db.id)}>
                    {db.title} ({db.widget_count || 0} widgets)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Report Title */}
          <div className="space-y-2">
            <Label htmlFor="report-title">Report Title <span className="text-destructive">*</span></Label>
            <Input
              id="report-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Q3 Sales & Revenue Report"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="report-description">Executive Summary / Notes</Label>
            <Textarea
              id="report-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Key takeaways, context, or report objectives..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={generating || !selectedDbId || !title.trim()}
            className="bg-primary text-primary-foreground"
          >
            {generating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Compiling Data...
              </>
            ) : (
              <>
                <FileText className="mr-2 h-4 w-4" /> Generate Report
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// Modal for full in-app preview of generated report
function ReportPreviewModal({
  report,
  open,
  onOpenChange,
  onDownload,
  onRegenerate,
  isRegenerating,
}: {
  report: GeneratedReport
  open: boolean
  onOpenChange: (o: boolean) => void
  onDownload: (report: GeneratedReport, format: "pdf" | "csv" | "json") => void
  onRegenerate: (report: GeneratedReport) => void
  isRegenerating: boolean
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] h-[90vh] flex flex-col p-0 overflow-hidden shadow-2xl">
        {/* MODAL HEADER (Fixed) */}
        <div className="shrink-0 border-b p-6 pb-4 bg-muted/20">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/20">
                  {report.dashboard_title}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  Generated {new Date(report.created_at).toLocaleString()}
                </span>
              </div>
              <h2 className="text-xl font-bold tracking-tight">{report.title}</h2>
              {report.description && (
                <p className="text-sm text-muted-foreground mt-1">{report.description}</p>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={() => onRegenerate(report)}
                disabled={isRegenerating}
              >
                <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isRegenerating ? "animate-spin text-primary" : ""}`} />
                {isRegenerating ? "Refreshing..." : "Refresh Data"}
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" className="h-8 text-xs gap-1.5 bg-primary">
                    <Download className="h-3.5 w-3.5" /> Download Report <ChevronDown className="h-3 w-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-52">
                  <DropdownMenuItem onClick={() => onDownload(report, "pdf")} className="cursor-pointer text-xs">
                    <Printer className="mr-2 h-3.5 w-3.5 text-blue-600" /> Save as PDF / Print
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onDownload(report, "csv")} className="cursor-pointer text-xs">
                    <FileSpreadsheet className="mr-2 h-3.5 w-3.5 text-emerald-600" /> Download CSV Spreadsheet
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onDownload(report, "json")} className="cursor-pointer text-xs">
                    <FileCode className="mr-2 h-3.5 w-3.5 text-purple-600" /> Download JSON Data
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        {/* MODAL BODY (Vertically Scrollable) */}
        <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-6">
          {/* KPI CARDS */}
          {report.summary.kpis.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider text-[11px]">
                Key Performance Indicators
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {report.summary.kpis.map((kpi, idx) => (
                  <div key={idx} className="rounded-lg border bg-card p-3 shadow-sm">
                    <p className="text-[11px] font-medium text-muted-foreground truncate">{kpi.label}</p>
                    <p className="text-lg font-bold text-foreground mt-0.5">{kpi.value}</p>
                  </div>
                ))}
                <div className="rounded-lg border bg-card p-3 shadow-sm">
                  <p className="text-[11px] font-medium text-muted-foreground">Total Records</p>
                  <p className="text-lg font-bold text-foreground mt-0.5">{report.summary.total_records.toLocaleString()}</p>
                </div>
                <div className="rounded-lg border bg-card p-3 shadow-sm">
                  <p className="text-[11px] font-medium text-muted-foreground">Widgets Analyzed</p>
                  <p className="text-lg font-bold text-foreground mt-0.5">{report.summary.total_widgets}</p>
                </div>
              </div>
            </div>
          )}

          {/* WIDGETS DATA TABLES */}
          <div className="space-y-5">
            <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider text-[11px]">
              Widget Breakdowns & Data Tables
            </h3>

            {report.widgets_data.map((w, idx) => (
              <div key={w.id} className="rounded-lg border bg-card overflow-hidden shadow-sm">
                <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-[10px] font-bold">
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-sm">{w.title}</span>
                  </div>
                  <Badge variant="secondary" className="text-[10px] uppercase font-mono">
                    {w.widget_type} • {w.row_count} rows
                  </Badge>
                </div>

                <div className="p-4 space-y-3">
                  {w.natural_query && (
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">Query:</span> {w.natural_query}
                    </p>
                  )}

                  {w.columns.length > 0 ? (
                    <div className="rounded border overflow-x-auto max-h-64">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-muted/50 border-b font-medium text-muted-foreground sticky top-0 bg-background/95 backdrop-blur-xs">
                          <tr>
                            {w.columns.map((col, cIdx) => (
                              <th key={cIdx} className="p-2 px-3 font-semibold whitespace-nowrap">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {w.rows.slice(0, 50).map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-muted/30">
                              {row.map((cell, cellIdx) => (
                                <td key={cellIdx} className="p-2 px-3 whitespace-nowrap text-foreground/80">
                                  {cell === null || cell === undefined ? "-" : String(cell)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground italic">No tabular data records for this widget.</p>
                  )}

                  {w.rows.length > 50 && (
                    <p className="text-[11px] text-muted-foreground text-right">
                      Showing 50 of {w.rows.length} rows. Full dataset included in downloads.
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* MODAL FOOTER (Fixed) */}
        <div className="shrink-0 border-t p-4 bg-muted/10 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {report.widgets_data.length} widgets compiled
          </span>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
