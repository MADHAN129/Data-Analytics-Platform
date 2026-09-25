"""In-App Notification Service for Data-Taker.

Handles creation, retrieval, and management of user and superadmin notifications
for security incidents, database health alerts, and system events.
"""

import logging
from typing import Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.notification import Notification
from app.models.user import User
from app.services.security_guard_service import get_dynamic_superadmins

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str = "security_alert",
    severity: str = "high",
    data: Optional[dict[str, Any]] = None,
    company_id: Optional[int] = None,
) -> Notification:
    """Create and persist an in-app notification for a specific user."""
    if company_id is None and user_id > 0:
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            company_id = u.company_id

    notif = Notification(
        user_id=user_id,
        company_id=company_id,
        title=title,
        message=message,
        type=type,
        severity=severity,
        is_read=False,
        data=data,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Optional real-time WebSocket notification dispatch
    try:
        from app.services.ws_manager import manager
        import asyncio
        payload = {
            "type": "notification",
            "data": {
                "id": notif.id,
                "title": notif.title,
                "message": notif.message,
                "type": notif.type,
                "severity": notif.severity,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
            }
        }
        # In sync context, attempt broadcast if loop is running
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(manager.broadcast(payload))
        except Exception:
            pass
    except Exception:
        pass

    return notif


def create_security_violation_notifications(
    db: Session,
    offender_user_id: Optional[int],
    offender_name: str,
    offender_email: str,
    company_id: Optional[int],
    violation_type: str,
    reason: str,
    natural_language: Optional[str],
    attempted_sql: Optional[str],
    source: str,
    timestamp: str,
) -> list[Notification]:
    """Create in-app notifications for SuperAdmins and the involved user when a security violation occurs."""
    created_notifs = []
    
    # 1. Discover SuperAdmins dynamically (Strictly NO hardcoding)
    superadmins = get_dynamic_superadmins(db, company_id=company_id)
    
    admin_notif_data = {
        "violation_type": violation_type,
        "reason": reason,
        "offender_name": offender_name,
        "offender_email": offender_email,
        "offender_user_id": offender_user_id,
        "natural_language": natural_language,
        "attempted_sql": attempted_sql,
        "source": source,
        "timestamp": timestamp,
        "action_taken": "BLOCKED (Read-only protection enforced)",
    }

    # Dispatch to all discovered SuperAdmins
    notified_user_ids = set()
    for sa in superadmins:
        if sa.id not in notified_user_ids:
            notified_user_ids.add(sa.id)
            notif = create_notification(
                db=db,
                user_id=sa.id,
                title=f"🚨 Security Alert: Prohibited {violation_type} Intercepted",
                message=f"User {offender_name} ({offender_email}) attempted a prohibited operation via {source}: {reason}",
                type="security_alert",
                severity="critical" if "DROP" in violation_type or "INJECTION" in violation_type else "high",
                data=admin_notif_data,
                company_id=sa.company_id or company_id,
            )
            created_notifs.append(notif)

    # 2. Also notify the offending user if they are a registered user and not already notified
    if offender_user_id and offender_user_id > 0 and offender_user_id not in notified_user_ids:
        user_notif_data = {
            "violation_type": violation_type,
            "reason": reason,
            "natural_language": natural_language,
            "attempted_sql": attempted_sql,
            "timestamp": timestamp,
            "status": "Blocked by system guardrail",
        }
        user_notif = create_notification(
            db=db,
            user_id=offender_user_id,
            title="⚠️ Security Guardrail Warning: Operation Blocked",
            message=f"Your recent request was blocked by security policy: {reason}. This incident has been logged and reported.",
            type="security_warning",
            severity="high",
            data=user_notif_data,
            company_id=company_id,
        )
        created_notifs.append(user_notif)

    return created_notifs


def list_notifications(
    db: Session,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
    page: int = 1,
) -> tuple[list[Notification], int, int]:
    """List notifications for a user, along with total count and unread count."""
    base_query = db.query(Notification).filter(Notification.user_id == user_id)
    
    total = base_query.count()
    unread_count = base_query.filter(Notification.is_read == False).count()

    query = base_query
    if unread_only:
        query = query.filter(Notification.is_read == False)

    offset = (page - 1) * limit
    items = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()

    return items, total, unread_count


def mark_notification_read(db: Session, notification_id: int, user_id: int) -> bool:
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not notif:
        return False
    notif.is_read = True
    db.commit()
    return True


def mark_all_read(db: Session, user_id: int) -> int:
    """Mark all unread notifications for a user as read."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return count


def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
    """Delete a notification."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not notif:
        return False
    db.delete(notif)
    db.commit()
    return True
