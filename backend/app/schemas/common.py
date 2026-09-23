from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    metadata: Optional[dict] = None


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    services: dict
