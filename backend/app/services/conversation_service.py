from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.conversation import Conversation, ConversationMessage
from app.schemas.conversation import (
    ConversationResponse,
    ConversationMessageResponse,
    CreateConversationRequest,
    UpdateConversationRequest,
    SendMessageRequest,
)
from app.services.llm_service import llm_service
from app.services.connection_service import get_connector
from app.services.query_service import _serialize_rows
from app.api.deps import user_has_permission_by_id
from app.config import settings


def list_conversations(
    db: Session,
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    company_id: Optional[int] = None,
) -> tuple[list[ConversationResponse], int]:
    query = db.query(Conversation)
    if company_id is not None:
        query = query.filter((Conversation.company_id == company_id) | (Conversation.user_id == user_id))
    else:
        query = query.filter(Conversation.user_id == user_id)

    total = query.count()
    offset = (page - 1) * per_page
    items = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(per_page).all()
    return [ConversationResponse.model_validate(c) for c in items], total


def create_conversation(
    db: Session,
    data: CreateConversationRequest,
    user_id: int,
) -> ConversationResponse:
    from app.models.user import User
    creator = db.query(User).filter(User.id == user_id).first()
    company_id = creator.company_id if creator else None

    title = data.title or "New Conversation"
    conv = Conversation(
        user_id=user_id,
        company_id=company_id,
        title=title,
        database_id=data.database_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationResponse.model_validate(conv)


def get_conversation(db: Session, conversation_id: int, user_id: int) -> ConversationResponse:
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)


def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return True


def update_conversation(
    db: Session,
    conversation_id: int,
    data: UpdateConversationRequest,
    user_id: int,
) -> ConversationResponse:
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if data.title is not None:
        conv.title = data.title
    if data.database_id is not None:
        conv.database_id = data.database_id
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conv)
    return ConversationResponse.model_validate(conv)


def get_messages(
    db: Session,
    conversation_id: int,
    user_id: int,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[ConversationMessageResponse], int]:
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    query = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id,
    )
    total = query.count()
    offset = (page - 1) * per_page
    items = query.order_by(ConversationMessage.created_at.asc()).offset(offset).limit(per_page).all()

    from app.schemas.conversation import ClarificationOption

    responses = []
    for m in items:
        resp = ConversationMessageResponse.model_validate(m)
        if m.tool_results and isinstance(m.tool_results, dict):
            if "results" in m.tool_results:
                resp.results = m.tool_results["results"]
            elif "columns" in m.tool_results:
                resp.results = m.tool_results
            if "generated_sql" in m.tool_results:
                resp.generated_sql = m.tool_results["generated_sql"]
            if "quick_options" in m.tool_results:
                resp.quick_options = m.tool_results["quick_options"]
            if "error" in m.tool_results:
                resp.error_message = m.tool_results["error"]

        if m.tool_calls and isinstance(m.tool_calls, list):
            for tc in m.tool_calls:
                if isinstance(tc, dict) and tc.get("type") == "clarification":
                    resp.clarification_options = [
                        ClarificationOption(**opt) for opt in tc.get("options", [])
                    ]
        responses.append(resp)

    return responses, total


def send_message(
    db: Session,
    conversation_id: int,
    data: SendMessageRequest,
    user_id: int,
) -> ConversationMessageResponse:
    from app.models.user import User
    from app.schemas.conversation import ClarificationOption

    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_msg = ConversationMessage(
        conversation_id=conversation_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    schema_context = ""
    db_conn = None

    if conv.database_id:
        from app.models.connection import DatabaseConnection

        user_obj = db.query(User).filter(User.id == user_id).first()
        company_id = user_obj.company_id if user_obj else None

        query = db.query(DatabaseConnection).filter(DatabaseConnection.id == conv.database_id)
        if company_id is not None:
            query = query.filter((DatabaseConnection.company_id == company_id) | (DatabaseConnection.created_by == user_id))
        elif not user_has_permission_by_id(db, user_id, "access.manage"):
            query = query.filter(DatabaseConnection.created_by == user_id)
        db_conn = query.first()
        if db_conn:
            try:
                connector = get_connector(db_conn)
                schema = connector.get_schema()
                lines = []
                for table in schema.tables:
                    cols = ", ".join(f"{c.name} ({c.data_type})" for c in table.columns[:25])
                    lines.append(f"Table: {table.name} [{cols}]")
                schema_context = "\n".join(lines[:30])
            except Exception:
                pass

    dialect = db_conn.connection_type if db_conn else "postgresql"

    # Phase 1 & 2: Agentic Schema Exploration & Intent Clarification
    intent_analysis = llm_service.analyze_intent_and_clarify(data.content, schema_context, dialect)

    if intent_analysis.get("status") in ("clarify", "unrelated") and intent_analysis.get("options"):
        clarification_opts = [
            ClarificationOption(**opt) for opt in intent_analysis.get("options", [])
        ]
        clarification_msg_content = intent_analysis.get("message", "How would you like to view this data?")

        assistant_msg = ConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=clarification_msg_content,
            tool_calls=[{"type": "clarification", "options": intent_analysis.get("options", [])}],
            tool_results=None,
            tokens_used=llm_service._estimate_tokens(data.content, clarification_msg_content),
            model_used=llm_service.model_name,
        )
        db.add(assistant_msg)
        conv.message_count = (conv.message_count or 0) + 2
        conv.updated_at = datetime.now(timezone.utc)
        if conv.message_count <= 2:
            conv.title = data.content[:80]

        db.commit()
        db.refresh(assistant_msg)

        resp = ConversationMessageResponse.model_validate(assistant_msg)
        resp.clarification_options = clarification_opts
        return resp

    # Phase 3: Direct SQL Generation, Execution & Self-Healing
    sql, explanation, tokens_used = llm_service.generate_sql(
        data.content, schema_context, dialect,
    )

    generated_sql = sql
    results = None
    error_message = None

    if db_conn and sql and not sql.startswith("ERROR:") and sql not in ("UNRELATED", "AMBIGUOUS"):
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                connector = get_connector(db_conn)
                import time
                start = time.time()
                raw_results = connector.execute_query(sql)
                elapsed = int((time.time() - start) * 1000)
                columns = raw_results.get("columns", [])
                rows = _serialize_rows(raw_results.get("rows", []))
                results = {
                    "columns": columns,
                    "rows": rows[:1000],
                    "row_count": len(rows),
                    "execution_time_ms": elapsed,
                }
                error_message = None
                break
            except Exception as e:
                error_message = str(e)
                if attempt < max_retries:
                    sql, explanation, retry_tokens = llm_service.fix_sql(
                        data.content, sql, error_message, schema_context, dialect,
                    )
                    generated_sql = sql
                    tokens_used = (tokens_used or 0) + (retry_tokens or 0)
                    if sql.startswith("ERROR:"):
                        break

    # Phase 4: Rich Multi-Modal Reporting (Summary, Labels, Data, Quick Options)
    quick_options = []
    if results and results.get("rows"):
        try:
            summary = llm_service.synthesize_data_summary(
                data.content, sql, results.get("columns", []), results.get("rows", [])
            )
            response_content = f"{summary}\n\n```sql\n{sql}\n```"
        except Exception:
            response_content = f"{explanation}\n\n```sql\n{sql}\n```"

        quick_options = llm_service.generate_follow_up_suggestions(
            data.content, sql, results.get("columns", []), results.get("rows", [])
        )
    else:
        is_dummy_sql = sql.strip().rstrip(";") in ("SELECT 1", "SELECT 1 WHERE 1=0", "UNRELATED", "AMBIGUOUS")
        if is_dummy_sql:
            response_content = explanation
        else:
            response_content = f"{explanation}\n\n```sql\n{sql}\n```"
            if error_message:
                response_content += f"\n\n*Error: {error_message}*"

    stored_tool_results = {
        "results": results,
        "generated_sql": generated_sql,
        "quick_options": quick_options,
        "error": error_message,
    }

    assistant_msg = ConversationMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=response_content,
        tool_calls=None,
        tool_results=stored_tool_results,
        tokens_used=tokens_used,
        model_used=llm_service.model_name,
    )
    db.add(assistant_msg)
    conv.message_count = (conv.message_count or 0) + 2
    conv.total_tokens = (conv.total_tokens or 0) + (tokens_used or 0)
    conv.updated_at = datetime.now(timezone.utc)

    if conv.message_count <= 2:
        conv.title = data.content[:80]

    db.commit()
    db.refresh(assistant_msg)

    resp = ConversationMessageResponse.model_validate(assistant_msg)
    resp.generated_sql = generated_sql
    resp.results = results
    resp.quick_options = quick_options
    resp.error_message = error_message
    return resp
