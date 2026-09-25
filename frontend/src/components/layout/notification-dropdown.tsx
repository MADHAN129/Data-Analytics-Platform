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
import { SecurityAlertModal } from "@/components/security/security-alert-modal"
import type { NotificationItemResponse, SecurityAlert } from "@/types/api"
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Database,
  Unlink,
  Link2,
  ShieldAlert,
  Clock,
  CheckCheck,
  Trash2,
  ChevronRight,
} from "lucide-react"
import { formatDate } from "@/lib/utils"

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
  
  // Database Notifications
  const [dbNotifications, setDbNotifications] = useState<DatabaseNotificationItem[]>([])
  
  // In-App Security and System Notifications
  const [inAppNotifications, setInAppNotifications] = useState<NotificationItemResponse[]>([])
  const [inAppUnreadCount, setInAppUnreadCount] = useState(0)

  // Filter Tabs
  const [activeTab, setActiveTab] = useState<"all" | "security" | "databases">("all")

  // Modal State for Inspecting Security Alert
  const [selectedSecurityAlert, setSelectedSecurityAlert] = useState<SecurityAlert | null>(null)
  const [showSecurityModal, setShowSecurityModal] = useState(false)

  const isMountedRef = useRef(true)

  // 1. Fetch In-App Notifications
  const fetchInAppNotifications = useCallback(async () => {
    try {
      const res = await api.listNotifications({ limit: 30 })
      if (!isMountedRef.current) return
      setInAppNotifications(res.notifications || [])
      setInAppUnreadCount(res.unread_count || 0)
    } catch {
      // Silently ignore if not logged in or during initial load
    }
  }, [])

  // 2. Fetch Database Health Notifications
  const checkDatabaseHealth = useCallback(async (showLoading = false) => {
    if (showLoading) setIsChecking(true)
    try {
      const dbListRes = await api.listDatabases({ per_page: 100 })
      const allDbs = dbListRes.connections || []
      if (!isMountedRef.current) return

      if (allDbs.length === 0) {
        setDbNotifications([])
        return
      }

      let batchHealth: { id: number; name: string; healthy: boolean; latency_ms?: number | null; checked_at?: string }[] = []
      try {
        const healthRes = await api.getBatchConnectionHealth()
        batchHealth = healthRes.connections || []
      } catch {
        batchHealth = allDbs.map((db) => ({
          id: db.id,
          name: db.name,
          healthy: db.health_status === true || (db.health_status !== false && db.is_active),
          latency_ms: db.health_latency_ms,
          checked_at: db.health_checked_at || undefined,
        }))
      }

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

      items.sort((a, b) => (a.status === "disconnected" ? -1 : 1))

      if (isMountedRef.current) {
        setDbNotifications(items)
      }
    } catch {
      // Silently ignore
    } finally {
      if (isMountedRef.current && showLoading) {
        setIsChecking(false)
      }
    }
  }, [])

  // Refresh all notifications
  const refreshAll = useCallback(async (showLoading = false) => {
    await Promise.all([
      fetchInAppNotifications(),
      checkDatabaseHealth(showLoading),
    ])
  }, [fetchInAppNotifications, checkDatabaseHealth])

  useEffect(() => {
    isMountedRef.current = true
    refreshAll(false)

    // Polling interval every 25 seconds
    const interval = setInterval(() => {
      refreshAll(false)
    }, 25000)

    return () => {
      isMountedRef.current = false
      clearInterval(interval)
    }
  }, [refreshAll])

  const handleDropdownOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (open) {
      refreshAll(true)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead()
      setInAppNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      setInAppUnreadCount(0)
    } catch {
      // Ignored
    }
  }

  const handleInspectSecurityNotif = async (notif: NotificationItemResponse) => {
    if (!notif.is_read) {
      api.markNotificationRead(notif.id).catch(() => {})
      setInAppNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      )
      setInAppUnreadCount((c) => Math.max(0, c - 1))
    }

    if (notif.data) {
      const alertPayload: SecurityAlert = {
        is_violation: true,
        violation_type: (notif.data.violation_type as string) || "SECURITY_ALERT",
        reason: (notif.data.reason as string) || notif.message,
        attempted_sql: notif.data.attempted_sql as string | undefined,
        natural_language: notif.data.natural_language as string | undefined,
        timestamp: (notif.data.timestamp as string) || notif.created_at,
        user_name: notif.data.offender_name as string | undefined,
        user_email: notif.data.offender_email as string | undefined,
        user_id: notif.data.offender_user_id as number | undefined,
        company_id: notif.company_id ?? undefined,
        source: notif.data.source as string | undefined,
        superadmin_notified: true,
      }
      setSelectedSecurityAlert(alertPayload)
      setShowSecurityModal(true)
    }
  }

  const disconnectedCount = dbNotifications.filter((n) => n.status === "disconnected").length
  const totalUnreadCount = inAppUnreadCount + disconnectedCount
  const securityNotifications = inAppNotifications.filter((n) => n.type === "security_alert" || n.type === "security_warning")

  return (
    <>
      <DropdownMenu open={isOpen} onOpenChange={handleDropdownOpenChange}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="relative h-9 w-9 rounded-full transition-colors hover:bg-accent"
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5 text-foreground/80" />
            {totalUnreadCount > 0 ? (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground animate-pulse shadow-sm">
                {totalUnreadCount}
              </span>
            ) : dbNotifications.length > 0 ? (
              <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-background" />
            ) : null}
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent className="w-84 sm:w-[440px] p-0 shadow-xl border-border" align="end" forceMount>
          
          {/* HEADER */}
          <div className="flex items-center justify-between border-b px-4 py-3 bg-muted/40">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">Notifications</span>
              {totalUnreadCount > 0 && (
                <Badge variant="destructive" className="text-[10px] px-1.5 py-0.5 h-5">
                  {totalUnreadCount} New
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-1.5">
              {inAppUnreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground"
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleMarkAllRead()
                  }}
                  title="Mark all as read"
                >
                  <CheckCheck className="h-3.5 w-3.5 mr-1 text-emerald-600" />
                  Mark read
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  refreshAll(true)
                }}
                disabled={isChecking}
                title="Refresh notifications"
              >
                <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isChecking ? "animate-spin" : ""}`} />
                {isChecking ? "..." : "Refresh"}
              </Button>
            </div>
          </div>

          {/* FILTER TABS */}
          <div className="flex border-b bg-muted/15 px-3 py-1.5 gap-1.5 text-xs">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                activeTab === "all"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              All ({inAppNotifications.length + dbNotifications.length})
            </button>
            <button
              onClick={() => setActiveTab("security")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
                activeTab === "security"
                  ? "bg-destructive text-destructive-foreground"
                  : "text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              }`}
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              Security ({securityNotifications.length})
            </button>
            <button
              onClick={() => setActiveTab("databases")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
                activeTab === "databases"
                  ? "bg-emerald-600 text-white"
                  : "text-muted-foreground hover:text-emerald-600 hover:bg-emerald-500/10"
              }`}
            >
              <Database className="h-3.5 w-3.5" />
              Databases ({dbNotifications.length})
            </button>
          </div>

          {/* NOTIFICATION CONTENT LIST */}
          <ScrollArea className="max-h-96">
            <div className="p-3 space-y-2.5">
              
              {/* SECTION: SECURITY & IN-APP NOTIFICATIONS */}
              {(activeTab === "all" || activeTab === "security") && inAppNotifications.length > 0 && (
                <div className="space-y-2">
                  {inAppNotifications.map((notif) => {
                    const isSecurity = notif.type === "security_alert" || notif.type === "security_warning"
                    const offender = notif.data?.offender_name 
                      ? String(notif.data.offender_name) 
                      : notif.data?.offender_email 
                      ? String(notif.data.offender_email) 
                      : undefined
                    return (
                      <div
                        key={`inapp-${notif.id}`}
                        onClick={() => isSecurity && handleInspectSecurityNotif(notif)}
                        className={`group relative flex flex-col gap-1.5 rounded-lg border p-3 text-left transition-all ${
                          isSecurity
                            ? notif.is_read
                              ? "border-red-200 bg-red-50/30 hover:bg-red-50/60 dark:border-red-950 dark:bg-red-950/10 cursor-pointer"
                              : "border-destructive/40 bg-destructive/10 hover:bg-destructive/20 shadow-sm cursor-pointer"
                            : notif.is_read
                            ? "border-border bg-card"
                            : "border-primary/30 bg-primary/5"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                                isSecurity
                                  ? "bg-destructive/20 text-destructive"
                                  : "bg-primary/20 text-primary"
                              }`}
                            >
                              {isSecurity ? (
                                <ShieldAlert className="h-4 w-4" />
                              ) : (
                                <Bell className="h-4 w-4" />
                              )}
                            </div>
                            <div>
                              <p className="text-xs font-bold leading-tight text-foreground flex items-center gap-1.5">
                                {notif.title}
                                {!notif.is_read && (
                                  <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                                )}
                              </p>
                              {Boolean(offender) && (
                                <p className="text-[11px] font-medium text-muted-foreground mt-0.5">
                                  User: <span className="text-foreground font-semibold">{offender}</span>
                                </p>
                              )}
                            </div>
                          </div>

                          <Badge
                            variant={isSecurity ? "destructive" : "secondary"}
                            className="text-[9px] px-1.5 py-0 uppercase shrink-0 font-mono tracking-wider"
                          >
                            {notif.severity}
                          </Badge>
                        </div>

                        <p className="text-xs text-muted-foreground leading-relaxed pl-9.5">
                          {notif.message}
                        </p>

                        <div className="flex items-center justify-between text-[10px] text-muted-foreground pl-9.5 pt-1 border-t border-border/30 mt-1">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDate(notif.created_at)}</span>
                          </div>

                          {isSecurity && (
                            <span className="text-destructive font-semibold flex items-center gap-0.5 group-hover:underline">
                              Inspect Incident <ChevronRight className="h-3 w-3" />
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* SECTION: DATABASE HEALTH NOTIFICATIONS */}
              {(activeTab === "all" || activeTab === "databases") && dbNotifications.length > 0 && (
                <div className="space-y-2">
                  {dbNotifications.map((db) => {
                    const isDisconnected = db.status === "disconnected"
                    return (
                      <div
                        key={`db-${db.id}`}
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
                                className={`text-xs font-semibold leading-tight ${
                                  isDisconnected ? "text-destructive" : "text-emerald-700 dark:text-emerald-400"
                                }`}
                              >
                                {isDisconnected
                                  ? "Database connection unreachable"
                                  : "Database connection healthy"}
                              </p>
                              <p className="text-[11px] font-medium text-foreground/90 mt-0.5">
                                Database: <span className="font-semibold">{db.name}</span>
                              </p>
                            </div>
                          </div>

                          <Badge
                            variant={isDisconnected ? "destructive" : "secondary"}
                            className={`text-[9px] px-1.5 py-0 capitalize shrink-0 ${
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
                            className={`h-5 px-2 text-[10px] font-medium ${
                              isDisconnected
                                ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                : "border-border text-foreground hover:bg-accent"
                            }`}
                            onClick={() => {
                              setIsOpen(false)
                              router.push("/dashboard/databases")
                            }}
                          >
                            {isDisconnected ? "Reconnect" : "Manage"}
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* EMPTY STATE */}
              {inAppNotifications.length === 0 && dbNotifications.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground px-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground mb-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  </div>
                  <p className="text-sm font-medium text-foreground">All Clear</p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-[240px]">
                    No security alerts or connection issues detected.
                  </p>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* FOOTER */}
          <DropdownMenuSeparator className="m-0" />
          <div className="p-2 bg-muted/20 flex items-center justify-between gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-[11px] text-primary justify-center font-medium h-7 flex-1"
              onClick={() => {
                setIsOpen(false)
                router.push("/dashboard/databases")
              }}
            >
              <Database className="mr-1.5 h-3.5 w-3.5" />
              Databases
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-[11px] text-muted-foreground hover:text-foreground justify-center font-medium h-7 flex-1"
              onClick={() => {
                setIsOpen(false)
                router.push("/dashboard/settings/audit-logs")
              }}
            >
              <ShieldAlert className="mr-1.5 h-3.5 w-3.5" />
              Audit Logs
            </Button>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Security Incident Inspection Modal from Dropdown */}
      <SecurityAlertModal
        open={showSecurityModal}
        onOpenChange={setShowSecurityModal}
        alert={selectedSecurityAlert}
      />
    </>
  )
}
