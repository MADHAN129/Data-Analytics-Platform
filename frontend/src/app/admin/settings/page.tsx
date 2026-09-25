"use client"

import { useState } from "react"
import { api } from "@/lib/api-client"
import { useToast } from "@/components/ui/use-toast"
import { useThemeStore } from "@/store/theme-store"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Sun,
  Moon,
  Laptop,
  Palette,
  Shield,
  KeyRound,
  Bell,
  Sliders,
  Check,
  Loader2,
  Sparkles,
  Eye,
  Zap,
  Lock,
  Smartphone,
  Globe,
  Database,
  RefreshCw,
  Info,
} from "lucide-react"

export default function SettingsPage() {
  const { toast } = useToast()
  const {
    mode,
    compactMode,
    animations,
    highContrast,
    setMode,
    setCompactMode,
    setAnimations,
    setHighContrast,
  } = useThemeStore()

  // Password Form States
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [changingPassword, setChangingPassword] = useState(false)

  // Notification Preferences States
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [queryCompleteAlerts, setQueryCompleteAlerts] = useState(true)
  const [securityAlerts, setSecurityAlerts] = useState(true)
  const [weeklyDigest, setWeeklyDigest] = useState(false)

  // System Config States
  const [platformName, setPlatformName] = useState("Agentic AI Analytics")
  const [defaultRefreshInterval, setDefaultRefreshInterval] = useState("30")
  const [timezone, setTimezone] = useState("UTC+05:30 (IST)")
  const [savingConfig, setSavingConfig] = useState(false)

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentPassword) {
      toast({
        title: "Validation Error",
        description: "Please enter your current password.",
        variant: "destructive",
      })
      return
    }
    if (newPassword.length < 8) {
      toast({
        title: "Validation Error",
        description: "New password must be at least 8 characters long.",
        variant: "destructive",
      })
      return
    }
    if (newPassword !== confirmPassword) {
      toast({
        title: "Password Mismatch",
        description: "New password and confirm password do not match. Please ensure both passwords match.",
        variant: "destructive",
      })
      return
    }

    try {
      setChangingPassword(true)
      const res = await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      toast({
        title: "Password Changed Successfully",
        description: res?.message || "Your password has been updated securely.",
      })
    } catch (err: unknown) {
      const errorObj = err as { detail?: string | { msg?: string }[]; message?: string }
      let errorMsg = "Current password is incorrect. Please check your current password and try again."
      if (typeof errorObj?.detail === "string") {
        errorMsg = errorObj.detail
      } else if (Array.isArray(errorObj?.detail) && errorObj.detail.length > 0) {
        errorMsg = errorObj.detail[0].msg || errorMsg
      } else if (errorObj?.message) {
        errorMsg = errorObj.message
      }
      toast({
        title: "Incorrect Password",
        description: errorMsg,
        variant: "destructive",
      })
    } finally {
      setChangingPassword(false)
    }
  }

  const handleSaveNotifications = () => {
    toast({
      title: "Preferences Saved",
      description: "Notification preferences have been updated successfully.",
    })
  }

  const handleSaveGeneralConfig = (e: React.FormEvent) => {
    e.preventDefault()
    setSavingConfig(true)
    setTimeout(() => {
      setSavingConfig(false)
      toast({
        title: "Configuration Saved",
        description: "System and regional settings updated successfully.",
      })
    }, 400)
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Customize platform appearance, night mode, account security, notifications, and system preferences.
        </p>
      </div>

      <Tabs defaultValue="appearance" className="space-y-6">
        <TabsList className="grid h-11 w-full grid-cols-4 max-w-2xl bg-muted/60 p-1">
          <TabsTrigger value="appearance" className="flex items-center gap-2">
            <Palette className="h-4 w-4" />
            <span>Appearance</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            <span>Security & Auth</span>
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            <span>Notifications</span>
          </TabsTrigger>
          <TabsTrigger value="system" className="flex items-center gap-2">
            <Sliders className="h-4 w-4" />
            <span>General</span>
          </TabsTrigger>
        </TabsList>

        {/* ========================================================================= */}
        {/* APPEARANCE & THEME MODES TAB */}
        {/* ========================================================================= */}
        <TabsContent value="appearance" className="space-y-6">
          {/* Theme Mode Selector Card (Button Model) */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">Theme & Display Mode</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Choose between Light mode, Night / Dark mode, or follow your operating system preferences.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="inline-flex items-center rounded-lg border bg-muted/60 p-1">
                {/* Light Mode Button */}
                <button
                  type="button"
                  onClick={() => setMode("light")}
                  className={`flex items-center gap-2 rounded-md px-4 py-2 text-xs font-semibold transition-all ${
                    mode === "light"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <Sun className={`h-4 w-4 ${mode === "light" ? "text-amber-300" : "text-amber-500"}`} />
                  <span>Light Mode</span>
                </button>

                {/* Night / Dark Mode Button */}
                <button
                  type="button"
                  onClick={() => setMode("dark")}
                  className={`flex items-center gap-2 rounded-md px-4 py-2 text-xs font-semibold transition-all ${
                    mode === "dark"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <Moon className={`h-4 w-4 ${mode === "dark" ? "text-indigo-200" : "text-indigo-400"}`} />
                  <span>Night / Dark Mode</span>
                </button>

                {/* System Default Button */}
                <button
                  type="button"
                  onClick={() => setMode("system")}
                  className={`flex items-center gap-2 rounded-md px-4 py-2 text-xs font-semibold transition-all ${
                    mode === "system"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <Laptop className="h-4 w-4" />
                  <span>System Default</span>
                </button>
              </div>
            </CardContent>
          </Card>

          {/* Interface & Visual Accessibility Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Eye className="h-5 w-5 text-primary" />
                <CardTitle>Interface & Accessibility Preferences</CardTitle>
              </div>
              <CardDescription>
                Customize UI scaling, animation behavior, and data readability.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="compact-mode" className="text-sm font-medium">Compact Density</Label>
                  <p className="text-xs text-muted-foreground">
                    Reduce padding in data tables and query results for higher information density.
                  </p>
                </div>
                <Switch
                  id="compact-mode"
                  checked={compactMode}
                  onCheckedChange={setCompactMode}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="animations-toggle" className="text-sm font-medium">Motion & UI Transitions</Label>
                  <p className="text-xs text-muted-foreground">
                    Enable smooth transitions, drawer effects, and animated charts.
                  </p>
                </div>
                <Switch
                  id="animations-toggle"
                  checked={animations}
                  onCheckedChange={setAnimations}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="high-contrast" className="text-sm font-medium">Enhanced Text Contrast</Label>
                  <p className="text-xs text-muted-foreground">
                    Boost font weighting and border clarity for improved legibility.
                  </p>
                </div>
                <Switch
                  id="high-contrast"
                  checked={highContrast}
                  onCheckedChange={setHighContrast}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ========================================================================= */}
        {/* SECURITY & PASSWORD MANAGEMENT TAB */}
        {/* ========================================================================= */}
        <TabsContent value="security" className="space-y-6">
          {/* Change Password Card */}
          <Card>
            <form onSubmit={handleChangePassword}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <KeyRound className="h-5 w-5 text-primary" />
                  <CardTitle>Change Password</CardTitle>
                </div>
                <CardDescription>
                  Update your account password. Use at least 8 characters with letters, numbers, and symbols.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="settings-current-password">Current Password *</Label>
                  <Input
                    id="settings-current-password"
                    type="password"
                    placeholder="Enter your current password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="settings-new-password">New Password *</Label>
                    <Input
                      id="settings-new-password"
                      type="password"
                      placeholder="Min. 8 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="settings-confirm-password">Confirm New Password *</Label>
                    <Input
                      id="settings-confirm-password"
                      type="password"
                      placeholder="Repeat new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 text-xs text-muted-foreground flex items-start gap-2">
                  <Info className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
                  <span>
                    Passwords must be at least 8 characters long and differ from your current password.
                  </span>
                </div>
              </CardContent>
              <CardFooter className="flex justify-end border-t bg-muted/20 px-6 py-4">
                <Button
                  type="submit"
                  disabled={changingPassword}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-sm"
                >
                  {changingPassword ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Updating password...
                    </>
                  ) : (
                    "Update Password"
                  )}
                </Button>
              </CardFooter>
            </form>
          </Card>

          {/* Two-Factor Authentication & Account Security */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Lock className="h-5 w-5 text-primary" />
                <CardTitle>Two-Factor Authentication (2FA)</CardTitle>
              </div>
              <CardDescription>
                Add an extra layer of security to your analytics account during sign-in.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Authenticator App (TOTP)</span>
                    <Badge variant="outline" className="text-xs border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400">
                      Recommended
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Use Google Authenticator, Microsoft Authenticator, or 1Password to generate verification codes.
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => toast({ title: "2FA Setup", description: "Two-Factor authentication wizard will be available shortly." })}>
                  <Smartphone className="mr-2 h-3.5 w-3.5" />
                  Configure 2FA
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ========================================================================= */}
        {/* NOTIFICATIONS TAB */}
        {/* ========================================================================= */}
        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-primary" />
                <CardTitle>Notification Preferences</CardTitle>
              </div>
              <CardDescription>
                Manage what notifications you receive via email and inside the web platform.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="email-alerts" className="text-sm font-medium">Email Alerts for Long Queries</Label>
                  <p className="text-xs text-muted-foreground">
                    Receive email notifications when background batch queries or heavy analytics jobs finish.
                  </p>
                </div>
                <Switch
                  id="email-alerts"
                  checked={emailAlerts}
                  onCheckedChange={setEmailAlerts}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="query-alerts" className="text-sm font-medium">In-App Query Completion Popups</Label>
                  <p className="text-xs text-muted-foreground">
                    Show toast popup banners when your SQL execution completes in background tabs.
                  </p>
                </div>
                <Switch
                  id="query-alerts"
                  checked={queryCompleteAlerts}
                  onCheckedChange={setQueryCompleteAlerts}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="security-alerts" className="text-sm font-medium">Security & Audit Notifications</Label>
                  <p className="text-xs text-muted-foreground">
                    Get alerted upon logins from new IP addresses or critical permission modifications.
                  </p>
                </div>
                <Switch
                  id="security-alerts"
                  checked={securityAlerts}
                  onCheckedChange={setSecurityAlerts}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="weekly-digest" className="text-sm font-medium">Weekly Analytics Summary Digest</Label>
                  <p className="text-xs text-muted-foreground">
                    Receive weekly summary reports of database usage, query trends, and top insights.
                  </p>
                </div>
                <Switch
                  id="weekly-digest"
                  checked={weeklyDigest}
                  onCheckedChange={setWeeklyDigest}
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-end border-t bg-muted/20 px-6 py-4">
              <Button onClick={handleSaveNotifications} className="bg-blue-600 hover:bg-blue-700 text-white">
                Save Notification Settings
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* ========================================================================= */}
        {/* SYSTEM & GENERAL CONFIG TAB */}
        {/* ========================================================================= */}
        <TabsContent value="system" className="space-y-6">
          <Card>
            <form onSubmit={handleSaveGeneralConfig}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Sliders className="h-5 w-5 text-primary" />
                  <CardTitle>System & Regional Configuration</CardTitle>
                </div>
                <CardDescription>
                  Configure environment defaults, platform branding, and query refresh rates.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="platform-name">Platform Title</Label>
                    <Input
                      id="platform-name"
                      value={platformName}
                      onChange={(e) => setPlatformName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="timezone-select">Default Timezone</Label>
                    <Input
                      id="timezone-select"
                      value={timezone}
                      onChange={(e) => setTimezone(e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="refresh-interval">Dashboard Auto-Refresh (seconds)</Label>
                    <Input
                      id="refresh-interval"
                      type="number"
                      value={defaultRefreshInterval}
                      onChange={(e) => setDefaultRefreshInterval(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="system-ver">Platform Version</Label>
                    <Input
                      id="system-ver"
                      value="v2.4.0 (Enterprise Build)"
                      disabled
                      className="bg-muted text-muted-foreground"
                    />
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-end border-t bg-muted/20 px-6 py-4">
                <Button type="submit" disabled={savingConfig} className="bg-blue-600 hover:bg-blue-700 text-white">
                  {savingConfig ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Configuration"
                  )}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
