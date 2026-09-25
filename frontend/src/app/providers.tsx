"use client"

import { useEffect } from "react"
import { Toaster } from "@/components/ui/toaster"
import { useThemeStore } from "@/store/theme-store"

export function Providers({ children }: { children: React.ReactNode }) {
  const { initTheme } = useThemeStore()

  useEffect(() => {
    initTheme()
  }, [initTheme])

  return (
    <>
      {children}
      <Toaster />
    </>
  )
}
