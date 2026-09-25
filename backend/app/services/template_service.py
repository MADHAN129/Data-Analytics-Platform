from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.template import QueryTemplate
from app.schemas.template import (
    TemplateCreateRequest, TemplateUpdateRequest, TemplateResponse,
)


def list_templates(
    db: Session,
    user_id: int,
    page: int = 1,
    per_page: int = 50,
    search: str = None,
) -> tuple[list[TemplateResponse], int]:
    query = db.query(QueryTemplate).filter(QueryTemplate.user_id == user_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            QueryTemplate.title.ilike(like) | QueryTemplate.natural_language.ilike(like)
        )
    total = query.count()
    offset = (page - 1) * per_page
    items = query.order_by(QueryTemplate.updated_at.desc()).offset(offset).limit(per_page).all()
    return [TemplateResponse.model_validate(t) for t in items], total


def create_template(
    db: Session,
    data: TemplateCreateRequest,
    user_id: int,
) -> TemplateResponse:
    tpl = QueryTemplate(
        user_id=user_id,
        title=data.title,
        description=data.description,
        natural_language=data.natural_language,
        generated_sql=data.generated_sql,
        database_id=data.database_id,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return TemplateResponse.model_validate(tpl)


def get_template(db: Session, template_id: int, user_id: int) -> TemplateResponse:
    tpl = db.query(QueryTemplate).filter(
        QueryTemplate.id == template_id,
        QueryTemplate.user_id == user_id,
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse.model_validate(tpl)


def update_template(
    db: Session,
    template_id: int,
    data: TemplateUpdateRequest,
    user_id: int,
) -> TemplateResponse:
    tpl = db.query(QueryTemplate).filter(
        QueryTemplate.id == template_id,
        QueryTemplate.user_id == user_id,
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if data.title is not None:
        tpl.title = data.title
    if data.description is not None:
        tpl.description = data.description
    if data.natural_language is not None:
        tpl.natural_language = data.natural_language
    if data.generated_sql is not None:
        tpl.generated_sql = data.generated_sql
    db.commit()
    db.refresh(tpl)
    return TemplateResponse.model_validate(tpl)


def delete_template(db: Session, template_id: int, user_id: int) -> bool:
    tpl = db.query(QueryTemplate).filter(
        QueryTemplate.id == template_id,
        QueryTemplate.user_id == user_id,
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tpl)
    db.commit()
    return True
