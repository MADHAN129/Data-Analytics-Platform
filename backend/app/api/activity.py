from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.api.deps import get_current_user, user_has_permission
from app.models.user import User
from app.models.connection import DatabaseConnection
from app.models.query import Query as QueryModel
from app.models.conversation import Conversation, ConversationMessage
from app.models.audit import AuditLog
from app.schemas.activity import (
    ActivityOverviewResponse,
    ActivityQueryItem,
    ActivityDatabaseItem,
    TokenTimelineItem,
)

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("/overview", response_model=ActivityOverviewResponse)
def get_activity_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_admin = user_has_permission(db, current_user, "access.manage")

    # 1. Total tokens calculation
    query_tokens_q = db.query(func.coalesce(func.sum(QueryModel.tokens_used), 0))
    msg_tokens_q = db.query(func.coalesce(func.sum(ConversationMessage.tokens_used), 0))

    if not is_admin and current_user.company_id:
        query_tokens_q = query_tokens_q.filter(QueryModel.company_id == current_user.company_id)
        # join with conversation for company filter
        msg_tokens_q = msg_tokens_q.join(Conversation, ConversationMessage.conversation_id == Conversation.id).filter(Conversation.company_id == current_user.company_id)

    total_query_tokens = query_tokens_q.scalar() or 0
    total_msg_tokens = msg_tokens_q.scalar() or 0
    total_tokens = total_query_tokens + total_msg_tokens

    # 2. Total queries count
    queries_count_q = db.query(func.count(QueryModel.id))
    if not is_admin and current_user.company_id:
        queries_count_q = queries_count_q.filter(QueryModel.company_id == current_user.company_id)
    total_queries = queries_count_q.scalar() or 0

    # 3. Users count
    users_count_q = db.query(func.count(User.id))
    if not is_admin and current_user.company_id:
        users_count_q = users_count_q.filter(User.company_id == current_user.company_id)
    total_users = users_count_q.scalar() or 0

    # 4. Recent queries with user and database details
    queries_q = (
        db.query(QueryModel)
        .order_by(desc(QueryModel.created_at))
        .limit(100)
    )
    if not is_admin and current_user.company_id:
        queries_q = queries_q.filter(QueryModel.company_id == current_user.company_id)

    raw_queries = queries_q.all()

    # Pre-fetch users and databases mapping
    all_users = {u.id: u for u in db.query(User).all()}
    all_dbs = {d.id: d for d in db.query(DatabaseConnection).all()}

    recent_queries: List[ActivityQueryItem] = []
    for q in raw_queries:
        u = all_users.get(q.user_id)
        d = all_dbs.get(q.database_id)
        recent_queries.append(
            ActivityQueryItem(
                id=q.id,
                question=q.natural_language or "SQL Query",
                generated_sql=q.generated_sql,
                status=q.status or "completed",
                tokens_used=q.tokens_used or 0,
                execution_time_ms=q.execution_time_ms,
                row_count=q.row_count or 0,
                created_at=q.created_at or datetime.utcnow(),
                user_id=q.user_id,
                user_name=u.full_name if u else f"User #{q.user_id}",
                user_email=u.email if u else None,
                database_id=q.database_id,
                database_name=d.name if d else (f"Database #{q.database_id}" if q.database_id else "No Database"),
                database_type=d.connection_type if d else None,
                database_host=d.host if d else None,
                database_port=d.port if d else None,
            )
        )

    # 5. Database lifecycle items (Active + Inactive + Deleted Audit Logs)
    dbs_q = db.query(DatabaseConnection).order_by(desc(DatabaseConnection.created_at))
    if not is_admin and current_user.company_id:
        dbs_q = dbs_q.filter(DatabaseConnection.company_id == current_user.company_id)
    raw_dbs = dbs_q.all()

    database_lifecycle: List[ActivityDatabaseItem] = []
    seen_db_ids = set()

    for d in raw_dbs:
        seen_db_ids.add(str(d.id))
        u = all_users.get(d.created_by)
        is_active = bool(d.is_active)
        dismissed_at = d.updated_at if (not is_active and d.updated_at and d.updated_at > d.created_at) else None

        database_lifecycle.append(
            ActivityDatabaseItem(
                id=d.id,
                name=d.name,
                type=d.connection_type,
                host=d.host,
                port=d.port,
                database_name=d.database_name,
                username=d.username,
                is_active=is_active,
                health_status=d.health_status,
                health_latency_ms=d.health_latency_ms,
                created_at=d.created_at or datetime.utcnow(),
                updated_at=d.updated_at,
                dismissed_at=dismissed_at,
                created_by_user_id=d.created_by,
                created_by_name=u.full_name if u else f"User #{d.created_by}",
                created_by_email=u.email if u else None,
            )
        )

    # Cross-reference audit logs for deleted / dismissed databases
    audit_deleted_q = (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "database", AuditLog.action == "delete")
        .order_by(desc(AuditLog.created_at))
    )
    if not is_admin and current_user.company_id:
        audit_deleted_q = audit_deleted_q.filter(AuditLog.company_id == current_user.company_id)

    for al in audit_deleted_q.all():
        if al.resource_id and al.resource_id not in seen_db_ids:
            seen_db_ids.add(al.resource_id)
            details = al.details or {}
            u = all_users.get(al.user_id)
            try:
                db_id_int = int(al.resource_id)
            except Exception:
                db_id_int = 0

            database_lifecycle.append(
                ActivityDatabaseItem(
                    id=db_id_int,
                    name=details.get("name") or f"Dismissed DB #{al.resource_id}",
                    type=details.get("type", "postgresql"),
                    host=details.get("host", "disconnected"),
                    port=details.get("port", 5432),
                    database_name=details.get("database_name", "—"),
                    username=details.get("username", "—"),
                    is_active=False,
                    health_status=False,
                    health_latency_ms=None,
                    created_at=al.created_at,
                    updated_at=al.created_at,
                    dismissed_at=al.created_at,
                    created_by_user_id=al.user_id,
                    created_by_name=u.full_name if u else f"User #{al.user_id}",
                    created_by_email=u.email if u else None,
                )
            )

    active_databases = sum(1 for d in database_lifecycle if d.is_active)
    dismissed_databases = sum(1 for d in database_lifecycle if not d.is_active)
    total_databases = len(database_lifecycle)

    # 6. Token Timeline over the last N days
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    timeline_dict: Dict[str, Dict[str, int]] = defaultdict(lambda: {"tokens": 0, "queries": 0})

    # Fill daily buckets
    for i in range(days + 1):
        day_str = (cutoff_date + timedelta(days=i)).strftime("%Y-%m-%d")
        timeline_dict[day_str] = {"tokens": 0, "queries": 0}

    for q in raw_queries:
        if q.created_at and q.created_at.replace(tzinfo=None) >= cutoff_date:
            day_str = q.created_at.strftime("%Y-%m-%d")
            timeline_dict[day_str]["tokens"] += (q.tokens_used or 0)
            timeline_dict[day_str]["queries"] += 1

    token_timeline = [
        TokenTimelineItem(
            date=day,
            tokens=data["tokens"],
            queries_count=data["queries"],
        )
        for day, data in sorted(timeline_dict.items())
    ]

    return ActivityOverviewResponse(
        total_tokens=total_tokens,
        total_queries=total_queries,
        total_databases=total_databases,
        active_databases=active_databases,
        dismissed_databases=dismissed_databases,
        total_users=total_users,
        recent_queries=recent_queries,
        database_lifecycle=database_lifecycle,
        token_timeline=token_timeline,
    )
