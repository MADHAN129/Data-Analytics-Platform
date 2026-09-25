"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
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

const defaultNewUserForm: CreateUserRequest = {
  full_name: "",
  email: "",
  password: "",
  phone: "",
  roles: ["Analyst"],
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserResponse[]>([])
  const [availableRoles, setAvailableRoles] = useState<RoleResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null)
  
  // Dialogs
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [roleDialogOpen, setRoleDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  
  // Form states
  const [newUserForm, setNewUserForm] = useState<CreateUserRequest>({ ...defaultNewUserForm })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [isUpdatingRole, setIsUpdatingRole] = useState<number | null>(null)
  
  const { toast } = useToast()
  const perPage = 20

  const fetchRoles = useCallback(async () => {
    try {
      const data = await api.listRoles()
      setAvailableRoles(data.roles || [])
    } catch {
      // Fallback roles if list fails
      setAvailableRoles([
        { id: 1, name: "SuperAdmin", description: "Full system access with all permissions", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
        { id: 2, name: "Analyst", description: "Can create connections, query data and build dashboards", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
        { id: 3, name: "Viewer", description: "Can view shared dashboards and reports", is_system: true, permissions: [], user_count: 0, created_at: "", updated_at: "" },
      ])
    }
  }, [])

  const fetchUsers = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await api.listUsers({ page, per_page: perPage, search: search || undefined })
      setUsers(data.users)
      setTotal(data.total)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to load users", variant: "destructive" })
    } finally {
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
      await api.createUser({
        full_name: newUserForm.full_name.trim(),
        email: newUserForm.email.trim(),
        password: newUserForm.password,
        phone: newUserForm.phone?.trim() || undefined,
        roles: newUserForm.roles && newUserForm.roles.length > 0 ? newUserForm.roles : ["Analyst"],
      })
      toast({ title: "User created successfully", variant: "success" })
      setAddDialogOpen(false)
      setNewUserForm({ ...defaultNewUserForm })
      fetchUsers()
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
    setIsToggling(true)
    try {
      if (user.is_active) {
        await api.deactivateUser(user.id)
        toast({ title: "User deactivated", variant: "success" })
      } else {
        await api.activateUser(user.id)
        toast({ title: "User activated", variant: "success" })
      }
      fetchUsers()
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Operation failed", variant: "destructive" })
    } finally {
      setIsToggling(false)
    }
  }

  const handleDeleteUser = async () => {
    if (!selectedUser) return
    try {
      await api.deleteUser(selectedUser.id)
      toast({ title: "User deleted", variant: "success" })
      setDeleteDialogOpen(false)
      setSelectedUser(null)
      fetchUsers()
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to delete user", variant: "destructive" })
    }
  }

  const handleToggleRoleForSelectedUser = async (role: RoleResponse) => {
    if (!selectedUser) return
    const hasRole = selectedUser.roles.some((r) => r.id === role.id || r.name === role.name)
    setIsUpdatingRole(role.id)

    try {
      if (hasRole) {
        await api.removeRoleFromUser(selectedUser.id, role.id)
        toast({ title: `Removed ${role.name} role`, variant: "success" })
        const updatedRoles = selectedUser.roles.filter((r) => r.id !== role.id && r.name !== role.name)
        setSelectedUser({ ...selectedUser, roles: updatedRoles })
      } else {
        await api.assignRoleToUser(selectedUser.id, role.id)
        toast({ title: `Assigned ${role.name} role`, variant: "success" })
        const updatedRoles = [...selectedUser.roles, role]
        setSelectedUser({ ...selectedUser, roles: updatedRoles })
      }
      fetchUsers()
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error updating role", description: error.detail || "Operation failed", variant: "destructive" })
    } finally {
      setIsUpdatingRole(null)
    }
  }

  const toggleNewUserRole = (roleName: string) => {
    const currentRoles = newUserForm.roles || []
    if (currentRoles.includes(roleName)) {
      if (currentRoles.length === 1) {
        toast({ title: "At least one role must be selected", variant: "destructive" })
        return
      }
      setNewUserForm({
        ...newUserForm,
        roles: currentRoles.filter((r) => r !== roleName),
      })
    } else {
      setNewUserForm({
        ...newUserForm,
        roles: [...currentRoles, roleName],
      })
    }
  }

  const columns: Column<UserResponse>[] = [
    {
      key: "user",
      header: "User",
      cell: (user) => (
        <div className="flex items-center gap-3">
          <Avatar className="h-9 w-9">
            <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
              {getInitials(user.full_name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <p className="font-medium">{user.full_name}</p>
            <p className="text-xs text-muted-foreground">{user.email}</p>
          </div>
        </div>
      ),
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
                    ? "bg-purple-500/10 text-purple-700 border-purple-200"
                    : role.name === "Analyst"
                    ? "bg-blue-500/10 text-blue-700 border-blue-200"
                    : "bg-slate-500/10 text-slate-700 border-slate-200"
                }`}
              >
                {role.name}
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
      cell: (user) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => { setSelectedUser(user); setRoleDialogOpen(true) }}>
              <Shield className="mr-2 h-4 w-4" />
              Manage Roles
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => handleToggleStatus(user)}
              disabled={isToggling}
              className={user.is_active ? "text-amber-600" : "text-emerald-600"}
            >
              {user.is_active ? (
                <>
                  <UserX className="mr-2 h-4 w-4" />
                  Deactivate User
                </>
              ) : (
                <>
                  <UserCheck className="mr-2 h-4 w-4" />
                  Activate User
                </>
              )}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => { setSelectedUser(user); setDeleteDialogOpen(true) }}
              className="text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete User
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
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
              <Label>Select Roles *</Label>
              <div className="space-y-2 rounded-lg border p-3">
                {availableRoles.length > 0 ? (
                  availableRoles.map((role) => {
                    const isChecked = (newUserForm.roles || []).includes(role.name)
                    return (
                      <div
                        key={role.id}
                        onClick={() => toggleNewUserRole(role.name)}
                        className={`flex items-start gap-3 p-2 rounded-md cursor-pointer transition-colors ${
                          isChecked ? "bg-primary/10 border border-primary/20" : "hover:bg-muted"
                        }`}
                      >
                        <div
                          className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                            isChecked ? "bg-primary text-primary-foreground border-primary" : "border-muted-foreground"
                          }`}
                        >
                          {isChecked && <Check className="h-3 w-3 stroke-[3]" />}
                        </div>
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium leading-none flex items-center gap-2">
                            <span>{role.name}</span>
                            {role.name === "SuperAdmin" && (
                              <Badge variant="outline" className="text-[10px] py-0 px-1 bg-purple-50 text-purple-700">
                                Full Access
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">{role.description}</p>
                        </div>
                      </div>
                    )
                  })
                ) : (
                  <div className="space-y-2">
                    {["SuperAdmin", "Analyst", "Viewer"].map((rName) => {
                      const isChecked = (newUserForm.roles || []).includes(rName)
                      return (
                        <div
                          key={rName}
                          onClick={() => toggleNewUserRole(rName)}
                          className={`flex items-center gap-3 p-2 rounded-md cursor-pointer ${
                            isChecked ? "bg-primary/10" : "hover:bg-muted"
                          }`}
                        >
                          <div
                            className={`flex h-4 w-4 items-center justify-center rounded border ${
                              isChecked ? "bg-primary text-primary-foreground" : "border-muted-foreground"
                            }`}
                          >
                            {isChecked && <Check className="h-3 w-3 stroke-[3]" />}
                          </div>
                          <span className="text-sm font-medium">{rName}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
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
            <DialogTitle>Manage Roles</DialogTitle>
            <DialogDescription>
              Assign or remove roles for <span className="font-semibold text-foreground">{selectedUser?.full_name}</span> ({selectedUser?.email})
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-4">
            {availableRoles.map((role) => {
              const isAssigned = selectedUser?.roles.some((r) => r.id === role.id || r.name === role.name)
              const isUpdating = isUpdatingRole === role.id

              return (
                <div
                  key={role.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                >
                  <div className="space-y-1 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{role.name}</span>
                      {role.name === "SuperAdmin" && (
                        <Badge variant="outline" className="text-[10px] py-0 px-1 bg-purple-50 text-purple-700">
                          SuperAdmin
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{role.description}</p>
                  </div>

                  <Button
                    size="sm"
                    variant={isAssigned ? "outline" : "default"}
                    disabled={isUpdating}
                    onClick={() => handleToggleRoleForSelectedUser(role)}
                    className={isAssigned ? "border-destructive text-destructive hover:bg-destructive/10" : ""}
                  >
                    {isUpdating ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : isAssigned ? (
                      "Remove"
                    ) : (
                      "Assign"
                    )}
                  </Button>
                </div>
              )
            })}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialogOpen(false)}>
              Done
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
