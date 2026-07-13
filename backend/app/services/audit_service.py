from typing import Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    status: str = "success",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=details,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()
    return log


def get_audit_logs(
    db: Session,
    page: int = 1,
    per_page: int = 50,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if status:
        query = query.filter(AuditLog.status == status)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    total = query.count()

    sort_column = getattr(AuditLog, sort_by, AuditLog.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    logs = query.offset((page - 1) * per_page).limit(per_page).all()

    # Enrich with user email
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        log_data = {
            "id": log.id,
            "user_id": log.user_id,
            "user_email": user.email if user else "unknown",
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "status": log.status,
            "created_at": log.created_at,
        }
        result.append(log_data)

    return result, total


def get_audit_stats(db: Session):
    total_events = db.query(AuditLog).count()
    successful_events = db.query(AuditLog).filter(AuditLog.status == "success").count()
    failed_events = db.query(AuditLog).filter(AuditLog.status == "failure").count()
    unique_users = db.query(AuditLog.user_id).distinct().count()

    top_actions = (
        db.query(AuditLog.action, func.count(AuditLog.id).label("count"))
        .group_by(AuditLog.action)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )

    top_users_data = (
        db.query(AuditLog.user_id, func.count(AuditLog.id).label("action_count"))
        .group_by(AuditLog.user_id)
        .order_by(desc("action_count"))
        .limit(10)
        .all()
    )

    top_users = []
    for user_id, action_count in top_users_data:
        user = db.query(User).filter(User.id == user_id).first()
        top_users.append({
            "user_id": user_id,
            "email": user.email if user else "unknown",
            "action_count": action_count,
        })

    return {
        "total_events": total_events,
        "successful_events": successful_events,
        "failed_events": failed_events,
        "unique_users": unique_users,
        "top_actions": [{"action": a, "count": c} for a, c in top_actions],
        "top_users": top_users,
    }
