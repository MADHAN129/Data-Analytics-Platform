"use client"

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
  AreaChart, Area,
} from "recharts"
import type { QueryResult, VisualizationSuggestion } from "@/types/api"

const COLORS = [
  "hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))",
  "hsl(var(--chart-4))", "hsl(var(--chart-5))",
]

function rowsToChartData(results: QueryResult, xKey?: string, yKey?: string) {
  const x = xKey || results.columns[0]
  const y = yKey || results.columns[1] || results.columns[0]
  return {
    data: results.rows.map((row) => {
      const item: Record<string, unknown> = {}
      results.columns.forEach((col, i) => { item[col] = row[i] })
      return item
    }),
    x,
    y,
  }
}

function BarChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const { data, x, y } = rowsToChartData(results, config?.x as string, config?.y as string)
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey={x} className="text-xs" tick={{ fontSize: 12 }} />
        <YAxis className="text-xs" tick={{ fontSize: 12 }} />
        <Tooltip />
        <Bar dataKey={y} fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function PieChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const labelKey = (config?.label as string) || results.columns[0]
  const valueKey = (config?.value as string) || results.columns[1] || results.columns[0]
  const data = results.rows.map((row) => {
    const item: Record<string, unknown> = {}
    results.columns.forEach((col, i) => { item[col] = row[i] })
    return item
  })
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={labelKey}
          cx="50%" cy="50%" outerRadius={100}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          label={(entry: any) => `${entry.name ?? entry[labelKey]} (${entry.value ?? entry[valueKey]})`}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

function LineChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const { data, x, y } = rowsToChartData(results, config?.x as string, config?.y as string)
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey={x} className="text-xs" tick={{ fontSize: 12 }} />
        <YAxis className="text-xs" tick={{ fontSize: 12 }} />
        <Tooltip />
        <Line type="monotone" dataKey={y} stroke="hsl(var(--chart-1))" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function AreaChartView({ results, config }: { results: QueryResult; config?: Record<string, unknown> }) {
  const { data, x, y } = rowsToChartData(results, config?.x as string, config?.y as string)
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey={x} className="text-xs" tick={{ fontSize: 12 }} />
        <YAxis className="text-xs" tick={{ fontSize: 12 }} />
        <Tooltip />
        <Area type="monotone" dataKey={y} stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1))" fillOpacity={0.2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function KpiView({ results }: { results: QueryResult }) {
  if (results.rows.length === 0) return null
  const firstRow = results.rows[0]
  const firstCol = results.columns[0]
  const val = firstRow[0]
  return (
    <div className="flex flex-col items-center justify-center py-6">
      <p className="text-sm text-muted-foreground">{firstCol}</p>
      <p className="text-4xl font-bold tracking-tight">{String(val ?? "—")}</p>
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
