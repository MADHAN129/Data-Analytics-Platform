"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { apiCache } from "@/lib/api-cache"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { DataTable, type Column } from "@/components/ui/data-table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { UserResponse, RoleResponse, CreateUserRequest } from "@/types/api"
import { useAuthStore } from "@/store/auth-store"
import { getInitials, formatDate } from "@/lib/utils"
import {
  Loader2,
  MoreVertical,
  Search,
  Shield,
  UserPlus,
  Check,
  CheckCircle2,
  UserCheck,
  UserX,
  Trash2,
} from "lucide-react"

interface NewUserFormData {
  full_name: string
  email: string
  password: string
  phone: string
  role: string
}

const defaultNewUserForm: NewUserFormData = {
  full_name: "",
  email: "",
  password: "",
  phone: "",
  role: "Analyst",
}

export default function AdminUsersPage() {
  const { user: currentUser, setUser } = useAuthStore()
  const [me, setMe] = useState<UserResponse | null>(currentUser)
  const [users, setUsers] = useState<UserResponse[]>([])
  const [availableRoles, setAvailableRoles] = useState<RoleResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null)

  useEffect(() => {
    if (currentUser) {
      setMe(currentUser)
    } else {
      api.getCurrentUser()
        .then((u) => {
          setMe(u)
          setUser(u)
        })
        .catch(() => {})
    }
  }, [currentUser, setUser])

  const isUserSelf = useCallback((targetUser: UserResponse) => {
    const effectiveMe = me || currentUser
    if (!effectiveMe) return false
    const matchId = Boolean(
      effectiveMe.id !== undefined &&
      targetUser.id !== undefined &&
      String(effectiveMe.id) === String(targetUser.id)
    )
    const matchEmail = Boolean(
      effectiveMe.email &&
      targetUser.email &&
      effectiveMe.email.trim().toLowerCase() === targetUser.email.trim().toLowerCase()
    )
    return matchId || matchEmail
  }, [me, currentUser])
  
  const isSuperAdminUser = useCallback((targetUser: UserResponse | null) => {
    if (!targetUser) return false
    return targetUser.roles.some((r) => r.name === "SuperAdmin")
  }, [])

  // Dialogs
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [roleDialogOpen, setRoleDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  
  // Form states
  const [newUserForm, setNewUserForm] = useState<NewUserFormData>({ ...defaultNewUserForm })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [isUpdatingRole, setIsUpdatingRole] = useState<number | null>(null)
  
  const { toast } = useToast()
  const perPage = 20

  const fetchRoles = useCallback(async () => {
    try {
      const { data } = await apiCache.swr("roles:all", () => api.listRoles(), {
        ttlMs: 60000,
        onRevalidate: (fresh) => setAvailableRoles(fresh.roles || []),
      })
      setAvailableRoles(data.roles || [])
    } catch {
      // Fallback roles if list fails
      setAvailableRoles([
        { id: 1, name: "SuperAdmin", description: "Company owner with full unrestricted system access", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
        { id: 2, name: "Admin", description: "Company administrator with user, database, and audit management", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
        { id: 3, name: "Analyst", description: "Can create connections, query data and build dashboards", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
        { id: 4, name: "Viewer", description: "Can view shared dashboards and reports", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
      ])
    }
  }, [])

  const fetchUsers = useCallback(async (forceFresh = false) => {
    const cacheKey = `users:page=${page}:search=${search}`
    try {
      const { data } = await apiCache.swr(
        cacheKey,
        () => api.listUsers({ page, per_page: perPage, search: search || undefined }),
        {
          ttlMs: 45000,
          forceFresh,
          onRevalidate: (fresh) => {
            setUsers(fresh.users)
            setTotal(fresh.total)
          },
        }
      )
      setUsers(data.users)
      setTotal(data.total)
      setIsLoading(false)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to load users", variant: "destructive" })
      setIsLoading(false)
    }
  }, [page, perPage, search, toast])

  useEffect(() => {
    fetchUsers()
    fetchRoles()
  }, [fetchUsers, fetchRoles])

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newUserForm.email || !newUserForm.password || !newUserForm.full_name) {
      toast({ title: "Error", description: "Please fill in all required fields", variant: "destructive" })
      return
    }

    setIsSubmitting(true)
    try {
      const selectedRole = newUserForm.role || "Analyst"
      await api.createUser({
        full_name: newUserForm.full_name.trim(),
        email: newUserForm.email.trim(),
        password: newUserForm.password,
        phone: newUserForm.phone?.trim() || undefined,
        role: selectedRole,
        roles: [selectedRole],
      })
      apiCache.invalidate("users")
      toast({ title: "User created successfully", variant: "success" })
      setAddDialogOpen(false)
      setNewUserForm({ ...defaultNewUserForm })
      fetchUsers(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({
        title: "Error creating user",
        description: error.detail || "Failed to create user",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleToggleStatus = async (user: UserResponse) => {
    if (isUserSelf(user)) {
      toast({
        title: "Action Not Allowed",
        description: "You cannot deactivate or modify the status of your own account.",
        variant: "destructive",
      })
      return
    }

    setIsToggling(true)
    try {
      if (user.is_active) {
        await api.deactivateUser(user.id)
        toast({ title: "User deactivated", variant: "success" })
      } else {
        await api.activateUser(user.id)
        toast({ title: "User activated", variant: "success" })
      }
      apiCache.invalidate("users")
      fetchUsers(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Operation failed", variant: "destructive" })
    } finally {
      setIsToggling(false)
    }
  }

  const handleDeleteUser = async () => {
    if (!selectedUser) return
    if (isUserSelf(selectedUser)) {
      toast({
        title: "Action Not Allowed",
        description: "You cannot delete your own account.",
        variant: "destructive",
      })
      setDeleteDialogOpen(false)
      setSelectedUser(null)
      return
    }

    try {
      await api.deleteUser(selectedUser.id)
      apiCache.invalidate("users")
      toast({ title: "User deleted", variant: "success" })
      setDeleteDialogOpen(false)
      setSelectedUser(null)
      fetchUsers(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to delete user", variant: "destructive" })
    }
  }

  const handleSetRoleForSelectedUser = async (targetRole: RoleResponse) => {
    if (!selectedUser) return
    if (isUserSelf(selectedUser)) {
      toast({
        title: "Action Not Allowed",
        description: "You cannot modify roles of your own account.",
        variant: "destructive",
      })
      return
    }
    const currentRoleIds = selectedUser.roles.map((r) => r.id)
    if (currentRoleIds.includes(targetRole.id) && currentRoleIds.length === 1) {
      return // Already has only this role
    }

    setIsUpdatingRole(targetRole.id)
    try {
      await api.setUserRole(selectedUser.id, targetRole.id)
      apiCache.invalidate("users")
      toast({ title: `Role updated to ${targetRole.name}`, variant: "success" })
      setSelectedUser({ ...selectedUser, roles: [targetRole] })
      fetchUsers(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error updating role", description: error.detail || "Operation failed", variant: "destructive" })
    } finally {
      setIsUpdatingRole(null)
    }
  }

  const columns: Column<UserResponse>[] = [
    {
      key: "user",
      header: "User",
      cell: (user) => {
        const isSelf = isUserSelf(user)
        return (
          <div className="flex items-center gap-3">
            <Avatar className="h-9 w-9">
              <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                {getInitials(user.full_name)}
              </AvatarFallback>
            </Avatar>
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium">{user.full_name}</p>
                {isSelf && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 border-primary/40 text-primary bg-primary/5 font-semibold">
                    You
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{user.email}</p>
            </div>
          </div>
        )
      },
    },
    {
      key: "roles",
      header: "Roles",
      cell: (user) => (
        <div className="flex flex-wrap gap-1.5">
          {user.roles.length > 0 ? (
            user.roles.map((role) => (
              <Badge
                key={role.id}
                variant="secondary"
                className={`text-xs ${
                  role.name === "SuperAdmin"
                    ? "bg-purple-500/10 text-purple-700 border-purple-200 font-semibold"
                    : role.name === "Admin"
                    ? "bg-emerald-500/10 text-emerald-700 border-emerald-200 font-medium"
                    : role.name === "Analyst"
                    ? "bg-blue-500/10 text-blue-700 border-blue-200"
                    : "bg-slate-500/10 text-slate-700 border-slate-200"
                }`}
              >
                {role.name === "SuperAdmin" ? "★ SuperAdmin" : role.name}
              </Badge>
            ))
          ) : (
            <span className="text-xs text-muted-foreground">No roles</span>
          )}
        </div>
      ),
    },
    {
      key: "provider",
      header: "Auth",
      cell: (user) => (
        <Badge variant="outline" className="text-xs capitalize">
          {user.auth_provider}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (user) => (
        <Badge variant={user.is_active ? "success" : "destructive"} className="text-xs">
          {user.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      cell: (user) => <span className="text-sm text-muted-foreground">{formatDate(user.created_at)}</span>,
    },
    {
      key: "actions",
      header: "",
      cell: (user) => {
        const isSelf = isUserSelf(user)
        const isSuperAdmin = isSuperAdminUser(user)
        const cannotDeactivate = isSelf || isSuperAdmin
        const cannotDelete = isSelf || isSuperAdmin
        const cannotManageRoles = isSelf || isSuperAdmin

        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => {
                  if (!cannotManageRoles) {
                    setSelectedUser(user)
                    setRoleDialogOpen(true)
                  }
                }}
                disabled={cannotManageRoles}
                className={cannotManageRoles ? "text-muted-foreground opacity-40 cursor-not-allowed" : ""}
                title={
                  isSelf
                    ? "You cannot modify roles of your own account"
                    : isSuperAdmin
                    ? "Company SuperAdmin role is permanent and cannot be modified"
                    : undefined
                }
              >
                <Shield className="mr-2 h-4 w-4" />
                Manage Roles
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => !cannotDeactivate && handleToggleStatus(user)}
                disabled={cannotDeactivate || isToggling}
                className={
                  cannotDeactivate
                    ? "text-muted-foreground opacity-40 cursor-not-allowed"
                    : user.is_active
                    ? "text-amber-600 focus:text-amber-600 focus:bg-amber-50"
                    : "text-emerald-600 focus:text-emerald-600 focus:bg-emerald-50"
                }
                title={
                  isSelf
                    ? "You cannot change the status of your own account"
                    : isSuperAdmin
                    ? "Company SuperAdmin cannot be deactivated"
                    : undefined
                }
              >
                {user.is_active ? (
                  <>
                    <UserX className="mr-2 h-4 w-4" />
                    <span>Deactivate User</span>
                  </>
                ) : (
                  <>
                    <UserCheck className="mr-2 h-4 w-4" />
                    <span>Activate User</span>
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => {
                  if (cannotDelete) return
                  setSelectedUser(user)
                  setDeleteDialogOpen(true)
                }}
                disabled={cannotDelete}
                className={
                  cannotDelete
                    ? "text-muted-foreground opacity-40 cursor-not-allowed"
                    : "text-destructive focus:text-destructive focus:bg-destructive/10"
                }
                title={
                  isSelf
                    ? "You cannot delete your own account"
                    : isSuperAdmin
                    ? "Company SuperAdmin cannot be deleted"
                    : undefined
                }
              >
                <Trash2 className="mr-2 h-4 w-4" />
                <span>Delete User</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )
      },
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Users</h1>
          <p className="text-muted-foreground">Manage user accounts and permissions</p>
        </div>
        <Button onClick={() => setAddDialogOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Add User
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search users by name or email..."
                className="pl-9"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={users}
            total={total}
            page={page}
            perPage={perPage}
            onPageChange={setPage}
            isLoading={isLoading}
          />
        </CardContent>
      </Card>

      {/* ========================================================================= */}
      {/* ADD USER DIALOG                                                           */}
      {/* ========================================================================= */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add New User</DialogTitle>
            <DialogDescription>
              Create a new user account and assign system permissions.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateUser} className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="user-fullname">Full Name *</Label>
              <Input
                id="user-fullname"
                placeholder="e.g., John Doe"
                value={newUserForm.full_name}
                onChange={(e) => setNewUserForm({ ...newUserForm, full_name: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="user-email">Email Address *</Label>
              <Input
                id="user-email"
                type="email"
                placeholder="name@example.com"
                value={newUserForm.email}
                onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="user-password">Initial Password *</Label>
              <Input
                id="user-password"
                type="password"
                placeholder="••••••••"
                value={newUserForm.password}
                onChange={(e) => setNewUserForm({ ...newUserForm, password: e.target.value })}
                required
                minLength={6}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="user-phone">Phone Number (optional)</Label>
              <Input
                id="user-phone"
                placeholder="+1 234 567 8900"
                value={newUserForm.phone || ""}
                onChange={(e) => setNewUserForm({ ...newUserForm, phone: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Select Role *</Label>
              <div className="space-y-2 rounded-lg border p-2 bg-muted/20">
                {(availableRoles.length > 0 ? availableRoles : [
                  { id: 2, name: "Admin", description: "Company administrator with user, database, and audit management", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
                  { id: 3, name: "Analyst", description: "Can create connections, query data and build dashboards", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
                  { id: 4, name: "Viewer", description: "Can view shared dashboards and reports", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
                ])
                  .filter((role) => role.name !== "SuperAdmin")
                  .map((role) => {
                    const isSelected = newUserForm.role === role.name
                    return (
                      <div
                        key={role.id}
                        onClick={() => setNewUserForm({ ...newUserForm, role: role.name })}
                        className={`flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer transition-all ${
                          isSelected
                            ? "bg-primary/10 border-primary/40 shadow-sm"
                            : "bg-background border-border hover:bg-muted/50"
                        }`}
                      >
                        <div
                          className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                            isSelected ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/60"
                          }`}
                        >
                          {isSelected && <div className="h-1.5 w-1.5 rounded-full bg-background" />}
                        </div>
                        <div className="space-y-0.5 flex-1">
                          <div className="text-sm font-semibold flex items-center justify-between">
                            <span>{role.name}</span>
                            {role.name === "Admin" && (
                              <Badge variant="outline" className="text-[10px] py-0 px-1.5 bg-emerald-500/10 text-emerald-700 border-emerald-200">
                                Administrator
                              </Badge>
                            )}
                            {role.name === "Analyst" && (
                              <Badge variant="outline" className="text-[10px] py-0 px-1.5 bg-blue-500/10 text-blue-700 border-blue-200">
                                Default
                              </Badge>
                            )}
                            {role.name === "Viewer" && (
                              <Badge variant="outline" className="text-[10px] py-0 px-1.5 bg-slate-500/10 text-slate-700 border-slate-200">
                                Read Only
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">{role.description}</p>
                        </div>
                      </div>
                    )
                  })}
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setAddDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting || !newUserForm.email || !newUserForm.password || !newUserForm.full_name}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating User...
                  </>
                ) : (
                  "Create User"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ========================================================================= */}
      {/* MANAGE ROLES DIALOG                                                       */}
      {/* ========================================================================= */}
      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Manage User Role</DialogTitle>
            <DialogDescription>
              Assign role for <span className="font-semibold text-foreground">{selectedUser?.full_name}</span> ({selectedUser?.email})
            </DialogDescription>
          </DialogHeader>

          {isSuperAdminUser(selectedUser) ? (
            <div className="rounded-lg border border-purple-200 bg-purple-50/50 dark:bg-purple-950/20 p-4 text-center my-4 space-y-2">
              <div className="flex justify-center">
                <Shield className="h-8 w-8 text-purple-600 dark:text-purple-400" />
              </div>
              <p className="text-sm font-semibold text-purple-900 dark:text-purple-300">
                Company SuperAdmin (Owner)
              </p>
              <p className="text-xs text-purple-700 dark:text-purple-400">
                This account holds primary company ownership. The SuperAdmin role cannot be removed or demoted.
              </p>
            </div>
          ) : (
            <div className="space-y-3 py-4">
              {availableRoles
                .filter((role) => role.name !== "SuperAdmin")
                .map((role) => {
                  const isAssigned = selectedUser?.roles.some((r) => r.id === role.id || r.name === role.name)
                  const isUpdating = isUpdatingRole === role.id

                  return (
                    <div
                      key={role.id}
                      onClick={() => !isUpdating && !isAssigned && handleSetRoleForSelectedUser(role)}
                      className={`flex items-center justify-between p-3 rounded-lg border transition-all cursor-pointer ${
                        isAssigned
                          ? "bg-primary/10 border-primary/40 shadow-sm"
                          : "bg-card hover:bg-muted/50 border-border"
                      }`}
                    >
                      <div className="space-y-1 pr-4">
                        <div className="flex items-center gap-2">
                          <div
                            className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                              isAssigned ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/60"
                            }`}
                          >
                            {isAssigned && <div className="h-1.5 w-1.5 rounded-full bg-background" />}
                          </div>
                          <span className="font-medium text-sm">{role.name}</span>
                          {role.name === "Admin" && (
                            <Badge variant="outline" className="text-[10px] py-0 px-1.5 bg-emerald-500/10 text-emerald-700 border-emerald-200">
                              Administrator
                            </Badge>
                          )}
                          {role.name === "Analyst" && (
                            <Badge variant="outline" className="text-[10px] py-0 px-1.5 bg-blue-500/10 text-blue-700 border-blue-200">
                              Default
                            </Badge>
                          )}
                          {role.name === "Viewer" && (
                            <Badge variant="outline" className="text-[10px] py-0 px-1.5 bg-slate-500/10 text-slate-700 border-slate-200">
                              Read Only
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground pl-6">{role.description}</p>
                      </div>

                      <div>
                        {isUpdating ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : isAssigned ? (
                          <Badge variant="success" className="text-xs">
                            Active
                          </Badge>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleSetRoleForSelectedUser(role)
                            }}
                          >
                            Select
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ========================================================================= */}
      {/* DELETE USER CONFIRMATION                                                  */}
      {/* ========================================================================= */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
            <DialogDescription>
              Are you sure you want to deactivate and remove &quot;{selectedUser?.full_name}&quot;?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteUser}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
