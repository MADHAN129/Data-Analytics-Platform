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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { UserResponse } from "@/types/api"
import { getInitials, formatDate } from "@/lib/utils"
import { Loader2, MoreVertical, Search, Shield, UserPlus } from "lucide-react"

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null)
  const [roleDialogOpen, setRoleDialogOpen] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const { toast } = useToast()

  const perPage = 20

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

  useEffect(() => { fetchUsers() }, [fetchUsers])

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

  const columns: Column<UserResponse>[] = [
    {
      key: "user",
      header: "User",
      cell: (user) => (
        <div className="flex items-center gap-3">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-primary/10 text-primary text-xs">
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
        <div className="flex flex-wrap gap-1">
          {user.roles.length > 0 ? (
            user.roles.map((role) => (
              <Badge key={role.id} variant="secondary" className="text-xs">
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
        <Badge variant="outline" className="text-xs">
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
              className={user.is_active ? "text-destructive" : "text-emerald-600"}
            >
              {user.is_active ? "Deactivate" : "Activate"}
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
        <Button>
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
                placeholder="Search users..."
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

      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Manage Roles</DialogTitle>
            <DialogDescription>
              Manage roles for {selectedUser?.full_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedUser?.roles.map((role) => (
              <div key={role.id} className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{role.name}</p>
                  <p className="text-sm text-muted-foreground">{role.description}</p>
                </div>
                <Badge>{role.is_system ? "System" : "Custom"}</Badge>
              </div>
            ))}
            {selectedUser?.roles.length === 0 && (
              <p className="text-sm text-muted-foreground">No roles assigned</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
