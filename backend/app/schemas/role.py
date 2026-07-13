from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.schemas.permission import PermissionResponse


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool
    permissions: List[PermissionResponse] = []
    user_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CreateRoleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleListResponse(BaseModel):
    roles: List[RoleResponse]
    total: int
