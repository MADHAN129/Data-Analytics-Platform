"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth-store"
import { Sidebar } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"
import { Loader2 } from "lucide-react"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { user, isLoading, isAuthenticated, fetchUser } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    if (isLoading) {
      const token = localStorage.getItem("access_token")
      if (token) {
        fetchUser()
      } else {
        useAuthStore.setState({ isLoading: false })
        router.push("/login")
      }
    }
  }, [isLoading, fetchUser, router])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar userRoles={user?.roles?.map((r) => r.name)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
