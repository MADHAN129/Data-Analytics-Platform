"use client"

import React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { SecurityAlert } from "@/types/api"
import { ShieldAlert, AlertTriangle, CheckCircle2, Clock, Terminal, User, Sparkles } from "lucide-react"

interface SecurityAlertModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  alert: SecurityAlert | null
}

export function SecurityAlertModal({
  open,
  onOpenChange,
  alert,
}: SecurityAlertModalProps) {
  if (!alert) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto border-destructive/30 bg-background shadow-2xl p-0">
        
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-red-600 via-rose-600 to-amber-600 p-6 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm shadow-inner">
              <ShieldAlert className="h-7 w-7 text-white animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Badge variant="destructive" className="bg-white text-red-700 font-bold uppercase tracking-wider text-[10px] px-2 py-0.5">
                  Prohibited Operation
                </Badge>
                <span className="text-xs text-white/80 font-medium">Read-Only Guardrail Active</span>
              </div>
              <DialogTitle className="text-xl font-bold tracking-tight text-white mt-1">
                Security Interception: Prohibited Query Blocked
              </DialogTitle>
            </div>
          </div>
          <DialogDescription className="text-white/90 text-xs mt-2 leading-relaxed">
            Data-Taker enforces strict read-only database isolation. Any operation attempting to modify data (DELETE, UPDATE, DROP, ALTER, TRUNCATE, INSERT) or bypass AI safety guardrails is blocked immediately.
          </DialogDescription>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-4">

          {/* Reason Card */}
          <div className="rounded-lg border border-red-200 bg-red-50/50 p-4 dark:border-red-950 dark:bg-red-950/20">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-destructive">
                    Violation Type:
                  </span>
                  <Badge variant="outline" className="border-red-300 text-destructive font-mono text-[11px]">
                    {alert.violation_type}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {alert.reason}
                </p>
              </div>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="flex items-center gap-2 rounded-md border p-2.5 bg-muted/30">
              <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="truncate">
                <span className="text-muted-foreground">Intercepted At: </span>
                <span className="font-medium">{alert.timestamp}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-md border p-2.5 bg-muted/30">
              <Terminal className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="truncate">
                <span className="text-muted-foreground">Vector: </span>
                <span className="font-medium">{alert.source || "MCP Query Guard"}</span>
              </div>
            </div>
          </div>

          {/* User NL Prompt if available */}
          {alert.natural_language && (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                <span>Original Prompt (NLP):</span>
              </div>
              <div className="rounded-md bg-muted/60 p-3 font-mono text-xs text-foreground border break-words">
                {alert.natural_language}
              </div>
            </div>
          )}

          {/* Attempted SQL Payload if available */}
          {alert.attempted_sql && (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                <Terminal className="h-3.5 w-3.5 text-destructive" />
                <span>Blocked SQL Payload:</span>
              </div>
              <pre className="rounded-md bg-zinc-950 p-3.5 text-[12px] font-mono text-zinc-100 border border-zinc-800 overflow-x-auto whitespace-pre-wrap break-all max-h-36">
                <code>{alert.attempted_sql}</code>
              </pre>
            </div>
          )}

          {/* SuperAdmin Notification Status */}
          <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-3.5 dark:border-emerald-950 dark:bg-emerald-950/20">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                  SuperAdmin Incident Notification Dispatched
                </p>
                <p className="text-[11px] text-emerald-700/80 dark:text-emerald-400/80 mt-0.5">
                  An automated high-priority alert email and audit log with your user identity, prompt, and execution timestamp have been sent to system administrators.
                </p>
              </div>
            </div>
          </div>

        </div>

        {/* Footer */}
        <DialogFooter className="p-4 bg-muted/20 border-t flex sm:justify-between items-center gap-2">
          <span className="text-[11px] text-muted-foreground">
            Zero modifications made to database.
          </span>
          <Button
            variant="default"
            className="bg-destructive hover:bg-destructive/90 text-white font-medium text-xs h-9 px-4"
            onClick={() => onOpenChange(false)}
          >
            I Acknowledge &amp; Understand
          </Button>
        </DialogFooter>

      </DialogContent>
    </Dialog>
  )
}
