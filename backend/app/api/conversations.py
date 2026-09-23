from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationResponse, ConversationListResponse,
    ConversationMessageResponse, MessageListResponse,
    CreateConversationRequest, UpdateConversationRequest,
    SendMessageRequest, MessageResponse,
)
from app.services import conversation_service
from app.services.audit_service import create_audit_log

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations, total = conversation_service.list_conversations(db, current_user.id, page, per_page)
    return ConversationListResponse(conversations=conversations, total=total)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: CreateConversationRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data is None:
        data = CreateConversationRequest()
    result = conversation_service.create_conversation(db, data, current_user.id)
    create_audit_log(
        db, current_user.id, "create", "conversation",
        result.id, {"title": result.title},
    )
    return result


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return conversation_service.get_conversation(db, conversation_id, current_user.id)


@router.delete("/{conversation_id}", response_model=MessageResponse)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation_service.delete_conversation(db, conversation_id, current_user.id)
    create_audit_log(db, current_user.id, "delete", "conversation", conversation_id)
    return MessageResponse(message="Conversation deleted")


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    data: UpdateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = conversation_service.update_conversation(db, conversation_id, data, current_user.id)
    create_audit_log(
        db, current_user.id, "update", "conversation",
        conversation_id, {"title": data.title},
    )
    return result


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def get_messages(
    conversation_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages, total = conversation_service.get_messages(db, conversation_id, current_user.id, page, per_page)
    return MessageListResponse(messages=messages, total=total)


@router.post("/{conversation_id}/messages", response_model=ConversationMessageResponse)
def send_message(
    conversation_id: int,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = conversation_service.send_message(db, conversation_id, data, current_user.id)
    create_audit_log(
        db, current_user.id, "send_message", "conversation",
        conversation_id, {"message_id": result.id},
    )
    return result
