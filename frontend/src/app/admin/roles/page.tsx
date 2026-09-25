"use client"

import { useEffect, useState, useCallback } from "react"
import { api } from "@/lib/api-client"
import { apiCache } from "@/lib/api-cache"
import { useToast } from "@/components/ui/use-toast"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { DataTable, type Column } from "@/components/ui/data-table"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import type { RoleResponse, PermissionResponse } from "@/types/api"
import { formatDate } from "@/lib/utils"
import { Loader2, Plus, Shield, Trash2 } from "lucide-react"

export default function AdminRolesPage() {
  const [roles, setRoles] = useState<RoleResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [selectedRole, setSelectedRole] = useState<RoleResponse | null>(null)
  const [permissions, setPermissions] = useState<PermissionResponse[]>([])
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([])
  const [newRoleName, setNewRoleName] = useState("")
  const [newRoleDesc, setNewRoleDesc] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { toast } = useToast()

  const perPage = 20

  const fetchRoles = useCallback(async (forceFresh = false) => {
    const cacheKey = `roles:page=${page}`
    try {
      const { data } = await apiCache.swr(
        cacheKey,
        () => api.listRoles({ page, per_page: perPage }),
        {
          ttlMs: 45000,
          forceFresh,
          onRevalidate: (fresh) => {
            setRoles(fresh.roles)
            setTotal(fresh.total)
          },
        }
      )
      setRoles(data.roles)
      setTotal(data.total)
      setIsLoading(false)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to load roles", variant: "destructive" })
      setIsLoading(false)
    }
  }, [page, perPage, toast])

  useEffect(() => { fetchRoles() }, [fetchRoles])

  const fetchPermissions = async () => {
    try {
      const { data } = await apiCache.swr("permissions:all", () => api.listPermissions(), {
        ttlMs: 60000,
        onRevalidate: (fresh) => setPermissions(fresh.permissions),
      })
      setPermissions(data.permissions)
    } catch {
      toast({ title: "Error", description: "Failed to load permissions", variant: "destructive" })
    }
  }

  const handleCreateRole = async () => {
    if (!newRoleName.trim()) return
    setIsSubmitting(true)
    try {
      await api.createRole({
        name: newRoleName.trim(),
        description: newRoleDesc.trim() || undefined,
        permission_ids: selectedPermissionIds.length > 0 ? selectedPermissionIds : undefined,
      })
      apiCache.invalidate("roles")
      toast({ title: "Role created", variant: "success" })
      setCreateDialogOpen(false)
      setNewRoleName("")
      setNewRoleDesc("")
      setSelectedPermissionIds([])
      fetchRoles(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to create role", variant: "destructive" })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteRole = async (role: RoleResponse) => {
    if (role.is_system) {
      toast({ title: "Cannot delete system role", variant: "destructive" })
      return
    }
    try {
      await api.deleteRole(role.id)
      apiCache.invalidate("roles")
      toast({ title: "Role deleted", variant: "success" })
      fetchRoles(true)
    } catch (err: unknown) {
      const error = err as { detail?: string }
      toast({ title: "Error", description: error.detail || "Failed to delete role", variant: "destructive" })
    }
  }

  const openEditDialog = async (role: RoleResponse) => {
    setSelectedRole(role)
    setSelectedPermissionIds(role.permissions.map((p) => p.id))
    await fetchPermissions()
    setEditDialogOpen(true)
  }

  const openCreateDialog = async () => {
    setNewRoleName("")
    setNewRoleDesc("")
    setSelectedPermissionIds([])
    await fetchPermissions()
    setCreateDialogOpen(true)
  }

  const togglePermission = (permissionId: number) => {
    setSelectedPermissionIds((prev) =>
      prev.includes(permissionId)
        ? prev.filter((id) => id !== permissionId)
        : [...prev, permissionId]
    )
  }

  const columns: Column<RoleResponse>[] = [
    {
      key: "name",
      header: "Role",
      cell: (role) => (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Shield className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="font-medium">{role.name}</p>
            <p className="text-xs text-muted-foreground">{role.description}</p>
          </div>
        </div>
      ),
    },
    {
      key: "type",
      header: "Type",
      cell: (role) => (
        <Badge variant={role.is_system ? "secondary" : "outline"} className="text-xs">
          {role.is_system ? "System" : "Custom"}
        </Badge>
      ),
    },
    {
      key: "permissions",
      header: "Permissions",
      cell: (role) => (
        <span className="text-sm text-muted-foreground">
          {role.permissions.length} permission{role.permissions.length !== 1 ? "s" : ""}
        </span>
      ),
    },
    {
      key: "users",
      header: "Users",
      cell: (role) => (
        <span className="text-sm font-medium">{role.user_count}</span>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      cell: (role) => <span className="text-sm text-muted-foreground">{formatDate(role.created_at)}</span>,
    },
    {
      key: "actions",
      header: "",
      cell: (role) => (
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => openEditDialog(role)}>
            Edit
          </Button>
          {!role.is_system && (
            <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDeleteRole(role)}>
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Roles</h1>
          <p className="text-muted-foreground">Manage roles and permissions</p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="mr-2 h-4 w-4" />
          Create Role
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={roles}
            total={total}
            page={page}
            perPage={perPage}
            onPageChange={setPage}
            isLoading={isLoading}
          />
        </CardContent>
      </Card>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Role</DialogTitle>
            <DialogDescription>Create a new custom role with permissions</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="role-name">Role Name</Label>
              <Input id="role-name" value={newRoleName} onChange={(e) => setNewRoleName(e.target.value)} placeholder="e.g., Data Scientist" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role-desc">Description</Label>
              <Textarea id="role-desc" value={newRoleDesc} onChange={(e) => setNewRoleDesc(e.target.value)} placeholder="Role description" />
            </div>
            <div className="space-y-2">
              <Label>Permissions</Label>
              <div className="max-h-48 overflow-y-auto space-y-2 rounded-md border p-3">
                {permissions.map((perm) => (
                  <label key={perm.id} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPermissionIds.includes(perm.id)}
                      onChange={() => togglePermission(perm.id)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <div>
                      <p className="text-sm font-medium">{perm.name}</p>
                      <p className="text-xs text-muted-foreground">{perm.description}</p>
                    </div>
                  </label>
                ))}
                {permissions.length === 0 && (
                  <p className="text-sm text-muted-foreground">No permissions available</p>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateRole} disabled={isSubmitting || !newRoleName.trim()}>
              {isSubmitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...</> : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
