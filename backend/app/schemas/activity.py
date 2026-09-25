from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ActivityQueryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    generated_sql: Optional[str] = None
    status: str
    tokens_used: int = 0
    execution_time_ms: Optional[int] = None
    row_count: int = 0
    created_at: datetime
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    database_id: Optional[int] = None
    database_name: Optional[str] = None
    database_type: Optional[str] = None
    database_host: Optional[str] = None
    database_port: Optional[int] = None


class ActivityDatabaseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    host: str
    port: int
    database_name: str
    username: str
    is_active: bool
    health_status: Optional[bool] = None
    health_latency_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_by_user_id: int
    created_by_name: Optional[str] = None
    created_by_email: Optional[str] = None


class TokenTimelineItem(BaseModel):
    date: str
    tokens: int
    queries_count: int


class ActivityOverviewResponse(BaseModel):
    total_tokens: int
    total_queries: int
    total_databases: int
    active_databases: int
    dismissed_databases: int
    total_users: int
    recent_queries: List[ActivityQueryItem]
    database_lifecycle: List[ActivityDatabaseItem]
    token_timeline: List[TokenTimelineItem]
