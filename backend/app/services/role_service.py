from typing import Optional, List

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.role import Role, RolePermission
from app.models.permission import Permission
from app.models.user import User, UserRole
from app.schemas.role import RoleResponse, CreateRoleRequest, UpdateRoleRequest
from app.schemas.permission import PermissionResponse
from app.services.audit_service import create_audit_log


def get_role_response(db: Session, role: Role, company_id: Optional[int] = None) -> RoleResponse:
    perms = (
        db.query(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .filter(RolePermission.role_id == role.id)
        .all()
    )
    user_count_query = (
        db.query(UserRole)
        .join(User, User.id == UserRole.user_id)
        .filter(UserRole.role_id == role.id)
    )
    if company_id is not None:
        user_count_query = user_count_query.filter(User.company_id == company_id)
    user_count = user_count_query.count()

    permissions = [
        PermissionResponse(
            id=p.id, name=p.name, resource=p.resource,
            action=p.action, description=p.description, created_at=p.created_at,
        )
        for p in perms
    ]

    return RoleResponse(
        id=role.id, name=role.name, description=role.description,
        is_system=role.is_system, permissions=permissions,
        user_count=user_count, created_at=role.created_at, updated_at=role.updated_at,
    )


def list_roles(db: Session, page: int = 1, per_page: int = 20, company_id: Optional[int] = None):
    total = db.query(Role).count()
    roles = db.query(Role).offset((page - 1) * per_page).limit(per_page).all()
    return [get_role_response(db, r, company_id=company_id) for r in roles], total


def create_role(db: Session, data: CreateRoleRequest, current_user_id: int, company_id: Optional[int] = None) -> RoleResponse:
    from fastapi import HTTPException, status

    existing = db.query(Role).filter(Role.name == data.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")

    role = Role(name=data.name, description=data.description)
    db.add(role)
    db.commit()
    db.refresh(role)

    if data.permission_ids:
        for pid in data.permission_ids:
            db.add(RolePermission(role_id=role.id, permission_id=pid))
        db.commit()

    create_audit_log(db, current_user_id, "role.create", "role", str(role.id),
                     {"name": role.name, "permissions": data.permission_ids})

    return get_role_response(db, role, company_id=company_id)


def update_role(db: Session, role_id: int, data: UpdateRoleRequest, current_user_id: int, company_id: Optional[int] = None) -> RoleResponse:
    from fastapi import HTTPException, status

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description

    if data.permission_ids is not None:
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for pid in data.permission_ids:
            db.add(RolePermission(role_id=role.id, permission_id=pid))

    db.commit()
    db.refresh(role)

    create_audit_log(db, current_user_id, "role.update", "role", str(role_id))

    return get_role_response(db, role, company_id=company_id)


def delete_role(db: Session, role_id: int, current_user_id: int):
    from fastapi import HTTPException, status

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete system role",
        )

    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    db.query(UserRole).filter(UserRole.role_id == role_id).delete()
    db.delete(role)
    db.commit()

    create_audit_log(db, current_user_id, "role.delete", "role", str(role_id))
