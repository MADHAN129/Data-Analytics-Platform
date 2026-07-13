from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseConnectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    connection_type: str = Field(..., pattern=r"^(postgresql|mysql|sqlserver|mariadb|mongodb|oracle|snowflake|bigquery|sqlite)$")
    host: str
    port: int = Field(..., ge=1, le=65535)
    database_name: str
    schema_name: str = "public"
    username: str
    password: str
    ssl: bool = False
    pool_size: int = Field(10, ge=1, le=100)
    timeout_seconds: int = Field(30, ge=5, le=300)


class DatabaseConnectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    connection_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: Optional[bool] = None
    pool_size: Optional[int] = None
    timeout_seconds: Optional[int] = None
    is_active: Optional[bool] = None


class DatabaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    connection_type: str
    host: str
    port: int
    database_name: str
    schema_name: str
    username: str
    ssl: bool = False
    health_status: Optional[bool] = None
    health_latency_ms: Optional[int] = None
    health_checked_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionHealthResponse(BaseModel):
    healthy: bool
    latency_ms: Optional[int] = None
    checked_at: datetime


class ConnectionHealthItem(BaseModel):
    id: int
    name: str
    healthy: bool
    latency_ms: Optional[int] = None
    checked_at: datetime


class BatchHealthResponse(BaseModel):
    connections: list[ConnectionHealthItem]


class DatabaseListResponse(BaseModel):
    connections: list[DatabaseResponse]
    total: int


class DatabaseTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[int] = None
    server_version: Optional[str] = None


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    default_value: Optional[str] = None
    max_length: Optional[int] = None


class TableSchema(BaseModel):
    name: str
    schema_name: str = "public"
    type: str = "table"
    row_count: Optional[int] = None
    columns: list[ColumnInfo]


class SchemaResponse(BaseModel):
    database_id: int
    schema_name: str
    tables: list[TableSchema]
    views: list[TableSchema]
    last_synced_at: Optional[datetime] = None


class SyncResult(BaseModel):
    database_id: int
    status: str
    tables_synced: int
    columns_synced: int
    duration_ms: int
    errors: list[str] = []
    synced_at: datetime
