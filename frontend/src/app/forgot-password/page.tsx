"use client"

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form"
import { BarChart3 } from "lucide-react"

export default function ForgotPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        <div className="flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <BarChart3 className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold">Agentic Analytics</h1>
        </div>
        <ForgotPasswordForm />
      </div>
    </div>
  )
}
