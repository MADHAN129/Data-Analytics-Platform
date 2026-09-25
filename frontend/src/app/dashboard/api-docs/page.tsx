"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ExternalLink,
  Code2,
  FileCode2,
  BookOpen,
  Copy,
  Check,
  Shield,
  Database,
  Sparkles,
  Users,
  LayoutDashboard,
  Layers,
  Terminal,
} from "lucide-react"

export default function ApiDocsPage() {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState("overview")

  const backendUrl = typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8090`
    : "http://localhost:8090"

  const swaggerUrl = `${backendUrl}/docs`
  const redocUrl = `${backendUrl}/redoc`
  const openapiUrl = `${backendUrl}/openapi.json`

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const endpointCategories = [
    {
      title: "Authentication",
      icon: <Shield className="h-5 w-5 text-blue-500" />,
      description: "JWT Login, registration, token refresh, password recovery, MFA",
      endpoints: [
        { method: "POST", path: "/api/v1/auth/login", desc: "Authenticate user and get JWT access token" },
        { method: "POST", path: "/api/v1/auth/register", desc: "Create a new user account" },
        { method: "POST", path: "/api/v1/auth/refresh", desc: "Refresh expired access token" },
        { method: "GET", path: "/api/v1/users/me", desc: "Get current authenticated profile" },
      ],
    },
    {
      title: "Database Connections",
      icon: <Database className="h-5 w-5 text-emerald-500" />,
      description: "Connect to PostgreSQL, MySQL, ClickHouse, SQLite, DuckDB, Snowflake",
      endpoints: [
        { method: "GET", path: "/api/v1/connections", desc: "List all configured database connections" },
        { method: "POST", path: "/api/v1/connections", desc: "Register a new database connection" },
        { method: "POST", path: "/api/v1/connections/{id}/test", desc: "Test connection credentials" },
        { method: "GET", path: "/api/v1/connections/{id}/schema", desc: "Introspect database schema and tables" },
      ],
    },
    {
      title: "AI & Query Engine",
      icon: <Sparkles className="h-5 w-5 text-purple-500" />,
      description: "Natural language to SQL, execution engine, query history, caching",
      endpoints: [
        { method: "POST", path: "/api/v1/queries/generate", desc: "Convert text prompt to SQL query with AI" },
        { method: "POST", path: "/api/v1/queries/execute", desc: "Execute SQL and return structured data" },
        { method: "GET", path: "/api/v1/queries/history", desc: "Retrieve query execution history" },
        { method: "POST", path: "/api/v1/conversations", desc: "Multi-turn analytical chat sessions" },
      ],
    },
    {
      title: "Dashboards & Reports",
      icon: <LayoutDashboard className="h-5 w-5 text-amber-500" />,
      description: "Custom chart widgets, dashboards, scheduling, auto-export",
      endpoints: [
        { method: "GET", path: "/api/v1/dashboards", desc: "List user and team dashboards" },
        { method: "POST", path: "/api/v1/dashboards", desc: "Create a new interactive dashboard" },
        { method: "POST", path: "/api/v1/dashboards/{id}/widgets", desc: "Add a chart or KPI widget" },
        { method: "GET", path: "/api/v1/reports", desc: "Fetch analytical reports" },
      ],
    },
    {
      title: "User Management & RBAC",
      icon: <Users className="h-5 w-5 text-indigo-500" />,
      description: "Role-based access control, user provisioning, system auditing",
      endpoints: [
        { method: "GET", path: "/api/v1/users", desc: "List system users (Admin only)" },
        { method: "POST", path: "/api/v1/users", desc: "Create a new user with single role" },
        { method: "GET", path: "/api/v1/roles", desc: "List roles (SuperAdmin, Analyst, Viewer)" },
        { method: "GET", path: "/api/v1/audit", desc: "Query security and audit logs" },
      ],
    },
  ]

  const codeSamples = [
    {
      title: "cURL",
      lang: "bash",
      code: `curl -X POST "${backendUrl}/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"email": "admin@agentic.ai", "password": "your_password"}'`,
    },
    {
      title: "Python (requests)",
      lang: "python",
      code: `import requests

BASE_URL = "${backendUrl}"

# 1. Login to retrieve access token
auth_resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
    "email": "admin@agentic.ai",
    "password": "your_password"
})
token = auth_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Ask AI to generate and run SQL
query_resp = requests.post(
    f"{BASE_URL}/api/v1/queries/generate",
    headers=headers,
    json={
        "connection_id": 1,
        "prompt": "Show top 10 customers by total revenue this month"
    }
)
print(query_resp.json())`,
    },
    {
      title: "JavaScript / TypeScript (Fetch)",
      lang: "javascript",
      code: `const BASE_URL = "${backendUrl}";

async function executeQuery(token, connectionId, prompt) {
  const response = await fetch(\`\${BASE_URL}/api/v1/queries/generate\`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": \`Bearer \${token}\`
    },
    body: JSON.stringify({
      connection_id: connectionId,
      prompt: prompt
    })
  });
  return await response.json();
}`,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API Documentation</h1>
          <p className="text-muted-foreground">
            Explore and integrate with the Agentic Analytics REST API & AI Engine
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <a href={openapiUrl} target="_blank" rel="noopener noreferrer">
              <FileCode2 className="mr-2 h-4 w-4" />
              OpenAPI JSON
            </a>
          </Button>
          <Button asChild>
            <a href={swaggerUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="mr-2 h-4 w-4" />
              Open Swagger UI
            </a>
          </Button>
        </div>
      </div>

      {/* Quick Launch Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="hover:border-primary/50 transition-colors">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Code2 className="h-6 w-6 text-primary" />
              <Badge variant="secondary">Interactive</Badge>
            </div>
            <CardTitle className="text-lg mt-2">Swagger UI</CardTitle>
            <CardDescription>
              Interactive playground to test endpoints, authenticate with JWT tokens, and inspect live responses.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" asChild>
              <a href={swaggerUrl} target="_blank" rel="noopener noreferrer">
                Launch Swagger UI
                <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 transition-colors">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <BookOpen className="h-6 w-6 text-blue-500" />
              <Badge variant="secondary">Documentation</Badge>
            </div>
            <CardTitle className="text-lg mt-2">ReDoc Reference</CardTitle>
            <CardDescription>
              Structured, human-readable API documentation with nested schema viewer, search, and parameter tables.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" asChild>
              <a href={redocUrl} target="_blank" rel="noopener noreferrer">
                Launch ReDoc
                <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 transition-colors">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Layers className="h-6 w-6 text-emerald-500" />
              <Badge variant="secondary">OpenAPI 3.1</Badge>
            </div>
            <CardTitle className="text-lg mt-2">OpenAPI Spec</CardTitle>
            <CardDescription>
              Raw machine-readable OpenAPI schema for generating SDK clients, Postman collections, and CLI tools.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" asChild>
              <a href={openapiUrl} target="_blank" rel="noopener noreferrer">
                View OpenAPI Schema
                <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid grid-cols-3 w-full max-w-md">
          <TabsTrigger value="overview">API Overview</TabsTrigger>
          <TabsTrigger value="quickstart">Code Examples</TabsTrigger>
          <TabsTrigger value="embedded">Interactive Embed</TabsTrigger>
        </TabsList>

        {/* Tab 1: Overview */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                Authentication & Authorization
              </CardTitle>
              <CardDescription>
                All secured endpoints require an Authorization header formatted with a valid Bearer token.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg bg-muted p-4 font-mono text-sm">
                <code>Authorization: Bearer &lt;your_jwt_access_token&gt;</code>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {endpointCategories.map((category) => (
              <Card key={category.title}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    {category.icon}
                    <CardTitle className="text-base">{category.title}</CardTitle>
                  </div>
                  <CardDescription className="text-xs">{category.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {category.endpoints.map((ep) => (
                    <div
                      key={ep.path}
                      className="flex items-start justify-between gap-2 p-2 rounded-md bg-muted/40 text-xs border"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={`font-bold px-1.5 py-0.5 rounded text-[10px] ${
                              ep.method === "GET"
                                ? "bg-blue-500/10 text-blue-600 border border-blue-200"
                                : ep.method === "POST"
                                ? "bg-emerald-500/10 text-emerald-600 border border-emerald-200"
                                : ep.method === "PUT"
                                ? "bg-amber-500/10 text-amber-600 border border-amber-200"
                                : "bg-red-500/10 text-red-600 border border-red-200"
                            }`}
                          >
                            {ep.method}
                          </span>
                          <span className="font-mono font-medium">{ep.path}</span>
                        </div>
                        <p className="text-muted-foreground">{ep.desc}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Tab 2: Code Examples */}
        <TabsContent value="quickstart" className="space-y-4">
          {codeSamples.map((sample, idx) => (
            <Card key={sample.title}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-muted-foreground" />
                    <CardTitle className="text-base">{sample.title}</CardTitle>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCopy(sample.code, idx)}
                    className="h-8 px-2"
                  >
                    {copiedIndex === idx ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-500 mr-1" />
                        <span className="text-xs text-emerald-500">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5 mr-1" />
                        <span className="text-xs">Copy</span>
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="rounded-lg bg-zinc-950 p-4 font-mono text-xs text-zinc-100 overflow-x-auto">
                  <code>{sample.code}</code>
                </pre>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Tab 3: Embedded Swagger Viewer */}
        <TabsContent value="embedded">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Embedded Swagger UI</CardTitle>
                  <CardDescription>Live interactive REST API documentation viewer</CardDescription>
                </div>
                <Button size="sm" variant="outline" asChild>
                  <a href={swaggerUrl} target="_blank" rel="noopener noreferrer">
                    Open in Full Window
                    <ExternalLink className="ml-2 h-3.5 w-3.5" />
                  </a>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-2">
              <div className="rounded-lg border overflow-hidden bg-background h-[700px]">
                <iframe
                  src={swaggerUrl}
                  title="Swagger UI Documentation"
                  className="w-full h-full border-0"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
