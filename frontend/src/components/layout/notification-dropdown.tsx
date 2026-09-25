"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
  Bell,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Database,
  Unlink,
  ExternalLink,
} from "lucide-react"

export interface DisconnectedDatabaseNotification {
  id: number
  name: string
  connection_type?: string
  host?: string
  checked_at: string
}

export function NotificationDropdown() {
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)
  const [isChecking, setIsChecking] = useState(false)
  const [disconnectedDatabases, setDisconnectedDatabases] = useState<DisconnectedDatabaseNotification[]>([])
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const [totalDatabases, setTotalDatabases] = useState(0)
  const isMountedRef = useRef(true)

  const checkDatabaseHealth = useCallback(async (showLoading = false) => {
    if (showLoading) setIsChecking(true)
    try {
      // 1. Fetch all configured databases
      const dbListRes = await api.listDatabases({ per_page: 100 })
      const allDbs = dbListRes.connections || []
      if (!isMountedRef.current) return
      setTotalDatabases(allDbs.length)

      if (allDbs.length === 0) {
        setDisconnectedDatabases([])
        setLastChecked(new Date())
        return
      }

      // 2. Fetch batch health check status
      let batchHealth: { id: number; name: string; healthy: boolean; checked_at?: string }[] = []
      try {
        const healthRes = await api.getBatchConnectionHealth()
        batchHealth = healthRes.connections || []
      } catch {
        // Fallback to database connection object properties if batch endpoint fails
        batchHealth = allDbs.map((db) => ({
          id: db.id,
          name: db.name,
          healthy: db.health_status === true || (db.health_status !== false && db.is_active),
          checked_at: db.health_checked_at || undefined,
        }))
      }

      // 3. Match and filter disconnected databases
      const healthMap = new Map(batchHealth.map((h) => [h.id, h.healthy]))
      const disconnected: DisconnectedDatabaseNotification[] = []

      for (const db of allDbs) {
        const isHealthy = healthMap.has(db.id)
          ? healthMap.get(db.id)
          : db.health_status !== false && db.is_active

        if (!isHealthy || !db.is_active || db.health_status === false) {
          disconnected.push({
            id: db.id,
            name: db.name,
            connection_type: db.connection_type,
            host: db.host,
            checked_at: db.health_checked_at || new Date().toISOString(),
          })
        }
      }

      if (isMountedRef.current) {
        setDisconnectedDatabases(disconnected)
        setLastChecked(new Date())
      }
    } catch {
      // Silently ignore connection errors to avoid interrupting user workflow
    } finally {
      if (isMountedRef.current && showLoading) {
        setIsChecking(false)
      }
    }
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    // Initial health check
    checkDatabaseHealth(false)

    // Polling interval every 30 seconds
    const interval = setInterval(() => {
      checkDatabaseHealth(false)
    }, 30000)

    return () => {
      isMountedRef.current = false
      clearInterval(interval)
    }
  }, [checkDatabaseHealth])

  const handleDropdownOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (open) {
      // Perform health check when user opens notification menu
      checkDatabaseHealth(true)
    }
  }

  const disconnectedCount = disconnectedDatabases.length

  return (
    <DropdownMenu open={isOpen} onOpenChange={handleDropdownOpenChange}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative h-9 w-9 rounded-full transition-colors hover:bg-accent"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5 text-foreground/80" />
          {disconnectedCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground animate-pulse shadow-sm">
              {disconnectedCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-80 sm:w-96 p-0" align="end" forceMount>
        {/* HEADER */}
        <div className="flex items-center justify-between border-b px-4 py-3 bg-muted/30">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">Notifications</span>
            {disconnectedCount > 0 ? (
              <Badge variant="destructive" className="text-[10px] px-1.5 py-0.5 h-5">
                {disconnectedCount} Alert{disconnectedCount > 1 ? "s" : ""}
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0.5 h-5 bg-emerald-500/10 text-emerald-600 border-emerald-200">
                Healthy
              </Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              checkDatabaseHealth(true)
            }}
            disabled={isChecking}
            title="Recheck database connections"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isChecking ? "animate-spin" : ""}`} />
            {isChecking ? "Checking..." : "Refresh"}
          </Button>
        </div>

        {/* NOTIFICATION CONTENT LIST */}
        <ScrollArea className="max-h-80">
          <div className="p-2 space-y-2">
            {disconnectedCount > 0 ? (
              disconnectedDatabases.map((db) => (
                <div
                  key={db.id}
                  className="group relative flex flex-col gap-1.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-left transition-colors hover:bg-destructive/15"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-destructive/20 text-destructive">
                        <Unlink className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-destructive leading-tight">
                          the database is disconnected
                        </p>
                        <p className="text-xs font-medium text-foreground/90 mt-0.5">
                          Database: <span className="font-semibold">{db.name}</span>
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground pl-9">
                    <span>{db.connection_type?.toUpperCase() || "Database"} {db.host ? `(${db.host})` : ""}</span>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-6 px-2 text-[11px] border-destructive/30 text-destructive hover:bg-destructive hover:text-destructive-foreground"
                      onClick={() => {
                        setIsOpen(false)
                        router.push("/dashboard/databases")
                      }}
                    >
                      Reconnect
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-6 text-center text-muted-foreground px-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 mb-2">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <p className="text-sm font-medium text-foreground">All databases connected</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-[240px]">
                  {totalDatabases > 0
                    ? `All ${totalDatabases} configured database connections are active and healthy.`
                    : "No databases are currently configured."}
                </p>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* FOOTER */}
        <DropdownMenuSeparator className="m-0" />
        <div className="p-2 bg-muted/20 flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-xs text-primary justify-center font-medium h-7"
            onClick={() => {
              setIsOpen(false)
              router.push("/dashboard/databases")
            }}
          >
            <Database className="mr-1.5 h-3.5 w-3.5" />
            Manage Database Connections
          </Button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
