from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PermissionResponse(BaseModel):
    id: int
    name: str
    resource: str
    action: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PermissionListResponse(BaseModel):
    permissions: List[PermissionResponse]
    total: int
