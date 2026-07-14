from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TemplateCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    natural_language: str = Field(..., min_length=1, max_length=5000)
    generated_sql: Optional[str] = None
    database_id: Optional[int] = None


class TemplateUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    natural_language: Optional[str] = Field(None, min_length=1, max_length=5000)
    generated_sql: Optional[str] = None


class TemplateResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    natural_language: str
    generated_sql: Optional[str] = None
    database_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
    total: int
