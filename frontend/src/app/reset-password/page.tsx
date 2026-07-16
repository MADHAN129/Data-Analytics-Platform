"use client"

import { Suspense } from "react"
import { ResetPasswordForm } from "@/components/auth/reset-password-form"
import { BarChart3, Loader2 } from "lucide-react"

function ResetPasswordFallback() {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
        <BarChart3 className="h-6 w-6 text-primary-foreground" />
      </div>
      <h1 className="text-2xl font-bold">Agentic Analytics</h1>
      <div className="flex justify-center pt-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        <div className="flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <BarChart3 className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold">Agentic Analytics</h1>
        </div>
        <Suspense fallback={<ResetPasswordFallback />}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  )
}
