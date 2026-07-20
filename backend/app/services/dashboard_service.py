from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.dashboard import Dashboard, DashboardWidget
from app.models.query import Query
from app.schemas.dashboard import (
    DashboardCreateRequest,
    DashboardUpdateRequest,
    LayoutUpdateRequest,
)
from app.models.template import QueryTemplate

import threading


def _run_with_timeout(func, seconds: int):
    """Run func in a thread and return its result, or None on timeout/error.

    Used to bound database network calls (schema fetch, query execution) and
    LLM calls so an unreachable database or a slow model cannot hang or crash
    an auto-generation request. Any failure yields None so the caller can
    degrade gracefully instead of aborting the whole dashboard generation.
    """
    result: dict = {}

    def _target():
        try:
            result["value"] = func()
        except Exception:  # noqa: BLE001
            result["error"] = True

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive() or "error" in result:
        return None
    return result.get("value")


def list_dashboards(
    db: Session, skip: int = 0, limit: int = 50
) -> tuple[list[Dashboard], int]:
    total = db.query(func.count(Dashboard.id)).scalar() or 0
    dashboards = (
        db.query(Dashboard)
        .order_by(Dashboard.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return dashboards, total


def get_dashboard(db: Session, dashboard_id: int) -> Dashboard | None:
    return db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()


def create_dashboard(
    db: Session, data: DashboardCreateRequest, user_id: int
) -> Dashboard:
    dash = Dashboard(
        user_id=user_id,
        title=data.title,
        description=data.description,
        is_template=data.is_template,
    )
    db.add(dash)
    db.commit()
    db.refresh(dash)
    return dash


def update_dashboard(
    db: Session, dash: Dashboard, data: DashboardUpdateRequest
) -> Dashboard:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dash, key, value)
    db.commit()
    db.refresh(dash)
    return dash


def delete_dashboard(db: Session, dash: Dashboard) -> None:
    db.query(DashboardWidget).filter(
        DashboardWidget.dashboard_id == dash.id
    ).delete()
    db.delete(dash)
    db.commit()


def add_widget(
    db: Session,
    dashboard_id: int,
    widget_type: str,
    title: str,
    position_x: int = 0,
    position_y: int = 0,
    width: int = 6,
    height: int = 4,
    query_id: int | None = None,
    config: dict | None = None,
) -> DashboardWidget:
    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        widget_type=widget_type,
        title=title,
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
        query_id=query_id,
        config=config or {},
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


def update_widget(
    db: Session, widget: DashboardWidget, **updates
) -> DashboardWidget:
    for key, value in updates.items():
        setattr(widget, key, value)
    db.commit()
    db.refresh(widget)
    return widget


def delete_widget(db: Session, widget: DashboardWidget) -> None:
    db.delete(widget)
    db.commit()


def update_layout(
    db: Session, dash: Dashboard, data: LayoutUpdateRequest
) -> list[DashboardWidget]:
    for item in data.widgets:
        db.query(DashboardWidget).filter(
            DashboardWidget.id == item.id,
            DashboardWidget.dashboard_id == dash.id,
        ).update(
            {
                "position_x": item.position_x,
                "position_y": item.position_y,
                "width": item.width,
                "height": item.height,
            }
        )
    db.commit()
    return (
        db.query(DashboardWidget)
        .filter(DashboardWidget.dashboard_id == dash.id)
        .order_by(DashboardWidget.position_y, DashboardWidget.position_x)
        .all()
    )


def auto_generate_from_query(
    db: Session,
    database_id: int,
    query_text: str | None = None,
    template_id: int | None = None,
    user_id: int | None = None,
) -> Dashboard:
    from app.services.connection_service import get_database, get_connector
    from app.services.query_service import _serialize_rows
    from app.services.llm_service import llm_service

    db_conn = get_database(db, database_id)
    if not db_conn:
        raise ValueError("Database connection not found")

    # Build schema context so the LLM can generate valid SQL. Bound any DB
    # network call with a timeout so an unreachable database can't hang the
    # whole auto-generation request.
    def _build_schema():
        connector = get_connector(db_conn)
        schema = connector.get_schema()
        lines = [
            f"Table: {t.name} [{', '.join(f'{c.name} ({c.data_type})' for c in t.columns[:25])}]"
            for t in schema.tables[:50]
        ]
        return "\n".join(lines)

    schema_context = _run_with_timeout(_build_schema, 12) or "Schema unavailable"

    # 1) Decompose the user's request into a set of widget specs.
    specs = _plan_widgets(query_text, schema_context)

    # 2) Derive a readable dashboard title from the request.
    if query_text and query_text.strip():
        title = query_text.strip()[:60].capitalize()
        if not title.endswith(("?", ".", "!")):
            title += "…" if len(query_text.strip()) > 60 else ""
    else:
        title = "Auto-generated Dashboard"

    dash = Dashboard(
        user_id=user_id or 0,
        title=title,
        description="Automatically generated dashboard based on your request."
        if query_text else "Automatically generated dashboard based on query analysis",
        auto_generated=True,
    )
    db.add(dash)
    db.flush()

    # 3) For each spec: generate SQL, execute read-only, and create a query + widget.
    col = 0
    row = 0
    for spec in specs:
        natural_language = spec["question"]
        try:
            generated = _run_with_timeout(
                lambda: llm_service.generate_sql(
                    natural_language, schema_context, db_conn.connection_type,
                ),
                12,
            )
        except Exception:
            generated = None
        if not generated:
            sql = _heuristic_sql(natural_language, schema_context)
            explanation = "Generated from your request (LLM unavailable)."
        else:
            sql, explanation, _ = generated
        if not sql or sql.strip() in (";", ""):
            sql = "SELECT 1 WHERE 1=0"
            explanation = "Could not generate a valid SQL query."

        status = "completed"
        result_columns = None
        result_rows = None
        row_count = 0
        error_message = None
        try:
            def _run_query():
                connector = get_connector(db_conn)
                return connector.execute_query(sql)

            raw = _run_with_timeout(_run_query, 12)
            if raw is None:
                raise TimeoutError("Database query timed out")
            columns = raw.get("columns", [])
            rows = _serialize_rows(raw.get("rows", []))
            result_columns = columns
            result_rows = rows[:1000]
            row_count = len(rows)
        except Exception as e:
            status = "failed"
            error_message = str(e)[:300]

        query = Query(
            user_id=dash.user_id,
            database_id=database_id,
            natural_language=natural_language,
            generated_sql=sql,
            explanation=explanation,
            status=status,
            result_columns=result_columns,
            result_rows=result_rows,
            row_count=row_count,
            error_message=error_message,
        )
        db.add(query)
        db.flush()

        add_widget(
            db,
            dashboard_id=dash.id,
            widget_type=spec["chart_type"],
            title=spec["title"],
            position_x=col * 6,
            position_y=row * 4,
            width=6,
            height=4,
            query_id=query.id,
            config={
                "auto_generated": True,
                "natural_language": natural_language,
                "database_id": database_id,
                "sql": sql,
            },
        )
        col = 1 - col
        if col == 0:
            row += 1

    db.commit()
    db.refresh(dash)
    return dash


def _plan_widgets(query_text: str | None, schema_context: str) -> list[dict]:
    """Turn a free-form request into a list of widget specs.

    Each spec: {"title", "question", "chart_type"}. Prefers the LLM to split the
    request into multiple charts; falls back to a heuristic split when the LLM
    is unavailable (mock mode) or returns nothing usable.
    """
    import json
    import re

    default = {
        "title": "Query Results",
        "question": query_text or "Show me an overview of the data",
        "chart_type": "table",
    }

    if not query_text or not query_text.strip():
        return [default]

    from app.services.llm_service import llm_service

    prompt = (
        "You are a BI dashboard assistant. Given a user's request, break it into "
        "separate visualization widgets. For each widget return a JSON object with: "
        "title (short), question (a single natural-language query), and chart_type "
        "(one of: bar_chart, line_chart, pie_chart, area_chart, kpi, table).\n"
        "Respond with a JSON array ONLY, no markdown.\n\n"
        f"User request: {query_text}\n"
        f"Database schema:\n{schema_context[:2000]}"
    )
    raw = None
    if not llm_service.use_mock:
        try:
            raw = llm_service._call_vllm(
                [
                    {"role": "system", "content": "You output strictly JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
        except Exception:
            raw = None

    if raw:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and parsed:
                specs = []
                for item in parsed[:6]:
                    if not isinstance(item, dict):
                        continue
                    q = (item.get("question") or item.get("title") or "").strip()
                    if not q:
                        continue
                    specs.append({
                        "title": item.get("title") or q[:40],
                        "question": q,
                        "chart_type": _normalize_chart_type(item.get("chart_type")),
                    })
                if specs:
                    return specs
        except (json.JSONDecodeError, TypeError):
            pass

    # Heuristic fallback: split the request into clauses and map obvious
    # keywords to chart types. Guarantees multiple widgets even without the LLM.
    clauses = re.split(r"(?i)\b(and|,|;|then|\.|\bl\.?\b)", query_text)
    clauses = [c.strip(" .,;") for c in clauses if c and c.strip(" .,") and len(c.strip()) > 3]
    if not clauses:
        clauses = [query_text.strip()]

    # Drop clauses that are meta-instructions rather than data requests
    # (e.g. "i need it in the three different graphs", "please show this").
    instruction_markers = (
        "i need", "i want", "please", "in the", "different", "graph", "chart",
        "dashboard", "visualization", "widgets", "separate", "display",
    )
    data_clauses = []
    for c in clauses:
        low = c.lower()
        if any(m in low for m in instruction_markers) and not any(
            k in low for k in ("per ", "total", "count", "sum", "amount", "number of", "no of", "sales", "users", "by ")
        ):
            continue
        data_clauses.append(c)

    specs = []
    for clause in data_clauses[:6]:
        chart = _infer_chart_type(clause)
        specs.append({
            "title": clause[:40].capitalize(),
            "question": clause.strip(),
            "chart_type": chart,
        })
    if not specs:
        specs = [{
            "title": query_text[:40].capitalize(),
            "question": query_text.strip(),
            "chart_type": "table",
        }]
    return specs


def _normalize_chart_type(value: str | None) -> str:
    allowed = {"bar_chart", "line_chart", "pie_chart", "area_chart", "kpi", "table"}
    if value in allowed:
        return value
    return _infer_chart_type(value or "")


def _infer_chart_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["per day", "over time", "trend", "daily", "monthly", "timeline", "by date"]):
        return "line_chart"
    if any(k in t for k in ["distribution", "share", "percentage", "breakdown", "by", "per ", "per role", "per category"]):
        return "bar_chart"
    if any(k in t for k in ["total", "sum", "count", "number of", "no of", "amount", "revenue"]):
        return "kpi"
    return "table"


def _heuristic_sql(question: str, schema_context: str) -> str:
    """Best-effort SQL when the LLM is unavailable or times out.

    Picks the most likely single table from the schema and builds a GROUP BY
    aggregation matching the request. Always read-only.
    """
    import re

    tables = re.findall(r"Table:\s*(\w+)", schema_context)
    table = tables[0] if tables else "data"

    q = question.lower()
    cols = re.findall(r"\(([^)]+)\)", schema_context)
    all_cols: list[str] = []
    for group in cols:
        for c in group.split(","):
            name = c.strip().split(" ")[0]
            if name:
                all_cols.append(name)

    date_col = next((c for c in all_cols if any(k in c for k in ("date", "time", "created", "at"))), None)
    amount_col = next((c for c in all_cols if any(k in c for k in ("amount", "price", "total", "revenue", "value", "sum"))), None)
    cat_col = next((c for c in all_cols if any(k in c for k in ("role", "status", "category", "type", "name"))), None)

    if any(k in q for k in ["per day", "daily", "over time", "trend", "by date", "timeline"]) and date_col:
        return f"SELECT {date_col}, COUNT(*) AS count FROM {table} GROUP BY {date_col} ORDER BY {date_col}"
    if any(k in q for k in ["total", "sum", "amount", "revenue"]) and amount_col:
        return f"SELECT SUM({amount_col}) AS total FROM {table}"
    if any(k in q for k in ["per role", "per category", "per status", "per type", "breakdown", "distribution"]) and cat_col:
        return f"SELECT {cat_col}, COUNT(*) AS count FROM {table} GROUP BY {cat_col} ORDER BY count DESC"
    if "count" in q or "number of" in q or "no of" in q:
        return f"SELECT COUNT(*) AS count FROM {table}"
    return f"SELECT * FROM {table} LIMIT 100"

