"use client"

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
  AreaChart, Area,
} from "recharts"
import type { QueryResult, VisualizationSuggestion } from "@/types/api"

const FALLBACK_COLORS = [
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#ef4444", // Rose
  "#8b5cf6", // Purple
  "#06b6d4", // Cyan
  "#ec4899", // Pink
  "#f97316", // Orange
  "#14b8a6", // Teal
  "#6366f1", // Indigo
  "#84cc16", // Lime
  "#eab308", // Yellow
]

function getColor(i: number): string {
  if (typeof document !== "undefined") {
    const val = getComputedStyle(document.documentElement).getPropertyValue(`--chart-${(i % 5) + 1}`)
    if (val.trim()) return `hsl(${val.trim()})`
  }
  return FALLBACK_COLORS[i % FALLBACK_COLORS.length]
}

function isNumeric(val: unknown): boolean {
  if (typeof val === "number") return !isNaN(val)
  if (typeof val === "string") {
    const cleaned = val.replace(/[$€£,%\s]/g, "")
    const n = Number(cleaned)
    return !isNaN(n) && cleaned.trim() !== ""
  }
  return false
}

function parseNumeric(val: unknown): number {
  if (typeof val === "number") return isNaN(val) ? 0 : val
  if (typeof val === "string") {
    const cleaned = val.replace(/[$€£,%\s]/g, "")
    const n = Number(cleaned)
    return isNaN(n) ? 0 : n
  }
  return 0
}

function formatNumber(val: unknown): string {
  if (typeof val === "number") {
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  if (typeof val === "string" && isNumeric(val)) {
    return parseNumeric(val).toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  return String(val ?? "")
}

function pickNumericCol(results: QueryResult): string | null {
  for (const col of results.columns) {
    const colIdx = results.columns.indexOf(col)
    const nonNullValues = results.rows
      .map((r) => r[colIdx])
      .filter((v) => v !== null && v !== undefined && v !== "")
    if (nonNullValues.length > 0 && nonNullValues.every((v) => isNumeric(v))) {
      return col
    }
  }
  return null
}

function pickStringCol(results: QueryResult, exclude?: string): string | null {
  for (const col of results.columns) {
    if (col === exclude) continue
    const colIdx = results.columns.indexOf(col)
    const nonNullValues = results.rows
      .map((r) => r[colIdx])
      .filter((v) => v !== null && v !== undefined && v !== "")
    if (nonNullValues.length > 0 && !nonNullValues.every((v) => isNumeric(v))) {
      return col
    }
  }
  return null
}

function buildData(results: QueryResult) {
  const numericCols = new Set<string>()
  for (const col of results.columns) {
    const colIdx = results.columns.indexOf(col)
    const nonNullValues = results.rows
      .map((r) => r[colIdx])
      .filter((v) => v !== null && v !== undefined && v !== "")
    if (nonNullValues.length > 0 && nonNullValues.every((v) => isNumeric(v))) {
      numericCols.add(col)
    }
  }

  return results.rows.map((row) => {
    const item: Record<string, unknown> = {}
    results.columns.forEach((col, i) => {
      const val = row[i]
      if (numericCols.has(col)) {
        item[col] = parseNumeric(val)
      } else {
        item[col] = val !== null && val !== undefined ? String(val) : ""
      }
    })
    return item
  })
}

function fixBarConfig(results: QueryResult, config?: Record<string, unknown>) {
  const numCol = pickNumericCol(results)
  const strCol = pickStringCol(results)

  let x = (config?.x as string) || (config?.label as string) || strCol || results.columns[0]
  let y = (config?.y as string) || (config?.value as string) || numCol || results.columns[1] || results.columns[0]

  const data = buildData(results)
  if (data.length > 0 && results.columns.length > 0) {
    const xIdx = results.columns.indexOf(x)
    const yIdx = results.columns.indexOf(y)

    const isXNum = xIdx >= 0 && isNumeric(results.rows[0]?.[xIdx])
    const isYNum = yIdx >= 0 && isNumeric(results.rows[0]?.[yIdx])

    if (isXNum && !isYNum) {
      const tmp = x; x = y; y = tmp
    } else if (!isYNum && numCol) {
      y = numCol
    }

    if (x === y && strCol && strCol !== y) {
      x = strCol
    }
  }
  return { data, x, y }
}

function fixPieConfig(results: QueryResult, config?: Record<string, unknown>) {
  const numCol = pickNumericCol(results)
  const strCol = pickStringCol(results)

  let label = (config?.label as string) || (config?.x as string) || strCol || results.columns[0]
  let value = (config?.value as string) || (config?.y as string) || numCol || results.columns[1] || results.columns[0]

  const data = buildData(results)
  if (data.length > 0 && results.columns.length > 0) {
    const labelIdx = results.columns.indexOf(label)
    const valueIdx = results.columns.indexOf(value)

    const isLabelNum = labelIdx >= 0 && isNumeric(results.rows[0]?.[labelIdx])
    const isValueNum = valueIdx >= 0 && isNumeric(results.rows[0]?.[valueIdx])

    if (isLabelNum && !isValueNum) {
      const tmp = label; label = value; value = tmp
    } else if (!isValueNum && numCol) {
      value = numCol
    }

    if (label === value && strCol && strCol !== value) {
      label = strCol
    }
  }
  return { data, label, value }
}

function BarChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const { data, x, y } = fixBarConfig(results, config)
  return (
    <div className="w-full h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, bottom: 25, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
          <XAxis dataKey={x} className="text-xs" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" height={45} />
          <YAxis className="text-xs" tick={{ fontSize: 11 }} tickFormatter={(val) => formatNumber(val)} />
          <Tooltip
            formatter={(val: unknown) => [formatNumber(val), y || "Value"]}
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              borderColor: "hsl(var(--border))",
              borderRadius: "0.5rem",
              color: "hsl(var(--popover-foreground))",
              fontSize: "12px",
            }}
          />
          <Bar dataKey={y} fill={getColor(0)} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function PieChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const { data, label, value } = fixPieConfig(results, config)

  // If there are more than 8 categories, take the top 7 and group the rest into "Other"
  let pieData = data
  if (data.length > 8) {
    const sorted = [...data].sort((a, b) => Number(b[value] || 0) - Number(a[value] || 0))
    const top = sorted.slice(0, 7)
    const rest = sorted.slice(7)
    const restSum = rest.reduce((acc, curr) => acc + Number(curr[value] || 0), 0)
    if (restSum > 0) {
      top.push({
        [label]: "Other",
        [value]: restSum,
      })
    }
    pieData = top
  }

  return (
    <div className="w-full h-[340px] flex flex-col items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 15, right: 15, bottom: 15, left: 15 }}>
          <Pie
            data={pieData}
            dataKey={value}
            nameKey={label}
            cx="50%"
            cy="45%"
            outerRadius={95}
            innerRadius={35}
            paddingAngle={2}
            label={({ name, percent }: { name?: string; percent?: number }) => {
              const p = ((percent ?? 0) * 100).toFixed(1)
              return `${name ?? ""}: ${p}%`
            }}
            labelLine={true}
          >
            {pieData.map((_, i) => (
              <Cell key={i} fill={getColor(i)} stroke="hsl(var(--background))" strokeWidth={1.5} />
            ))}
          </Pie>
          <Tooltip
            formatter={(val: unknown) => [formatNumber(val), (config?.value as string) || value || "Value"]}
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              borderColor: "hsl(var(--border))",
              borderRadius: "0.5rem",
              color: "hsl(var(--popover-foreground))",
              fontSize: "12px",
            }}
          />
          <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

function LineChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const { data, x, y } = fixBarConfig(results, config)
  return (
    <div className="w-full h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 10, bottom: 25, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
          <XAxis dataKey={x} className="text-xs" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" height={45} />
          <YAxis className="text-xs" tick={{ fontSize: 11 }} tickFormatter={(val) => formatNumber(val)} />
          <Tooltip
            formatter={(val: unknown) => [formatNumber(val), y || "Value"]}
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              borderColor: "hsl(var(--border))",
              borderRadius: "0.5rem",
              color: "hsl(var(--popover-foreground))",
              fontSize: "12px",
            }}
          />
          <Line type="monotone" dataKey={y} stroke={getColor(0)} strokeWidth={2} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function AreaChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const { data, x, y } = fixBarConfig(results, config)
  return (
    <div className="w-full h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, bottom: 25, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
          <XAxis dataKey={x} className="text-xs" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" height={45} />
          <YAxis className="text-xs" tick={{ fontSize: 11 }} tickFormatter={(val) => formatNumber(val)} />
          <Tooltip
            formatter={(val: unknown) => [formatNumber(val), y || "Value"]}
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              borderColor: "hsl(var(--border))",
              borderRadius: "0.5rem",
              color: "hsl(var(--popover-foreground))",
              fontSize: "12px",
            }}
          />
          <Area type="monotone" dataKey={y} stroke={getColor(0)} fill={getColor(0)} fillOpacity={0.2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function KpiView({ results }: { results: QueryResult }) {
  if (results.rows.length === 0) return null
  const firstRow = results.rows[0]
  const firstCol = results.columns[0]
  const numCol = pickNumericCol(results)
  const val = numCol ? firstRow[results.columns.indexOf(numCol)] : firstRow[0]
  return (
    <div className="flex flex-col items-center justify-center py-6">
      <p className="text-sm text-muted-foreground">{numCol || firstCol}</p>
      <p className="text-4xl font-bold tracking-tight">{formatNumber(val)}</p>
    </div>
  )
}

function TableView({ results }: { results: QueryResult }) {
  if (!results.columns || results.columns.length === 0) return null
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            {results.columns.map((col, i) => (
              <th key={i} className="px-4 py-2 text-left font-medium text-muted-foreground">{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.rows.slice(0, 50).map((row, i) => (
            <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2">{String(cell ?? "—")}</td>
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

export function VisualizationRenderer({
  results,
  suggestions,
}: {
  results: QueryResult
  suggestions?: VisualizationSuggestion[]
}) {
  if (!suggestions || suggestions.length === 0) {
    return <TableView results={results} />
  }

  return (
    <div className="space-y-4">
      {suggestions.map((v, i) => {
        const config = v.config || {}
        switch (v.type) {
          case "bar_chart":
            return (
              <div key={i}>
                <p className="mb-2 text-sm font-medium">{v.title || "Bar Chart"}</p>
                <BarChartView results={results} config={config} />
              </div>
            )
          case "pie_chart":
            return (
              <div key={i}>
                <p className="mb-2 text-sm font-medium">{v.title || "Pie Chart"}</p>
                <PieChartView results={results} config={config} />
              </div>
            )
          case "line_chart":
            return (
              <div key={i}>
                <p className="mb-2 text-sm font-medium">{v.title || "Line Chart"}</p>
                <LineChartView results={results} config={config} />
              </div>
            )
          case "area_chart":
            return (
              <div key={i}>
                <p className="mb-2 text-sm font-medium">{v.title || "Area Chart"}</p>
                <AreaChartView results={results} config={config} />
              </div>
            )
          case "kpi":
            return (
              <div key={i}>
                <p className="mb-1 text-sm font-medium">{v.title || "KPI"}</p>
                <KpiView results={results} />
              </div>
            )
          case "table":
            return (
              <div key={i}>
                {v.title && <p className="mb-2 text-sm font-medium">{v.title}</p>}
                <TableView results={results} />
              </div>
            )
          default:
            return <TableView key={i} results={results} />
        }
      })}
    </div>
  )
}
