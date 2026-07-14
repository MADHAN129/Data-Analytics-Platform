import type {
  RegisterRequest,
  LoginRequest,
  TokenResponse,
  RefreshTokenRequest,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  UserResponse,
  UpdateProfileRequest,
  UserListResponse,
  RoleResponse,
  RoleListResponse,
  CreateRoleRequest,
  UpdateRoleRequest,
  PermissionListResponse,
  AuditLogListResponse,
  AuditStats,
  MessageResponse,
  PaginationParams,
  HealthResponse,
  DatabaseCreateRequest,
  DatabaseUpdateRequest,
  DatabaseConnectionResponse,
  DatabaseListResponse,
  DatabaseTestResult,
  SyncResult,
  SchemaResponse,
  TableSchema,
  ColumnInfo,
  ConnectionHealthResponse,
  BatchHealthResponse,
  QueryRequest,
  SQLExecutionRequest,
  FollowUpRequest,
  QueryResponse,
  QueryListResponse,
  ExplainResponse,
  OptimizeResponse,
  VisualizeResponse,
  ConversationResponse,
  ConversationListResponse,
  ConversationMessageResponse,
  MessageListResponse,
  CreateConversationRequest,
  UpdateConversationRequest,
  SendMessageRequest,
  TemplateCreateRequest,
  TemplateUpdateRequest,
  TemplateResponse,
  TemplateListResponse,
} from "@/types/api"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

class ApiClient {
  private accessToken: string | null = null
  private _refreshToken: string | null = null
  private onUnauthorized: (() => void) | null = null

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token")
      this._refreshToken = localStorage.getItem("refresh_token")
    }
  }

  setTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken
    this._refreshToken = refreshToken
    localStorage.setItem("access_token", accessToken)
    localStorage.setItem("refresh_token", refreshToken)
  }

  clearTokens() {
    this.accessToken = null
    this._refreshToken = null
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
  }

  setOnUnauthorized(callback: () => void) {
    this.onUnauthorized = callback
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    }

    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (response.status === 401 && this._refreshToken) {
      const refreshed = await this.tryRefresh()
      if (refreshed) {
        headers["Authorization"] = `Bearer ${this.accessToken}`
        const retryResponse = await fetch(`${API_URL}${endpoint}`, {
          ...options,
          headers,
        })
        if (!retryResponse.ok) {
          throw await retryResponse.json()
        }
        return retryResponse.json()
      }
      this.clearTokens()
      this.onUnauthorized?.()
      throw new Error("Session expired")
    }

    if (!response.ok) {
      throw await response.json()
    }

    return response.json()
  }

  private async tryRefresh(): Promise<boolean> {
    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this._refreshToken }),
      })
      if (response.ok) {
        const data: TokenResponse = await response.json()
        this.setTokens(data.access_token, data.refresh_token)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  // ============================================
  // AUTHENTICATION
  // ============================================

  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    })
    this.setTokens(response.access_token, response.refresh_token)
    return response
  }

  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    })
    this.setTokens(response.access_token, response.refresh_token)
    return response
  }

  async logout(): Promise<MessageResponse> {
    const response = await this.request<MessageResponse>("/auth/logout", {
      method: "POST",
    })
    this.clearTokens()
    return response
  }

  async refreshToken(data: RefreshTokenRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify(data),
    })
    this.setTokens(response.access_token, response.refresh_token)
    return response
  }

  async changePassword(data: ChangePasswordRequest): Promise<MessageResponse> {
    return this.request<MessageResponse>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async forgotPassword(data: ForgotPasswordRequest): Promise<MessageResponse> {
    return this.request<MessageResponse>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async resetPassword(data: ResetPasswordRequest): Promise<MessageResponse> {
    return this.request<MessageResponse>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  // ============================================
  // USERS
  // ============================================

  async getCurrentUser(): Promise<UserResponse> {
    return this.request<UserResponse>("/users/me")
  }

  async updateProfile(data: UpdateProfileRequest): Promise<UserResponse> {
    return this.request<UserResponse>("/users/me", {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async listUsers(params?: PaginationParams & {
    search?: string
    is_active?: boolean
    role_id?: number
  }): Promise<UserListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    if (params?.search) query.set("search", params.search)
    if (params?.is_active !== undefined) query.set("is_active", String(params.is_active))
    if (params?.role_id) query.set("role_id", String(params.role_id))
    if (params?.sort_by) query.set("sort_by", params.sort_by)
    if (params?.sort_order) query.set("sort_order", params.sort_order)
    return this.request<UserListResponse>(`/users?${query.toString()}`)
  }

  async getUserById(userId: number): Promise<UserResponse> {
    return this.request<UserResponse>(`/users/${userId}`)
  }

  async updateUser(userId: number, data: UpdateProfileRequest): Promise<UserResponse> {
    return this.request<UserResponse>(`/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async deleteUser(userId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/users/${userId}`, {
      method: "DELETE",
    })
  }

  async activateUser(userId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/users/${userId}/activate`, {
      method: "POST",
    })
  }

  async deactivateUser(userId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/users/${userId}/deactivate`, {
      method: "POST",
    })
  }

  async assignRoleToUser(userId: number, roleId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/users/${userId}/roles`, {
      method: "POST",
      body: JSON.stringify({ role_id: roleId }),
    })
  }

  async removeRoleFromUser(userId: number, roleId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/users/${userId}/roles/${roleId}`, {
      method: "DELETE",
    })
  }

  // ============================================
  // ROLES
  // ============================================

  async listRoles(params?: PaginationParams): Promise<RoleListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    return this.request<RoleListResponse>(`/roles?${query.toString()}`)
  }

  async createRole(data: CreateRoleRequest): Promise<RoleResponse> {
    return this.request<RoleResponse>("/roles", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getRoleById(roleId: number): Promise<RoleResponse> {
    return this.request<RoleResponse>(`/roles/${roleId}`)
  }

  async updateRole(roleId: number, data: UpdateRoleRequest): Promise<RoleResponse> {
    return this.request<RoleResponse>(`/roles/${roleId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async deleteRole(roleId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/roles/${roleId}`, {
      method: "DELETE",
    })
  }

  async addPermissionToRole(roleId: number, permissionId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/roles/${roleId}/permissions`, {
      method: "POST",
      body: JSON.stringify({ permission_id: permissionId }),
    })
  }

  async removePermissionFromRole(roleId: number, permissionId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/roles/${roleId}/permissions/${permissionId}`, {
      method: "DELETE",
    })
  }

  // ============================================
  // PERMISSIONS
  // ============================================

  async listPermissions(params?: PaginationParams & { resource?: string }): Promise<PermissionListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    if (params?.resource) query.set("resource", params.resource)
    return this.request<PermissionListResponse>(`/permissions?${query.toString()}`)
  }

  // ============================================
  // AUDIT
  // ============================================

  async listAuditLogs(params?: PaginationParams & {
    user_id?: number
    action?: string
    resource_type?: string
    status?: "success" | "failure"
    start_date?: string
    end_date?: string
  }): Promise<AuditLogListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    if (params?.user_id) query.set("user_id", String(params.user_id))
    if (params?.action) query.set("action", params.action)
    if (params?.resource_type) query.set("resource_type", params.resource_type)
    if (params?.status) query.set("status", params.status)
    if (params?.start_date) query.set("start_date", params.start_date)
    if (params?.end_date) query.set("end_date", params.end_date)
    return this.request<AuditLogListResponse>(`/audit/logs?${query.toString()}`)
  }

  async getAuditStats(): Promise<AuditStats> {
    return this.request<AuditStats>("/audit/stats")
  }

  // ============================================
  // DATABASE CONNECTIONS
  // ============================================

  async listDatabases(params?: PaginationParams & {
    search?: string
    connection_type?: string
  }): Promise<DatabaseListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    if (params?.search) query.set("search", params.search)
    if (params?.connection_type) query.set("connection_type", params.connection_type)
    if (params?.sort_by) query.set("sort_by", params.sort_by)
    if (params?.sort_order) query.set("sort_order", params.sort_order)
    return this.request<DatabaseListResponse>(`/connections?${query.toString()}`)
  }

  async createDatabase(data: DatabaseCreateRequest): Promise<DatabaseConnectionResponse> {
    return this.request<DatabaseConnectionResponse>("/connections", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getDatabaseById(id: number): Promise<DatabaseConnectionResponse> {
    return this.request<DatabaseConnectionResponse>(`/connections/${id}`)
  }

  async updateDatabase(id: number, data: DatabaseUpdateRequest): Promise<DatabaseConnectionResponse> {
    return this.request<DatabaseConnectionResponse>(`/connections/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async deleteDatabase(id: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/connections/${id}`, {
      method: "DELETE",
    })
  }

  async testDatabaseConnection(id: number): Promise<DatabaseTestResult> {
    return this.request<DatabaseTestResult>(`/connections/${id}/test`, {
      method: "POST",
    })
  }

  async getConnectionHealth(id: number): Promise<ConnectionHealthResponse> {
    return this.request<ConnectionHealthResponse>(`/connections/${id}/health`)
  }

  async getBatchConnectionHealth(): Promise<BatchHealthResponse> {
    return this.request<BatchHealthResponse>("/connections/health/batch")
  }

  async syncDatabaseSchema(id: number): Promise<SyncResult> {
    return this.request<SyncResult>(`/connections/${id}/sync`, {
      method: "POST",
    })
  }

  async getDatabaseSchema(id: number): Promise<SchemaResponse> {
    return this.request<SchemaResponse>(`/connections/${id}/schema`)
  }

  async getDatabaseTables(id: number): Promise<TableSchema[]> {
    const res = await this.request<{ tables: TableSchema[] }>(`/connections/${id}/tables`)
    return res.tables
  }

  async getDatabaseTableDetail(id: number, tableName: string): Promise<TableSchema> {
    return this.request<TableSchema>(`/connections/${id}/tables/${encodeURIComponent(tableName)}`)
  }

  // ============================================
  // PHASE 3: QUERIES
  // ============================================

  async listQueries(params?: PaginationParams & {
    database_id?: number
    status?: string
  }): Promise<QueryListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    if (params?.database_id) query.set("database_id", String(params.database_id))
    if (params?.status) query.set("status", params.status)
    return this.request<QueryListResponse>(`/queries?${query.toString()}`)
  }

  async executeQuery(data: QueryRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>("/queries", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getQueryById(queryId: number): Promise<QueryResponse> {
    return this.request<QueryResponse>(`/queries/${queryId}`)
  }

  async executeRawSql(data: SQLExecutionRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>("/queries/sql", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async cancelQuery(queryId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/queries/${queryId}/cancel`, {
      method: "POST",
    })
  }

  async queryFollowUp(queryId: number, data: FollowUpRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>(`/queries/${queryId}/follow-up`, {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async explainQuery(queryId: number): Promise<ExplainResponse> {
    return this.request<ExplainResponse>(`/queries/${queryId}/explain`)
  }

  async optimizeQuery(queryId: number): Promise<OptimizeResponse> {
    return this.request<OptimizeResponse>(`/queries/${queryId}/optimize`, {
      method: "POST",
    })
  }

  async visualizeQuery(queryId: number): Promise<VisualizeResponse> {
    return this.request<VisualizeResponse>(`/queries/${queryId}/visualize`, {
      method: "POST",
    })
  }

  // ============================================
  // PHASE 3: CONVERSATIONS
  // ============================================

  async listConversations(params?: PaginationParams): Promise<ConversationListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    return this.request<ConversationListResponse>(`/conversations?${query.toString()}`)
  }

  async createConversation(data?: CreateConversationRequest): Promise<ConversationResponse> {
    return this.request<ConversationResponse>("/conversations", {
      method: "POST",
      body: JSON.stringify(data || {}),
    })
  }

  async getConversationById(conversationId: number): Promise<ConversationResponse> {
    return this.request<ConversationResponse>(`/conversations/${conversationId}`)
  }

  async deleteConversation(conversationId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/conversations/${conversationId}`, {
      method: "DELETE",
    })
  }

  async updateConversation(conversationId: number, data: UpdateConversationRequest): Promise<ConversationResponse> {
    return this.request<ConversationResponse>(`/conversations/${conversationId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
  }

  async getConversationMessages(
    conversationId: number,
    params?: PaginationParams,
  ): Promise<MessageListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    return this.request<MessageListResponse>(
      `/conversations/${conversationId}/messages?${query.toString()}`,
    )
  }

  async sendMessage(
    conversationId: number,
    data: SendMessageRequest,
  ): Promise<ConversationMessageResponse> {
    return this.request<ConversationMessageResponse>(
      `/conversations/${conversationId}/messages`,
      { method: "POST", body: JSON.stringify(data) },
    )
  }

  // ============================================
  // PHASE 3: QUERY TEMPLATES
  // ============================================

  async listTemplates(params?: { page?: number; per_page?: number; search?: string }): Promise<TemplateListResponse> {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", String(params.page))
    if (params?.per_page) query.set("per_page", String(params.per_page))
    if (params?.search) query.set("search", params.search)
    return this.request<TemplateListResponse>(`/templates?${query.toString()}`)
  }

  async createTemplate(data: TemplateCreateRequest): Promise<TemplateResponse> {
    return this.request<TemplateResponse>("/templates", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getTemplateById(templateId: number): Promise<TemplateResponse> {
    return this.request<TemplateResponse>(`/templates/${templateId}`)
  }

  async updateTemplate(templateId: number, data: TemplateUpdateRequest): Promise<TemplateResponse> {
    return this.request<TemplateResponse>(`/templates/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async deleteTemplate(templateId: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/templates/${templateId}`, {
      method: "DELETE",
    })
  }

  // ============================================
  // PHASE 3: QUERY SUGGESTIONS
  // ============================================

  async querySuggestions(q: string): Promise<string[]> {
    return this.request<string[]>(`/queries/suggestions?q=${encodeURIComponent(q)}`)
  }

  // ============================================
  // HEALTH
  // ============================================

  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health")
  }
}

export const api = new ApiClient()
