// ============================================
// AUTHENTICATION TYPES
// ============================================

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  phone?: string
  company_name?: string
}

export interface LoginRequest {
  email: string
  password: string
  remember_me?: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserResponse
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface ForgotPasswordRequest {
  email: string
}

export interface ResetPasswordRequest {
  token: string
  new_password: string
}

// ============================================
// USER TYPES
// ============================================

export interface UserResponse {
  id: number
  email: string
  full_name: string
  phone: string | null
  avatar_url: string | null
  bio?: string | null
  company_id?: number | null
  company_name?: string | null
  auth_provider: "local" | "azure_ad" | "google"
  is_active: boolean
  mfa_enabled: boolean
  roles: RoleResponse[]
  created_at: string
  updated_at: string
}

export interface UpdateProfileRequest {
  full_name?: string
  phone?: string
  avatar_url?: string
  bio?: string
}

export interface CreateUserRequest {
  email: string
  password: string
  full_name: string
  phone?: string
  role?: string
  role_id?: number
  roles?: string[]
  role_ids?: number[]
}

export interface UserListResponse {
  users: UserResponse[]
  total: number
  page: number
  per_page: number
  pages: number
}

// ============================================
// ROLE TYPES
// ============================================

export interface RoleResponse {
  id: number
  name: string
  description: string
  is_system: boolean
  permissions: PermissionResponse[]
  user_count: number
  created_at: string
  updated_at: string
}

export interface CreateRoleRequest {
  name: string
  description?: string
  permission_ids?: number[]
}

export interface UpdateRoleRequest {
  name?: string
  description?: string
  permission_ids?: number[]
}

export interface RoleListResponse {
  roles: RoleResponse[]
  total: number
}

// ============================================
// PERMISSION TYPES
// ============================================

export interface PermissionResponse {
  id: number
  name: string
  resource: string
  action: string
  description: string
  created_at: string
}

export interface PermissionListResponse {
  permissions: PermissionResponse[]
  total: number
}

// ============================================
// AUDIT TYPES
// ============================================

export interface AuditLogResponse {
  id: number
  user_id: number
  user_email: string
  action: string
  resource_type: string
  resource_id: string | null
  details: Record<string, unknown> | null
  status: "success" | "failure"
  created_at: string
}

export interface AuditLogListResponse {
  logs: AuditLogResponse[]
  total: number
  page: number
  per_page: number
}

export interface AuditStats {
  total_events: number
  successful_events: number
  failed_events: number
  unique_users: number
  top_actions: Array<{ action: string; count: number }>
  top_users: Array<{ user_id: number; email: string; action_count: number }>
}

// ============================================
// COMMON TYPES
// ============================================

export interface ApiError {
  detail: string
  error_code?: string
  metadata?: Record<string, unknown>
}

export interface ValidationError {
  field: string
  message: string
  code: string
}

export interface ValidationErrorResponse {
  detail: string
  errors: ValidationError[]
}

export interface MessageResponse {
  message: string
}

export interface PaginationParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: "asc" | "desc"
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy"
  version: string
  timestamp: string
  services: {
    database: "connected" | "disconnected"
    redis: "connected" | "disconnected"
    llm: "ready" | "loading" | "error"
  }
}

// ============================================
// DATABASE CONNECTION TYPES
// ============================================

export type ConnectionType = "postgresql" | "mysql" | "sqlserver" | "mariadb" | "mongodb" | "oracle"

export interface DatabaseCreateRequest {
  name: string
  description?: string
  connection_type: ConnectionType
  host: string
  port: number
  database_name: string
  schema_name?: string
  username: string
  password: string
  ssl?: boolean
  pool_size?: number
  timeout_seconds?: number
}

export interface DatabaseUpdateRequest {
  name?: string
  description?: string
  connection_type?: ConnectionType
  host?: string
  port?: number
  database_name?: string
  schema_name?: string
  username?: string
  password?: string
  ssl?: boolean
  pool_size?: number
  timeout_seconds?: number
  is_active?: boolean
}

export interface DatabaseConnectionResponse {
  id: number
  name: string
  description: string | null
  connection_type: ConnectionType
  host: string
  port: number
  database_name: string
  schema_name: string
  username: string
  ssl: boolean
  is_active: boolean
  pool_size: number
  timeout_seconds: number
  health_status: boolean | null
  health_latency_ms: number | null
  health_checked_at: string | null
  last_sync_at: string | null
  created_by: number
  created_at: string
  updated_at: string
}

export interface ConnectionHealthResponse {
  healthy: boolean
  latency_ms: number | null
  checked_at: string
}

export interface ConnectionHealthItem {
  id: number
  name: string
  healthy: boolean
  latency_ms: number | null
  checked_at: string
}

export interface BatchHealthResponse {
  connections: ConnectionHealthItem[]
}

export interface DatabaseListResponse {
  connections: DatabaseConnectionResponse[]
  total: number
}

export interface DatabaseTestResult {
  success: boolean
  message: string
  latency_ms: number | null
  server_version: string | null
}

export interface SyncResult {
  database_id: number
  status: string
  tables_synced: number
  columns_synced: number
  duration_ms: number
  errors: string[]
  synced_at: string
}

export interface ColumnInfo {
  name: string
  data_type: string
  nullable: boolean
  is_primary_key: boolean
  is_foreign_key: boolean
  default_value: string | null
  max_length: number | null
}

export interface TableSchema {
  name: string
  schema_name: string
  type: string
  row_count: number | null
  columns: ColumnInfo[]
}

export interface SchemaResponse {
  database_id: number
  schema_name: string
  tables: TableSchema[]
  views: TableSchema[]
  last_synced_at: string | null
}

// ============================================
// PHASE 3: QUERY TYPES
// ============================================

export interface QueryRequest {
  database_id: number
  natural_language: string
  conversation_id?: number
  options?: {
    max_rows?: number
    timeout_seconds?: number
    include_metadata?: boolean
  }
}

export interface SQLExecutionRequest {
  database_id: number
  sql: string
  timeout_seconds?: number
}

export interface FollowUpRequest {
  natural_language: string
}

export interface VisualizationSuggestion {
  type: string
  title?: string
  config?: Record<string, unknown>
}

export interface QueryResult {
  columns: string[]
  rows: unknown[][]
  row_count: number
  execution_time_ms?: number
}

export interface QueryResponse {
  id: number
  status: "pending" | "executing" | "completed" | "failed" | "cancelled"
  natural_language: string
  generated_sql?: string
  explanation?: string
  results?: QueryResult
  suggested_visualizations?: VisualizationSuggestion[]
  tokens_used?: number
  conversation_id?: number
  parent_query_id?: number
  error_message?: string
  created_at: string
}

export interface QueryListResponse {
  queries: QueryResponse[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface ExplainResponse {
  explanation: string
  generated_sql: string
}

export interface OptimizeSuggestion {
  type: string
  description: string
  impact: "low" | "medium" | "high"
}

export interface OptimizeResponse {
  suggestions: OptimizeSuggestion[]
}

export interface VisualizeResponse {
  visualizations: VisualizationSuggestion[]
}

// ============================================
// PHASE 3: CONVERSATION TYPES
// ============================================

export interface ConversationResponse {
  id: number
  title?: string
  database_id?: number
  context?: Record<string, unknown>
  message_count: number
  total_tokens: number
  created_at: string
  updated_at: string
}

export interface ConversationListResponse {
  conversations: ConversationResponse[]
  total: number
}

export interface ClarificationOption {
  id: string
  label: string
  prompt: string
  description?: string
  icon?: string
}

export interface ConversationMessageResponse {
  id: number
  conversation_id: number
  role: "user" | "assistant" | "system"
  content: string
  tool_calls?: Array<Record<string, unknown>>
  generated_sql?: string
  results?: QueryResult
  clarification_options?: ClarificationOption[]
  quick_options?: string[]
  error_message?: string
  tokens_used?: number
  model_used?: string
  created_at: string
}

export interface UpdateConversationRequest {
  title?: string
  database_id?: number | null
}

export interface MessageListResponse {
  messages: ConversationMessageResponse[]
  total: number
}

export interface CreateConversationRequest {
  title?: string
  database_id?: number
}

export interface SendMessageRequest {
  content: string
}

// Phase 3: Query Templates
export interface TemplateCreateRequest {
  title: string
  description?: string
  natural_language: string
  generated_sql?: string
  database_id?: number
}

export interface TemplateUpdateRequest {
  title?: string
  description?: string
  natural_language?: string
  generated_sql?: string
}

export interface TemplateResponse {
  id: number
  title: string
  description?: string
  natural_language: string
  generated_sql?: string
  database_id?: number
  created_at: string
  updated_at: string
}

export interface TemplateListResponse {
  templates: TemplateResponse[]
  total: number
}

// ============================================
// PHASE 4: DASHBOARD TYPES
// ============================================

export interface WidgetConfig {
  widget_type: string
  title: string
  position_x: number
  position_y: number
  width: number
  height: number
  config?: Record<string, unknown>
  query_id?: number
}

export interface WidgetResponse {
  id: number
  dashboard_id: number
  query_id?: number
  widget_type: string
  title: string
  position_x: number
  position_y: number
  width: number
  height: number
  config?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface DashboardCreateRequest {
  title: string
  description?: string
  is_template?: boolean
}

export interface DashboardUpdateRequest {
  title?: string
  description?: string
  is_template?: boolean
  is_public?: boolean
}

export interface DashboardResponse {
  id: number
  title: string
  description?: string
  layout_config?: Record<string, unknown>
  is_template: boolean
  is_public: boolean
  auto_generated: boolean
  widget_count: number
  created_at: string
  updated_at: string
}

export interface DashboardDetailResponse {
  id: number
  title: string
  description?: string
  layout_config?: Record<string, unknown>
  is_template: boolean
  is_public: boolean
  auto_generated: boolean
  widgets: WidgetResponse[]
  created_at: string
  updated_at: string
}

export interface DashboardListResponse {
  dashboards: DashboardResponse[]
  total: number
}

export interface LayoutUpdateItem {
  id: number
  position_x: number
  position_y: number
  width: number
  height: number
}

export interface LayoutUpdateRequest {
  widgets: LayoutUpdateItem[]
}

export interface AutoGenerateRequest {
  database_id: number
  query_text?: string
}
