from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WidgetConfig(BaseModel):
    widget_type: str
    title: str
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4
    config: Optional[dict] = None
    query_id: Optional[int] = None


class WidgetResponse(BaseModel):
    id: int
    dashboard_id: int
    query_id: Optional[int] = None
    widget_type: str
    title: str
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4
    config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_template: bool = False


class DashboardUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_template: Optional[bool] = None
    is_public: Optional[bool] = None


class DashboardResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    layout_config: Optional[dict] = None
    is_template: bool = False
    is_public: bool = False
    auto_generated: bool = False
    widget_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardDetailResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    layout_config: Optional[dict] = None
    is_template: bool = False
    is_public: bool = False
    auto_generated: bool = False
    widgets: list[WidgetResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardListResponse(BaseModel):
    dashboards: list[DashboardResponse]
    total: int


class LayoutUpdateItem(BaseModel):
    id: int
    position_x: int
    position_y: int
    width: int
    height: int


class LayoutUpdateRequest(BaseModel):
    widgets: list[LayoutUpdateItem]


class AutoGenerateRequest(BaseModel):
    database_id: int
    query_text: Optional[str] = None
