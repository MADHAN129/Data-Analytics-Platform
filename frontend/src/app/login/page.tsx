"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { LoginForm } from "@/components/auth/login-form"
import { useAuthStore } from "@/store/auth-store"
import { BarChart3 } from "lucide-react"

export default function LoginPage() {
  const { isAuthenticated, isLoading } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.push("/dashboard")
    }
  }, [isAuthenticated, isLoading, router])

  return (
    <div className="flex min-h-screen">
      <div className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-8">
          <div className="flex flex-col items-center gap-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
              <BarChart3 className="h-6 w-6 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-bold">Agentic Analytics</h1>
            <p className="text-sm text-muted-foreground">
              AI-powered enterprise analytics platform
            </p>
          </div>
          <LoginForm />
        </div>
      </div>
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary/10 to-primary/5 items-center justify-center p-12">
        <div className="max-w-md space-y-6">
          <h2 className="text-3xl font-bold tracking-tight">
            Transform your data into actionable insights
          </h2>
          <ul className="space-y-3">
            {[
              "Natural language querying powered by AI",
              "Voice-enabled data exploration",
              "Auto-generated dashboards and visualizations",
              "Multi-database support via MCP protocol",
            ].map((item) => (
              <li key={item} className="flex items-center gap-3 text-muted-foreground">
                <div className="h-2 w-2 rounded-full bg-primary" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
