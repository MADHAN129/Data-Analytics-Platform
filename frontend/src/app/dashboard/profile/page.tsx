"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import type { UserResponse } from "@/types/api"
import { useToast } from "@/components/ui/use-toast"
import { useAuthStore } from "@/store/auth-store"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  User,
  Mail,
  Phone,
  Shield,
  KeyRound,
  Camera,
  Trash2,
  Loader2,
  CheckCircle2,
  Calendar,
  Sparkles,
  Sliders,
  ChevronRight,
} from "lucide-react"

export default function ProfilePage() {
  const router = useRouter()
  const { toast } = useToast()
  const { setUser: setAuthUser } = useAuthStore()
  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [savingProfile, setSavingProfile] = useState(false)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)
  const [removePhotoDialogOpen, setRemovePhotoDialogOpen] = useState(false)
  const [removingPhoto, setRemovingPhoto] = useState(false)

  // Profile Form States
  const [fullName, setFullName] = useState("")
  const [phone, setPhone] = useState("")
  const [bio, setBio] = useState("")
  const [avatarUrl, setAvatarUrl] = useState("")

  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadUserProfile()
  }, [])

  const loadUserProfile = async () => {
    try {
      setLoading(true)
      const userData = await api.getCurrentUser()
      setUser(userData)
      setAuthUser(userData)
      setFullName(userData.full_name || "")
      setPhone(userData.phone || "")
      setBio(userData.bio || "")
      setAvatarUrl(userData.avatar_url || "")
    } catch {
      toast({
        title: "Failed to load profile",
        description: "Could not retrieve your user information. Please try refreshing.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: "Image too large",
        description: "Please select an image smaller than 10MB.",
        variant: "destructive",
      })
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const img = new Image()
      img.onload = async () => {
        try {
          setUploadingPhoto(true)
          const canvas = document.createElement("canvas")
          const maxDim = 400
          let width = img.width
          let height = img.height

          if (width > height) {
            if (width > maxDim) {
              height = Math.round((height * maxDim) / width)
              width = maxDim
            }
          } else {
            if (height > maxDim) {
              width = Math.round((width * maxDim) / height)
              height = maxDim
            }
          }

          canvas.width = width
          canvas.height = height
          const ctx = canvas.getContext("2d")
          if (ctx) {
            ctx.drawImage(img, 0, 0, width, height)
            const optimizedDataUrl = canvas.toDataURL("image/jpeg", 0.88)
            setAvatarUrl(optimizedDataUrl)

            // Auto-persist directly to backend & sync global navbar avatar
            const updated = await api.updateProfile({ avatar_url: optimizedDataUrl })
            setUser(updated)
            setAuthUser(updated)
            toast({
              title: "Profile photo updated",
              description: "Your new avatar has been saved and updated across the dashboard.",
            })
          }
        } catch {
          toast({
            title: "Error saving photo",
            description: "Could not save profile picture. Please try again.",
            variant: "destructive",
          })
        } finally {
          setUploadingPhoto(false)
        }
      }
      img.src = reader.result as string
    }
    reader.readAsDataURL(file)
  }

  const handleConfirmRemovePhoto = async () => {
    setRemovingPhoto(true)
    try {
      setAvatarUrl("")
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
      const updated = await api.updateProfile({ avatar_url: "" })
      setUser(updated)
      setAuthUser(updated)
      setRemovePhotoDialogOpen(false)
      toast({
        title: "Profile photo removed",
        description: "Your avatar has been reset to default initials.",
      })
    } catch {
      toast({
        title: "Error removing photo",
        description: "Could not remove profile picture. Please try again.",
        variant: "destructive",
      })
    } finally {
      setRemovingPhoto(false)
    }
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!fullName.trim()) {
      toast({
        title: "Validation Error",
        description: "Full name is required.",
        variant: "destructive",
      })
      return
    }

    try {
      setSavingProfile(true)
      const updated = await api.updateProfile({
        full_name: fullName.trim(),
        phone: phone.trim() || undefined,
        bio: bio.trim() || undefined,
        avatar_url: avatarUrl || undefined,
      })
      setUser(updated)
      setAuthUser(updated)
      toast({
        title: "Profile updated",
        description: "Your profile details have been saved successfully.",
      })
    } catch {
      toast({
        title: "Error saving profile",
        description: "Something went wrong. Please try again.",
        variant: "destructive",
      })
    } finally {
      setSavingProfile(false)
    }
  }

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2)
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">
          Manage your personal details, profile picture, bio, and role permissions.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Left Column: User Summary & Profile Photo Card */}
        <div className="space-y-6 md:col-span-1">
          <Card className="overflow-hidden">
            <div className="h-24 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600" />
            <CardContent className="relative pt-0 text-center">
              {/* Profile Avatar */}
              <div className="relative -mt-12 mb-4 inline-block">
                <Avatar className="h-24 w-24 border-4 border-background shadow-md">
                  {avatarUrl ? (
                    <AvatarImage src={avatarUrl} alt={fullName} className="object-cover" />
                  ) : (
                    <AvatarFallback className="bg-primary text-xl font-bold text-primary-foreground">
                      {fullName ? getInitials(fullName) : <User className="h-10 w-10" />}
                    </AvatarFallback>
                  )}
                </Avatar>
                <label
                  htmlFor="avatar-upload"
                  className="absolute bottom-0 right-0 flex h-7 w-7 cursor-pointer items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md transition-transform hover:scale-110 disabled:pointer-events-none disabled:opacity-60"
                  title="Upload profile photo"
                >
                  {uploadingPhoto ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Camera className="h-3.5 w-3.5" />
                  )}
                  <input
                    id="avatar-upload"
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    disabled={uploadingPhoto}
                    className="hidden"
                    onChange={handleImageUpload}
                  />
                </label>
              </div>

              <h2 className="text-xl font-bold">{fullName || "User Profile"}</h2>
              <p className="text-sm text-muted-foreground">{user?.email}</p>

              {/* Roles Badge List */}
              <div className="mt-3 flex flex-wrap justify-center gap-1.5">
                {user?.roles && user.roles.length > 0 ? (
                  user.roles.map((r) => (
                    <Badge key={r.id} variant="secondary" className="px-2.5 py-0.5 text-xs font-semibold">
                      <Shield className="mr-1 h-3 w-3 text-primary" />
                      {r.name}
                    </Badge>
                  ))
                ) : (
                  <Badge variant="outline" className="text-xs">
                    Viewer
                  </Badge>
                )}
                {user?.is_active && (
                  <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Active
                  </Badge>
                )}
              </div>

              {avatarUrl && (
                <div className="mt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setRemovePhotoDialogOpen(true)}
                    className="text-xs text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Remove photo
                  </Button>
                </div>
              )}

              <Separator className="my-5" />

              {/* Account Meta */}
              <div className="space-y-2 text-left text-xs text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5" /> Member Since
                  </span>
                  <span className="font-medium text-foreground">
                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "N/A"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5" /> Auth Provider
                  </span>
                  <span className="font-medium capitalize text-foreground">
                    {user?.auth_provider || "local"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Edit Details and Security Shortcut Cards */}
        <div className="space-y-6 md:col-span-2">
          {/* Personal Information Form */}
          <Card>
            <form onSubmit={handleSaveProfile}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-primary" />
                  <CardTitle>Personal Information</CardTitle>
                </div>
                <CardDescription>
                  Update your public name, contact information, and biography.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="full-name">Full Name *</Label>
                    <Input
                      id="full-name"
                      placeholder="Your full name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <div className="relative">
                      <Input
                        id="email"
                        value={user?.email || ""}
                        disabled
                        className="bg-muted text-muted-foreground"
                      />
                      <Mail className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground opacity-60" />
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number</Label>
                  <div className="relative">
                    <Input
                      id="phone"
                      type="tel"
                      placeholder="+1 (555) 000-0000"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                    />
                    <Phone className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground opacity-60" />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bio">Biography / About You</Label>
                  <Textarea
                    id="bio"
                    placeholder="Write a brief description of your role, background, or data interests..."
                    rows={4}
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Brief summary displayed on your profile.
                  </p>
                </div>
              </CardContent>
              <CardFooter className="flex justify-end border-t bg-muted/20 px-6 py-4">
                <Button type="submit" disabled={savingProfile} className="bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-sm">
                  {savingProfile ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving changes...
                    </>
                  ) : (
                    "Save Changes"
                  )}
                </Button>
              </CardFooter>
            </form>
          </Card>

          {/* Security & Password Redirect Card */}
          <Card className="border-dashed bg-muted/20">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-5 w-5 text-primary" />
                  <CardTitle className="text-base">Password & Account Security</CardTitle>
                </div>
                <Badge variant="outline" className="text-xs">
                  Settings
                </Badge>
              </div>
              <CardDescription>
                Password changes, two-factor authentication, theme customization, and notification preferences are managed in Settings.
              </CardDescription>
            </CardHeader>
            <CardFooter className="pt-0">
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => router.push("/admin/settings")}
              >
                <Sliders className="h-4 w-4 text-primary" />
                <span>Go to Settings & Security</span>
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>

      {/* Delete/Remove Profile Photo Confirmation Dialog */}
      <Dialog open={removePhotoDialogOpen} onOpenChange={setRemovePhotoDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Profile Photo</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove your profile photo? Your avatar will be reset to default initials.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setRemovePhotoDialogOpen(false)} disabled={removingPhoto}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleConfirmRemovePhoto} disabled={removingPhoto}>
              {removingPhoto ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
              Remove Photo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
