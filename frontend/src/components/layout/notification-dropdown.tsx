"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
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
  Link2,
  ExternalLink,
} from "lucide-react"

export interface DatabaseNotificationItem {
  id: number
  name: string
  connection_type?: string
  host?: string
  status: "connected" | "disconnected"
  latency_ms?: number | null
  checked_at: string
}

export function NotificationDropdown() {
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)
  const [isChecking, setIsChecking] = useState(false)
  const [notifications, setNotifications] = useState<DatabaseNotificationItem[]>([])
  const [activeTab, setActiveTab] = useState<"all" | "disconnected" | "connected">("all")
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const isMountedRef = useRef(true)

  const checkDatabaseHealth = useCallback(async (showLoading = false) => {
    if (showLoading) setIsChecking(true)
    try {
      // 1. Fetch all configured databases
      const dbListRes = await api.listDatabases({ per_page: 100 })
      const allDbs = dbListRes.connections || []
      if (!isMountedRef.current) return

      if (allDbs.length === 0) {
        setNotifications([])
        setLastChecked(new Date())
        return
      }

      // 2. Fetch batch health check status
      let batchHealth: { id: number; name: string; healthy: boolean; latency_ms?: number | null; checked_at?: string }[] = []
      try {
        const healthRes = await api.getBatchConnectionHealth()
        batchHealth = healthRes.connections || []
      } catch {
        // Fallback to database connection object properties if batch endpoint fails
        batchHealth = allDbs.map((db) => ({
          id: db.id,
          name: db.name,
          healthy: db.health_status === true || (db.health_status !== false && db.is_active),
          latency_ms: db.health_latency_ms,
          checked_at: db.health_checked_at || undefined,
        }))
      }

      // 3. Construct unified notification items for connected and disconnected databases
      const healthMap = new Map(batchHealth.map((h) => [h.id, h]))
      const items: DatabaseNotificationItem[] = []

      for (const db of allDbs) {
        const probe = healthMap.get(db.id)
        const isHealthy = probe ? probe.healthy : (db.health_status !== false && db.is_active)
        const latency = probe?.latency_ms ?? db.health_latency_ms

        if (isHealthy && db.is_active && db.health_status !== false) {
          items.push({
            id: db.id,
            name: db.name,
            connection_type: db.connection_type,
            host: db.host,
            status: "connected",
            latency_ms: latency,
            checked_at: probe?.checked_at || db.health_checked_at || new Date().toISOString(),
          })
        } else {
          items.push({
            id: db.id,
            name: db.name,
            connection_type: db.connection_type,
            host: db.host,
            status: "disconnected",
            latency_ms: null,
            checked_at: probe?.checked_at || db.health_checked_at || new Date().toISOString(),
          })
        }
      }

      // Sort disconnected first, then connected
      items.sort((a, b) => (a.status === "disconnected" ? -1 : 1))

      if (isMountedRef.current) {
        setNotifications(items)
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

  const disconnectedItems = notifications.filter((n) => n.status === "disconnected")
  const connectedItems = notifications.filter((n) => n.status === "connected")
  const disconnectedCount = disconnectedItems.length
  const connectedCount = connectedItems.length

  const filteredItems = notifications.filter((item) => {
    if (activeTab === "disconnected") return item.status === "disconnected"
    if (activeTab === "connected") return item.status === "connected"
    return true
  })

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
          {disconnectedCount > 0 ? (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground animate-pulse shadow-sm">
              {disconnectedCount}
            </span>
          ) : connectedCount > 0 ? (
            <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-background" />
          ) : null}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-80 sm:w-[420px] p-0 shadow-lg" align="end" forceMount>
        {/* HEADER */}
        <div className="flex items-center justify-between border-b px-4 py-3 bg-muted/30">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">Notifications</span>
            {disconnectedCount > 0 && (
              <Badge variant="destructive" className="text-[10px] px-1.5 py-0.5 h-5">
                {disconnectedCount} Disconnected
              </Badge>
            )}
            {connectedCount > 0 && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0.5 h-5 bg-emerald-500/10 text-emerald-600 border-emerald-300">
                {connectedCount} Connected
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

        {/* TABS FILTER */}
        {notifications.length > 0 && (
          <div className="flex border-b bg-muted/10 px-3 py-1.5 gap-1.5 text-xs">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                activeTab === "all"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              All ({notifications.length})
            </button>
            <button
              onClick={() => setActiveTab("disconnected")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
                activeTab === "disconnected"
                  ? "bg-destructive text-destructive-foreground"
                  : "text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              }`}
            >
              Disconnected ({disconnectedCount})
            </button>
            <button
              onClick={() => setActiveTab("connected")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
                activeTab === "connected"
                  ? "bg-emerald-600 text-white"
                  : "text-muted-foreground hover:text-emerald-600 hover:bg-emerald-500/10"
              }`}
            >
              Connected ({connectedCount})
            </button>
          </div>
        )}

        {/* NOTIFICATION CONTENT LIST */}
        <ScrollArea className="max-h-80">
          <div className="p-3 space-y-2.5">
            {filteredItems.length > 0 ? (
              filteredItems.map((db) => {
                const isDisconnected = db.status === "disconnected"
                return (
                  <div
                    key={db.id}
                    className={`group relative flex flex-col gap-1.5 rounded-lg border p-3 text-left transition-colors ${
                      isDisconnected
                        ? "border-destructive/30 bg-destructive/10 hover:bg-destructive/15"
                        : "border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                            isDisconnected
                              ? "bg-destructive/20 text-destructive"
                              : "bg-emerald-500/20 text-emerald-600"
                          }`}
                        >
                          {isDisconnected ? (
                            <Unlink className="h-4 w-4" />
                          ) : (
                            <Link2 className="h-4 w-4" />
                          )}
                        </div>
                        <div>
                          <p
                            className={`text-sm font-semibold leading-tight ${
                              isDisconnected ? "text-destructive" : "text-emerald-700 dark:text-emerald-400"
                            }`}
                          >
                            {isDisconnected
                              ? "the database is disconnected"
                              : "the database is connected"}
                          </p>
                          <p className="text-xs font-medium text-foreground/90 mt-0.5">
                            Database: <span className="font-semibold">{db.name}</span>
                          </p>
                        </div>
                      </div>

                      <Badge
                        variant={isDisconnected ? "destructive" : "secondary"}
                        className={`text-[10px] px-1.5 py-0.5 capitalize shrink-0 ${
                          !isDisconnected
                            ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-200"
                            : ""
                        }`}
                      >
                        {isDisconnected ? "Disconnected" : "Connected"}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground pl-9.5 pt-0.5">
                      <div className="flex items-center gap-2">
                        <span className="uppercase text-[10px] font-mono font-medium">
                          {db.connection_type || "DB"}
                        </span>
                        {db.host && <span>• {db.host}</span>}
                        {!isDisconnected && db.latency_ms != null && (
                          <span className="text-emerald-600 dark:text-emerald-400 font-mono">
                            • {db.latency_ms}ms
                          </span>
                        )}
                      </div>

                      <Button
                        size="sm"
                        variant={isDisconnected ? "destructive" : "outline"}
                        className={`h-6 px-2 text-[11px] font-medium ${
                          isDisconnected
                            ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            : "border-border text-foreground hover:bg-accent"
                        }`}
                        onClick={() => {
                          setIsOpen(false)
                          router.push("/dashboard/databases")
                        }}
                      >
                        {isDisconnected ? "Reconnect" : "View"}
                      </Button>
                    </div>
                  </div>
                )
              })
            ) : (
              <div className="flex flex-col items-center justify-center py-6 text-center text-muted-foreground px-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground mb-2">
                  <Database className="h-5 w-5" />
                </div>
                <p className="text-sm font-medium text-foreground">No database notifications</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-[240px]">
                  {activeTab !== "all"
                    ? `No ${activeTab} databases found.`
                    : "No database connections have been configured yet."}
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
