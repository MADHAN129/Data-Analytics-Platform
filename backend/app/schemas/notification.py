from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    company_id: Optional[int] = None
    title: str
    message: str
    type: str = "security_alert"
    severity: str = "high"
    is_read: bool = False
    data: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_ids: Optional[list[int]] = None
