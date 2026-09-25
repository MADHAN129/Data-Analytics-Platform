import pytest
from datetime import datetime
from unittest.mock import patch
from app.models.user import User, UserRole
from app.models.role import Role
from app.models.notification import Notification
from app.services.notification_service import (
    create_security_violation_notifications,
    list_notifications,
    mark_notification_read,
    mark_all_read,
    delete_notification,
)
from app.services.security_guard_service import trigger_security_incident
from app.utils.security import get_password_hash


def test_create_security_violation_notifications(db_session):
    # Dynamically create roles and dynamic users
    super_role = Role(name="SuperAdmin", description="System Super Admin", is_system=True)
    db_session.add(super_role)
    db_session.commit()
    db_session.refresh(super_role)

    # Dynamic superadmin user
    sa_user = User(
        email=f"sa_{db_session.query(User).count()}@security.test",
        password_hash=get_password_hash("AdminPass123!"),
        full_name="Super Admin Person",
        is_active=True,
    )
    db_session.add(sa_user)
    db_session.commit()
    db_session.refresh(sa_user)

    ur = UserRole(user_id=sa_user.id, role_id=super_role.id)
    db_session.add(ur)
    db_session.commit()

    # Dynamic standard user (the one who attempts the destructive query)
    user_person = User(
        email=f"user_{db_session.query(User).count()}@company.test",
        password_hash=get_password_hash("UserPass123!"),
        full_name="Standard User Person",
        is_active=True,
    )
    db_session.add(user_person)
    db_session.commit()
    db_session.refresh(user_person)

    # Trigger violation notification creation
    created_notes = create_security_violation_notifications(
        db=db_session,
        offender_user_id=user_person.id,
        offender_name=user_person.full_name,
        offender_email=user_person.email,
        company_id=None,
        violation_type="DDL_DROP",
        reason="Prohibited DROP statement intercepted.",
        natural_language="Drop all employee records",
        attempted_sql="DROP TABLE employees;",
        source="Analytics MCP Tool",
        timestamp=datetime.utcnow().isoformat(),
    )

    assert len(created_notes) >= 2

    # Check notification for the offending user
    user_note = (
        db_session.query(Notification)
        .filter(Notification.user_id == user_person.id)
        .first()
    )
    assert user_note is not None
    assert user_note.type == "security_warning"
    assert "Security Guardrail Warning" in user_note.title
    assert "DROP TABLE employees;" in user_note.data["attempted_sql"]

    # Check notification for the SuperAdmin
    sa_note = (
        db_session.query(Notification)
        .filter(Notification.user_id == sa_user.id)
        .first()
    )
    assert sa_note is not None
    assert sa_note.type == "security_alert"
    assert "Security Alert" in sa_note.title
    assert user_person.full_name in sa_note.message
    assert sa_note.data["violation_type"] == "DDL_DROP"


def test_list_notifications_and_unread_filtering(db_session):
    test_user = User(
        email=f"list_user_{db_session.query(User).count()}@test.com",
        password_hash=get_password_hash("Pass123!"),
        full_name="List Test User",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    # Add 3 notifications, 1 read, 2 unread
    n1 = Notification(
        user_id=test_user.id,
        title="Alert 1",
        message="Message 1",
        type="security_alert",
        severity="critical",
        is_read=False,
    )
    n2 = Notification(
        user_id=test_user.id,
        title="Alert 2",
        message="Message 2",
        type="security_warning",
        severity="warning",
        is_read=False,
    )
    n3 = Notification(
        user_id=test_user.id,
        title="Alert 3",
        message="Message 3",
        type="database_alert",
        severity="info",
        is_read=True,
    )
    db_session.add_all([n1, n2, n3])
    db_session.commit()

    # List all
    all_notes, total, unread_count = list_notifications(
        db=db_session,
        user_id=test_user.id,
        unread_only=False,
    )
    assert total == 3
    assert unread_count == 2
    assert len(all_notes) == 3

    # List unread only
    unread_notes, total_unread, unread_count = list_notifications(
        db=db_session,
        user_id=test_user.id,
        unread_only=True,
    )
    assert len(unread_notes) == 2
    assert unread_count == 2


def test_mark_read_and_delete(db_session):
    test_user = User(
        email=f"mark_user_{db_session.query(User).count()}@test.com",
        password_hash=get_password_hash("Pass123!"),
        full_name="Mark Test User",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    n1 = Notification(
        user_id=test_user.id,
        title="Incident 1",
        message="Msg 1",
        type="security_alert",
        is_read=False,
    )
    n2 = Notification(
        user_id=test_user.id,
        title="Incident 2",
        message="Msg 2",
        type="security_alert",
        is_read=False,
    )
    db_session.add_all([n1, n2])
    db_session.commit()
    db_session.refresh(n1)
    db_session.refresh(n2)

    # Mark single read
    success = mark_notification_read(db_session, notification_id=n1.id, user_id=test_user.id)
    assert success is True
    db_session.refresh(n1)
    assert n1.is_read is True

    # Mark all read
    count = mark_all_read(db_session, user_id=test_user.id)
    assert count >= 1
    db_session.refresh(n2)
    assert n2.is_read is True

    # Delete notification
    deleted = delete_notification(db_session, notification_id=n1.id, user_id=test_user.id)
    assert deleted is True
    assert db_session.query(Notification).filter(Notification.id == n1.id).first() is None


def test_trigger_security_incident_generates_notifications(db_session):
    # Dynamic SuperAdmin
    super_role = Role(name="SuperAdmin", description="System Super Admin", is_system=True)
    db_session.add(super_role)
    db_session.commit()
    db_session.refresh(super_role)

    sa_user = User(
        email=f"incident_sa_{db_session.query(User).count()}@security.test",
        password_hash=get_password_hash("Pass123!"),
        full_name="Incident SA",
        is_active=True,
    )
    db_session.add(sa_user)
    db_session.commit()
    db_session.refresh(sa_user)

    ur = UserRole(user_id=sa_user.id, role_id=super_role.id)
    db_session.add(ur)
    db_session.commit()

    # Dynamic User
    user_person = User(
        email=f"incident_user_{db_session.query(User).count()}@company.test",
        password_hash=get_password_hash("Pass123!"),
        full_name="Violating User",
        is_active=True,
    )
    db_session.add(user_person)
    db_session.commit()
    db_session.refresh(user_person)

    with patch("app.services.security_guard_service.send_security_alert_email") as mock_email:
        mock_email.return_value = True

        alert = trigger_security_incident(
            db=db_session,
            user_id=user_person.id,
            company_id=None,
            natural_language="Please truncate table audit_logs",
            attempted_sql="TRUNCATE TABLE audit_logs;",
            violation_type="DML_TRUNCATE",
            reason="TRUNCATE statements are strictly prohibited.",
            source="API Playground",
        )

        assert alert["is_violation"] is True
        assert alert["superadmin_notified"] is True

        # Verify notifications in db
        notifications = db_session.query(Notification).all()
        assert len(notifications) >= 2
        user_notifications = [n for n in notifications if n.user_id == user_person.id]
        sa_notifications = [n for n in notifications if n.user_id == sa_user.id]

        assert len(user_notifications) >= 1
        assert "TRUNCATE TABLE audit_logs;" in user_notifications[0].data["attempted_sql"]

        assert len(sa_notifications) >= 1
        assert sa_notifications[0].data["violation_type"] == "DML_TRUNCATE"
