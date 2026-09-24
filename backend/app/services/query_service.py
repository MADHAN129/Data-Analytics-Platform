import json
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.connection import DatabaseConnection
from app.models.query import Query
from app.models.conversation import Conversation
from app.models.template import QueryTemplate
from app.schemas.query import (
    QueryRequest, SQLExecutionRequest, FollowUpRequest,
    QueryResponse, QueryResult, VisualizationSuggestion,
    ExplainResponse, OptimizeResponse, OptimizeSuggestion,
    VisualizeResponse,
)
from app.services.connection_service import get_connector, get_database
from app.services.llm_service import llm_service
from app.utils.error_messages import friendly_error


def _make_json_safe(val):
    if isinstance(val, (datetime,)):
        return val.isoformat()
    if isinstance(val, (bytes, bytearray)):
        return val.hex()
    try:
        json.dumps(val)
        return val
    except (TypeError, ValueError):
        return str(val)


def _serialize_rows(rows):
    return [[_make_json_safe(cell) for cell in row] for row in rows]


def _db_conn_to_query_response(q: Query) -> QueryResponse:
    results = None
    if q.result_columns and q.result_rows:
        results = QueryResult(
            columns=q.result_columns,
            rows=q.result_rows,
            row_count=q.row_count,
            execution_time_ms=q.execution_time_ms,
        )
    return QueryResponse(
        id=q.id,
        status=q.status,
        natural_language=q.natural_language,
        generated_sql=q.generated_sql,
        explanation=q.explanation,
        results=results,
        tokens_used=q.tokens_used,
        conversation_id=q.conversation_id,
        parent_query_id=q.parent_query_id,
        error_message=q.error_message,
        created_at=q.created_at,
    )


def _get_schema_context(db_conn: DatabaseConnection) -> str:
    try:
        connector = get_connector(db_conn)
        schema = connector.get_schema()
        lines = [
            f"DATABASE TYPE: {db_conn.connection_type.upper()} ({db_conn.name})",
            f"SCHEMA / OWNER: {db_conn.schema_name or 'Default'}",
            "",
            "AVAILABLE TABLES & STRUCTURE:"
        ]
        for table in schema.tables:
            col_lines = []
            for c in table.columns:
                pk_tag = " [PRIMARY KEY]" if c.is_primary_key else ""
                col_lines.append(f"  - {c.name} ({c.data_type}{pk_tag})")
            lines.append(f"Table: {table.name}")
            lines.extend(col_lines)
            lines.append("")

        if any(t.name in ("EMPLOYEES", "DEPARTMENTS", "PROJECTS", "SALES_RECORDS") for t in schema.tables):
            lines.append("RELATIONSHIPS:")
            lines.append("- EMPLOYEES.DEPARTMENT_ID relates to DEPARTMENTS.DEPARTMENT_ID")
            lines.append("- PROJECTS.DEPARTMENT_ID relates to DEPARTMENTS.DEPARTMENT_ID")
            lines.append("- SALES_RECORDS.SALES_REP_ID relates to EMPLOYEES.EMPLOYEE_ID")
        return "\n".join(lines)
    except Exception:
        return f"Database Type: {db_conn.connection_type}. Schema unavailable."


def execute_natural_language_query(
    db: Session,
    data: QueryRequest,
    user_id: int,
) -> QueryResponse:
    db_conn = get_database(db, data.database_id)
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database not found")

    schema_context = _get_schema_context(db_conn)
    sql, explanation, tokens_used = llm_service.generate_sql(
        data.natural_language, schema_context, db_conn.connection_type,
    )

    if not sql or sql.strip() in (";", ""):
        if db_conn.connection_type == "oracle":
            sql = "SELECT 1 FROM DUAL WHERE 1=0;"
        elif db_conn.connection_type == "mongodb":
            sql = "{}"
        else:
            sql = "SELECT 1 WHERE 1=0;"
        explanation = "Could not generate a valid SQL query from your question. Try rephrasing or being more specific."

    query_record = Query(
        user_id=user_id,
        database_id=data.database_id,
        natural_language=data.natural_language,
        generated_sql=sql,
        explanation=explanation,
        status="executing",
        tokens_used=tokens_used,
        conversation_id=data.conversation_id,
    )
    db.add(query_record)
    db.commit()
    db.refresh(query_record)

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            connector = get_connector(db_conn)
            start = time.time()

            raw_results = connector.execute_query(sql)
            elapsed = int((time.time() - start) * 1000)

            columns = raw_results.get("columns", [])
            rows = _serialize_rows(raw_results.get("rows", []))
            row_count = len(rows)

            query_record.status = "completed"
            query_record.result_columns = columns
            query_record.result_rows = rows[:1000]
            query_record.row_count = row_count
            query_record.execution_time_ms = elapsed
            break
        except Exception as e:
            error_msg = friendly_error(str(e))
            if attempt < max_retries:
                sql, explanation, retry_tokens = llm_service.fix_sql(
                    data.natural_language, sql, error_msg, schema_context, db_conn.connection_type,
                )
                query_record.generated_sql = sql
                query_record.explanation = explanation
                query_record.tokens_used = (query_record.tokens_used or 0) + (retry_tokens or 0)
                db.commit()
                if sql.startswith("ERROR:"):
                    break
            else:
                query_record.status = "failed"
                query_record.error_message = error_msg
                db.commit()
                db.refresh(query_record)
                return _db_conn_to_query_response(query_record)

    db.commit()
    db.refresh(query_record)
    result = _db_conn_to_query_response(query_record)
    result.suggested_visualizations = _get_visualization_suggestions(query_record)
    return result


def execute_raw_sql(
    db: Session,
    data: SQLExecutionRequest,
    user_id: int,
) -> QueryResponse:
    db_conn = get_database(db, data.database_id)
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database not found")

    query_record = Query(
        user_id=user_id,
        database_id=data.database_id,
        natural_language=f"Execute raw SQL: {data.sql[:100]}",
        generated_sql=data.sql,
        status="executing",
    )
    db.add(query_record)
    db.commit()
    db.refresh(query_record)

    try:
        connector = get_connector(db_conn)
        start = time.time()
        raw_results = connector.execute_query(data.sql)
        elapsed = int((time.time() - start) * 1000)

        columns = raw_results.get("columns", [])
        rows = _serialize_rows(raw_results.get("rows", []))
        row_count = len(rows)

        query_record.status = "completed"
        query_record.result_columns = columns
        query_record.result_rows = rows[:1000]
        query_record.row_count = row_count
        query_record.execution_time_ms = elapsed

    except Exception as e:
        error_msg = friendly_error(str(e))
        query_record.status = "failed"
        query_record.error_message = error_msg
        db.commit()
        db.refresh(query_record)
        return _db_conn_to_query_response(query_record)

    db.commit()
    db.refresh(query_record)
    return _db_conn_to_query_response(query_record)


def follow_up_query(
    db: Session,
    query_id: int,
    data: FollowUpRequest,
    user_id: int,
) -> QueryResponse:
    parent = db.query(Query).filter(Query.id == query_id, Query.user_id == user_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Query not found")

    full_context = f"Previous question: {parent.natural_language}\nPrevious SQL: {parent.generated_sql}\nFollow-up: {data.natural_language}"

    follow_up_data = QueryRequest(
        database_id=parent.database_id,
        natural_language=full_context,
        conversation_id=parent.conversation_id,
    )
    result = execute_natural_language_query(db, follow_up_data, user_id)
    result.parent_query_id = query_id
    return result


def list_queries(
    db: Session,
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    database_id: Optional[int] = None,
    status: Optional[str] = None,
) -> tuple[list[QueryResponse], int, int]:
    query = db.query(Query).filter(Query.user_id == user_id)

    if database_id:
        query = query.filter(Query.database_id == database_id)
    if status:
        query = query.filter(Query.status == status)

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    items = query.order_by(Query.created_at.desc()).offset(offset).limit(per_page).all()

    responses = []
    for q in items:
        r = _db_conn_to_query_response(q)
        r.suggested_visualizations = _get_visualization_suggestions(q)
        responses.append(r)

    return responses, total, pages


def get_query(db: Session, query_id: int, user_id: int) -> QueryResponse:
    q = db.query(Query).filter(Query.id == query_id, Query.user_id == user_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    result = _db_conn_to_query_response(q)
    result.suggested_visualizations = _get_visualization_suggestions(q)
    return result


def cancel_query(db: Session, query_id: int, user_id: int) -> bool:
    q = db.query(Query).filter(Query.id == query_id, Query.user_id == user_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    if q.status in ("pending", "executing"):
        q.status = "cancelled"
        db.commit()
        return True
    return False


def explain_query(db: Session, query_id: int, user_id: int) -> ExplainResponse:
    q = db.query(Query).filter(Query.id == query_id, Query.user_id == user_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    sql = q.generated_sql or ""
    explanation = q.explanation or llm_service.explain_sql(sql, q.natural_language)
    return ExplainResponse(explanation=explanation, generated_sql=sql)


def optimize_query(db: Session, query_id: int, user_id: int) -> OptimizeResponse:
    q = db.query(Query).filter(Query.id == query_id, Query.user_id == user_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    sql = q.generated_sql or ""
    suggestions = llm_service.optimize_query(sql)
    return OptimizeResponse(
        suggestions=[OptimizeSuggestion(**s) for s in suggestions],
    )


def visualize_query(db: Session, query_id: int, user_id: int) -> VisualizeResponse:
    q = db.query(Query).filter(Query.id == query_id, Query.user_id == user_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    columns = q.result_columns or []
    suggestions = llm_service.suggest_visualizations(columns)
    return VisualizeResponse(
        visualizations=[VisualizationSuggestion(**s) for s in suggestions],
    )


def get_suggestions(db: Session, user_id: int, q: str) -> list[str]:
    like = f"{q}%"
    queries = db.query(Query.natural_language).filter(
        Query.user_id == user_id,
        Query.natural_language.ilike(like),
        Query.status == "completed",
    ).distinct().limit(8).all()
    results = [row[0] for row in queries]
    template_q = db.query(QueryTemplate.natural_language).filter(
        QueryTemplate.user_id == user_id,
        QueryTemplate.natural_language.ilike(like),
    ).limit(3).all()
    results.extend(row[0] for row in template_q if row[0] not in results)
    return results[:10]


def _get_visualization_suggestions(q: Query) -> list[VisualizationSuggestion]:
    columns = q.result_columns or []
    rows = q.result_rows or []
    if not columns:
        return []
    suggestions = llm_service.suggest_visualizations(columns, rows=rows, natural_language=q.natural_language or "")
    return [VisualizationSuggestion(**s) for s in suggestions]
