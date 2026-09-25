from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse, MarkReadRequest
from app.schemas.common import MessageResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total, unread_count = notification_service.list_notifications(
        db, current_user.id, unread_only=unread_only, limit=limit, page=page,
    )
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
    )


@router.put("/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success = notification_service.mark_notification_read(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return MessageResponse(message="Notification marked as read")


@router.put("/read-all", response_model=MessageResponse)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = notification_service.mark_all_read(db, current_user.id)
    return MessageResponse(message=f"Marked {count} notifications as read")


@router.delete("/{notification_id}", response_model=MessageResponse)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success = notification_service.delete_notification(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return MessageResponse(message="Notification deleted")
