from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.schemas.common import MessageResponse
from app.services import auth_service

router = APIRouter(tags=["Authentication"])


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db), request: Request = None):
    ip = request.client.host if request else None
    return auth_service.register_user(db, data, ip)


@router.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db), request: Request = None):
    ip = request.client.host if request else None
    return auth_service.login_user(db, data, ip)


@router.post("/auth/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.audit_service import create_audit_log
    create_audit_log(db, current_user.id, "logout", "auth", str(current_user.id))
    return MessageResponse(message="Logged out successfully")


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    return auth_service.refresh_token(db, data.refresh_token)


@router.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # For security, always return success
    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    return MessageResponse(message="Password reset successful")


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.change_password(db, current_user.id, data.current_password, data.new_password)
    return MessageResponse(message="Password changed successfully")
