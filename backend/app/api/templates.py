from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.template import (
    TemplateResponse, TemplateListResponse,
    TemplateCreateRequest, TemplateUpdateRequest,
)
from app.services import template_service
from app.schemas.conversation import MessageResponse

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=TemplateListResponse)
def list_templates(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates, total = template_service.list_templates(db, current_user.id, page, per_page, search)
    return TemplateListResponse(templates=templates, total=total)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    data: TemplateCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return template_service.create_template(db, data, current_user.id)


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return template_service.get_template(db, template_id, current_user.id)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    data: TemplateUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return template_service.update_template(db, template_id, data, current_user.id)


@router.delete("/{template_id}", response_model=MessageResponse)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template_service.delete_template(db, template_id, current_user.id)
    return MessageResponse(message="Template deleted")


@router.post("/{template_id}/instantiate", response_model=TemplateResponse)
def instantiate_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    template = template_service.get_template(db, template_id, current_user.id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

