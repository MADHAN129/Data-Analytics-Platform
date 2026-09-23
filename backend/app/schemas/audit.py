from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    user_email: str = ""
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    per_page: int


class AuditStats(BaseModel):
    total_events: int
    successful_events: int
    failed_events: int
    unique_users: int
    top_actions: List[Dict[str, Any]]
    top_users: List[Dict[str, Any]]
