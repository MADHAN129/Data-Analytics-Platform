from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.audit_service import create_audit_log
from app.config import settings


def register_user(db: Session, data: RegisterRequest, ip_address: str = None):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign default Viewer role
    from app.models.role import Role
    from app.models.user import UserRole

    viewer_role = db.query(Role).filter(Role.name == "Viewer").first()
    if viewer_role:
        ur = UserRole(user_id=user.id, role_id=viewer_role.id)
        db.add(ur)
        db.commit()

    create_audit_log(
        db, user.id, "register", "auth", str(user.id),
        {"email": user.email}, ip_address=ip_address,
    )

    return build_token_response(db, user)


def login_user(db: Session, data: LoginRequest, ip_address: str = None):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        create_audit_log(
            db, user.id if user else 0, "login", "auth", None,
            {"email": data.email, "ip": ip_address}, "failure", ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    create_audit_log(
        db, user.id, "login", "auth", str(user.id),
        {"email": user.email}, ip_address=ip_address,
    )

    return build_token_response(db, user)


def refresh_token(db: Session, token: str):
    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return build_token_response(db, user)


def change_password(db: Session, user_id: int, current_password: str, new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    user.password_hash = get_password_hash(new_password)
    db.commit()

    create_audit_log(db, user_id, "change_password", "auth", str(user_id))


def build_token_response(db: Session, user: User):
    from app.schemas.user import UserResponse, RoleInUser

    # Get user roles
    from app.models.user import UserRole
    from app.models.role import Role

    user_roles = (
        db.query(Role)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )

    roles = [
        RoleInUser(
            id=r.id, name=r.name, description=r.description,
            is_system=r.is_system, created_at=r.created_at, updated_at=r.updated_at,
        )
        for r in user_roles
    ]

    user_data = UserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        phone=user.phone, avatar_url=user.avatar_url,
        auth_provider=user.auth_provider, is_active=user.is_active,
        mfa_enabled=user.mfa_enabled, roles=roles,
        created_at=user.created_at, updated_at=user.updated_at,
    )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_data,
    }
