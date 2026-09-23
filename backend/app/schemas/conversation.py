from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.query import QueryResult


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    database_id: Optional[int] = None
    context: Optional[dict] = None
    message_count: int = 0
    total_tokens: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class ConversationMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    tool_calls: Optional[list] = None
    generated_sql: Optional[str] = None
    results: Optional[QueryResult] = None
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: list[ConversationMessageResponse]
    total: int


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None
    database_id: Optional[int] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    database_id: Optional[int] = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    message: str
