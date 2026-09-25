import json
import re
import time
import difflib
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.connection import DatabaseConnection
from app.models.query import Query
from app.models.conversation import Conversation
from app.models.template import QueryTemplate
from app.models.user import User
from app.schemas.query import (
    QueryRequest, SQLExecutionRequest, FollowUpRequest,
    QueryResponse, QueryResult, VisualizationSuggestion,
    ExplainResponse, OptimizeResponse, OptimizeSuggestion,
    VisualizeResponse,
)
from app.schemas.conversation import MessageResponse
from app.services.llm_service import llm_service
from app.services.mcp_client import mcp_client
from app.services.connection_service import get_connector, get_database
from app.config import settings
from app.utils.error_messages import friendly_error


def _user_has_manage_permission(db: Session, user_id: int) -> bool:
    try:
        from app.models.user import UserRole
        from app.models.role import RolePermission
        from app.models.permission import Permission
        role_ids = [r[0] for r in db.query(UserRole.role_id).filter(UserRole.user_id == user_id).all()]
        if not role_ids:
            return False
        perm = (
            db.query(RolePermission)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .filter(
                RolePermission.role_id.in_(role_ids),
                Permission.name == "access.manage",
            )
            .first()
        )
        return perm is not None
    except Exception:
        return True


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


def _get_schema_context(db_conn: DatabaseConnection) -> tuple[str, dict[str, set[str]], dict]:
    try:
        connector = get_connector(db_conn)
        schema = connector.get_schema()
        lines = [
            f"DATABASE TYPE: {db_conn.connection_type.upper()} ({db_conn.name})",
            f"SCHEMA / OWNER: {db_conn.schema_name or 'Default'}",
            "",
            "AVAILABLE TABLES & STRUCTURE:"
        ]
        
        pk_map = {}
        all_table_cols: dict[str, set[str]] = {}
        related_tables: set[str] = set()
        categorical_map: dict[str, list[dict]] = {}
        numeric_cols: list[tuple[str, str]] = []
        stop_words = {"paid", "active", "inactive", "booked", "completed", "in progress", "true", "false", "none", "null", "full_day", "van", "car", "bike"}

        sorted_tables = sorted(schema.tables, key=lambda t: (0 if (t.row_count or 0) > 0 else 1, t.name))
        empty_table_names = []

        for table in sorted_tables:
            t_name = table.name.upper()
            all_table_cols[t_name] = set()
            for c in table.columns:
                c_name = c.name.upper()
                all_table_cols[t_name].add(c_name)
                if c.sample_values:
                    for sv in c.sample_values:
                        sv_str = str(sv).strip()
                        if len(sv_str) >= 2 and sv_str.lower() not in stop_words:
                            categorical_map.setdefault(sv_str.lower(), []).append({
                                "table": t_name,
                                "column": c_name,
                                "value": sv_str
                            })
                if any(nt in c.data_type.upper() for nt in ("NUMBER", "INT", "FLOAT", "DECIMAL", "NUMERIC")):
                    numeric_cols.append((t_name, c_name))

            # If table is completely empty, summarize it compactly to keep context focused
            if table.row_count == 0 and not table.foreign_keys:
                empty_table_names.append(table.name)
                continue

            col_lines = []
            for c in table.columns:
                c_name = c.name.upper()
                tags = []
                if c.is_primary_key:
                    tags.append("[PRIMARY KEY]")
                    pk_map[c_name] = t_name
                if c.is_foreign_key:
                    tags.append("[FOREIGN KEY]")
                if c.sample_values:
                    tags.append(f"[Sample Values: {c.sample_values[:8]}]")
                tag_str = " " + " ".join(tags) if tags else ""
                col_lines.append(f"  - {c.name} ({c.data_type}{tag_str})")
            
            row_count_str = f" (Rows: {table.row_count})" if table.row_count is not None else ""
            lines.append(f"Table: {table.name}{row_count_str}")
            lines.extend(col_lines)
            lines.append("")

        if empty_table_names:
            lines.append(f"EMPTY TABLES (0 ROWS): {', '.join(sorted(empty_table_names))}")
            lines.append("")

        # 2. Extract verified foreign key relationships
        verified_relationships = []
        fk_tuples = []
        if hasattr(schema, "foreign_keys") and schema.foreign_keys:
            for fk in schema.foreign_keys:
                if fk.table_name and fk.referenced_table:
                    t1 = fk.table_name.upper()
                    t2 = fk.referenced_table.upper()
                    related_tables.add(t1)
                    related_tables.add(t2)
                    c1 = fk.column_name.upper()
                    c2 = fk.referenced_column.upper()
                    fk_tuples.append((t1, c1, t2, c2))
                    verified_relationships.append(
                        f"- {t1}.{c1} relates to {t2}.{c2}"
                    )
        
        # Fallback relationship detection if no explicit FKs are configured
        if not verified_relationships:
            for t_upper, t_cols in all_table_cols.items():
                for c_upper in t_cols:
                    if c_upper.endswith(("_ID", "_CODE")):
                        for target_t, target_cols in all_table_cols.items():
                            if target_t != t_upper and c_upper in target_cols:
                                related_tables.add(t_upper)
                                related_tables.add(target_t)
                                fk_tuples.append((t_upper, c_upper, target_t, c_upper))
                                verified_relationships.append(
                                    f"- {t_upper}.{c_upper} relates to {target_t}.{c_upper}"
                                )

        if verified_relationships:
            lines.append("VERIFIED DATABASE RELATIONSHIPS (FOREIGN KEYS):")
            lines.extend(sorted(set(verified_relationships)))
            lines.append("")

        # 3. Identify Independent / Isolated Tables
        independent_tables = [t for t in all_table_cols.keys() if t not in related_tables]
        if independent_tables:
            lines.append("INDEPENDENT / COMPANY-WIDE TABLES (NO DIRECT FOREIGN KEYS):")
            lines.append(f"- Tables: {', '.join(sorted(independent_tables))}")
            lines.append(
                "- CRITICAL JOIN SAFETY RULE: These tables have NO foreign keys to other tables. "
                "Never join an independent table directly to other tables using JOIN or comma-separated FROM, "
                "as this produces invalid Cartesian products and multiplied numbers. "
                "If a query requires both independent data and other metrics, compute each in a separate "
                "Common Table Expression (WITH clause) and combine them via CROSS JOIN, or query separately."
            )
            lines.append("")

        schema_metadata = {
            "active_tables": {t.name.upper(): t for t in sorted_tables if (t.row_count or 0) > 0},
            "all_table_cols": all_table_cols,
            "categorical_map": categorical_map,
            "numeric_cols": numeric_cols,
            "foreign_keys": fk_tuples,
        }

        return "\n".join(lines), all_table_cols, schema_metadata
    except Exception:
        return f"Database Type: {db_conn.connection_type}. Schema unavailable.", {}, {}


def _analyze_intent_and_resolve(natural_language: str, schema_metadata: dict, dialect: str) -> tuple[str, str, list[dict], str]:
    q_lower = natural_language.lower()
    active_tables = schema_metadata.get("active_tables", {})
    numeric_cols = schema_metadata.get("numeric_cols", [])
    categorical_map = schema_metadata.get("categorical_map", {})
    fk_list = schema_metadata.get("foreign_keys", [])
    all_table_cols = schema_metadata.get("all_table_cols", {})

    # 1. Schema / Metadata Exploration Check (e.g. "what are the tables available in the DB", "show tables")
    is_schema_question = (
        any(w in q_lower for w in ("table", "tables", "schema", "schemas", "database", "structure", "columns"))
        and any(w in q_lower for w in ("what", "which", "show", "list", "available", "exist", "all", "describe", "tell", "display"))
        and not any(w in q_lower for w in ("count", "sum", "average", "avg", "highest", "lowest", "calculate", "spent", "salary", "revenue", "price", "cost"))
    )

    # 2. Ambiguous Question Check
    ambiguous_keywords = ["best", "greatest", "top performer", "most successful", "worst", "lowest performer"]
    has_ambiguity = any(re.search(rf"\b{re.escape(k)}\b", q_lower) for k in ambiguous_keywords)
    metrics_mentioned = [c for t, c in numeric_cols if c.lower() in q_lower or any(syn in q_lower for syn in (c.lower().replace("_", " "), "salary", "revenue", "profit", "budget", "spent", "score", "headcount", "cost", "margin", "amount", "price"))]
    if has_ambiguity and not metrics_mentioned:
        suggs = [f"- `{t}.{c}`" for t, c in numeric_cols[:6]]
        return (
            "AMBIGUOUS",
            f"### 🎯 Direct Answer\nThe question is ambiguous because subjective terms like 'best' or 'greatest' require a specific metric.\n\n### 💡 Suggested Metrics\nPlease specify which metric you would like to evaluate, such as:\n" + "\n".join(suggs),
            [],
            ""
        )

    # 3. Entity Matching
    matched = []
    for val_lower, entries in categorical_map.items():
        pattern = rf"\b{re.escape(val_lower)}\b"
        if re.search(pattern, q_lower):
            for e in entries:
                matched.append(e)

    # 4. Unrelated Question Check
    if not is_schema_question:
        all_table_words = {t.lower() for t in active_tables} | {t.lower().rstrip("s") for t in active_tables}
        for t in active_tables:
            for w in t.lower().split("_"):
                all_table_words.add(w)

        all_col_words = set()
        for t, cols in all_table_cols.items():
            for c in cols:
                all_col_words.add(c.lower())
                for w in c.lower().split("_"):
                    all_col_words.add(w)

        q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", q_lower))
        relevant_matches = (q_words & all_table_words) | (q_words & all_col_words) | {e["value"].lower() for e in matched}
        common_db_words = {"how", "many", "count", "average", "avg", "total", "sum", "highest", "lowest", "list", "show", "what", "which", "who", "where", "table", "data", "row", "record", "earn", "earns", "cost", "costs", "spend", "spending", "spent", "pay", "paid", "make", "makes", "quarter", "quarterly", "year", "percentage", "pct", "ratio", "more", "less", "than"}
        has_business_intent = bool(q_words & common_db_words)

        if not relevant_matches and not (has_business_intent and (q_words & (all_table_words | all_col_words))):
            topics = [f"- {t.title().replace('_', ' ')}" for t in (active_tables.keys() or all_table_cols.keys())]
            return (
                "UNRELATED",
                f"### 🎯 Direct Answer\nThis question cannot be answered from the connected database. The database does not contain information to answer this question.\n\n### 💡 Available Topics\nBased on your database schema, you can query data related to:\n" + "\n".join(topics[:8]),
                [],
                ""
            )

    # 5. Construct Dynamic Guidance
    guidance = []

    if is_schema_question:
        if dialect == "MySQL":
            guidance.append("- SCHEMA INTROSPECTION QUERY: The user is asking for the tables in this MySQL database. Use: SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE(); (or SHOW TABLES;).")
        elif dialect == "PostgreSQL":
            guidance.append("- SCHEMA INTROSPECTION QUERY: The user is asking for the tables in this PostgreSQL database. Use: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
        elif dialect == "Oracle SQL":
            guidance.append("- SCHEMA INTROSPECTION QUERY: The user is asking for the tables in this Oracle database. Use: SELECT table_name FROM user_tables;")
        elif dialect == "SQLite":
            guidance.append("- SCHEMA INTROSPECTION QUERY: The user is asking for the tables in this SQLite database. Use: SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';")
        else:
            guidance.append("- SCHEMA INTROSPECTION QUERY: Use: SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE';")

    if matched:
        guidance.append("DYNAMIC ENTITY RESOLUTION:")
        for m in matched:
            guidance.append(f"- Entity '{m['value']}' was discovered in table {m['table']}, column {m['column']}.")
            for t1, c1, t2, c2 in fk_list:
                if t1 == m['table']:
                    guidance.append(f"  Relationship: {t1}.{c1} relates to {t2}.{c2}")
                elif t2 == m['table']:
                    guidance.append(f"  Relationship: {t2}.{c2} relates to {t1}.{c1}")
            guidance.append(f"  CRITICAL: If querying other tables, JOIN {m['table']} on the foreign key and filter WHERE {m['table']}.{m['column']} = '{m['value']}'.")

    # Match relevant tables by column keywords
    q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", q_lower))
    rel_tables = []
    active_cols = {t: cols for t, cols in all_table_cols.items() if t in active_tables} or all_table_cols
    for tbl, cols in active_cols.items():
        matched_cols = [c for c in cols if any(w in c.lower() for w in q_words if len(w) >= 3)]
        if matched_cols:
            rel_tables.append((tbl, matched_cols))

    rel_table_names = {tbl for tbl, _ in rel_tables} | {m["table"] for m in matched}

    if rel_tables:
        guidance.append("RELEVANT ACTIVE TABLES & COLUMNS:")
        for tbl, cols in sorted(rel_tables, key=lambda x: len(x[1]), reverse=True)[:5]:
            guidance.append(f"- Table {tbl}: verified columns {', '.join(sorted(cols))}")

    # Add verified foreign key relationships between relevant tables dynamically
    for t1, c1, t2, c2 in fk_list:
        if t1 in rel_table_names and t2 in rel_table_names:
            guidance.append(f"- Foreign Key Relationship: {t1}.{c1} relates to {t2}.{c2}. Use: JOIN {t2} ON {t1}.{c1} = {t2}.{c2}")

    # Ranking single item guidance
    if any(w in q_lower for w in ("highest", "lowest", "most", "least", "top", "best", "bottom")) and "summary" not in q_lower:
        if dialect == "Oracle SQL":
            guidance.append("- RANKING RULE: For questions asking for the 'highest', 'lowest', 'most', or 'top' single entity, ORDER BY the relevant metric (DESC for highest/most, ASC for lowest/least) and append 'FETCH FIRST 1 ROWS ONLY'.")
        elif dialect in ("PostgreSQL", "MySQL", "SQLite"):
            guidance.append("- RANKING RULE: For questions asking for the 'highest', 'lowest', 'most', or 'top' single entity, ORDER BY the relevant metric (DESC for highest/most, ASC for lowest/least) and append 'LIMIT 1'.")
        elif dialect in ("SQL Server", "T-SQL"):
            guidance.append("- RANKING RULE: Use 'SELECT TOP 1' with ORDER BY the relevant metric.")

    return "VALID", "", matched, "\n".join(guidance)


def _find_best_column_match(col_name: str, valid_cols: set[str] | list[str], table_name: str = "") -> Optional[str]:
    col_upper = col_name.upper()
    valid_upper = [c.upper() for c in valid_cols]
    if col_upper in valid_upper:
        return col_upper

    core_col = col_upper
    if table_name:
        t_prefix = table_name.rstrip("S").upper() + "_"
        if core_col.startswith(t_prefix):
            core_col = core_col[len(t_prefix):]
    for pfx in ("TOTAL_", "AVG_", "SUM_", "MAX_", "MIN_"):
        if core_col.startswith(pfx):
            core_col = core_col[len(pfx):]

    synonym_map = {
        ("SPEND", "SPENDING", "COST", "EXPENSE"): "SPENT",
        ("SALARY", "COMPENSATION", "PAY", "SALARY_COST"): "SALARY",
        ("PROFIT", "EARNING", "NET"): "NET_PROFIT",
        ("REVENUE", "SALES_AMOUNT", "SALES", "TURNOVER"): "TOTAL_REVENUE",
        ("QUARTER_ID", "QTR"): "QUARTER",
        ("NAME", "EMP_NAME", "EMPLOYEE_NAME", "FULLNAME"): "FIRST_NAME",
    }
    for syn_keys, target_col in synonym_map.items():
        if any(sk in core_col for sk in syn_keys):
            if target_col in valid_upper:
                return target_col
            for vc in valid_upper:
                if target_col in vc or vc in target_col:
                    return vc

    close = difflib.get_close_matches(core_col, valid_upper, n=1, cutoff=0.5)
    if close:
        return close[0]

    close_orig = difflib.get_close_matches(col_upper, valid_upper, n=1, cutoff=0.5)
    if close_orig:
        return close_orig[0]

    return None


# System Catalog & Metadata Whitelist across all database engines
SYSTEM_CATALOG_TABLES = {
    "DUAL",
    # ANSI / Information Schema
    "INFORMATION_SCHEMA", "TABLES", "COLUMNS", "VIEWS", "SCHEMATA", "KEY_COLUMN_USAGE",
    "TABLE_CONSTRAINTS", "STATISTICS", "ROUTINES", "PARAMETERS", "REFERENTIAL_CONSTRAINTS",
    # PostgreSQL
    "PG_CATALOG", "PG_TABLES", "PG_CLASS", "PG_NAMESPACE", "PG_ATTRIBUTE", "PG_TYPE",
    "PG_DATABASE", "PG_INDEX", "PG_STAT_USER_TABLES", "PG_VIEWS",
    # Oracle
    "USER_TABLES", "ALL_TABLES", "DBA_TABLES", "USER_TAB_COLUMNS", "ALL_TAB_COLUMNS", "DBA_TAB_COLUMNS",
    "USER_CONSTRAINTS", "ALL_CONSTRAINTS", "USER_CONS_COLUMNS", "ALL_CONS_COLUMNS", "USER_VIEWS", "ALL_VIEWS",
    "USER_OBJECTS", "ALL_OBJECTS", "V$VERSION", "V$SESSION",
    # SQLite
    "SQLITE_MASTER", "SQLITE_SCHEMA", "SQLITE_TEMP_MASTER", "SQLITE_TEMP_SCHEMA", "SQLITE_SEQUENCE",
    # SQL Server
    "SYS", "SYSOBJECTS", "SYSCOLUMNS", "SYSTABLES",
    # ClickHouse / Snowflake
    "SYSTEM",
}


def _validate_sql_before_execution(
    sql: str, 
    table_cols: dict[str, set[str]], 
    dialect: str,
    matched_entities: list[dict] = None,
    natural_language: str = "",
    schema_metadata: dict = None,
) -> tuple[bool, str, Optional[str]]:
    if not sql or not sql.strip():
        return False, "", "SQL query is empty."

    sanitized = sql.strip().rstrip(";") + ";"

    # Allow direct metadata inspection commands (e.g. SHOW TABLES, DESCRIBE ...)
    if re.match(r"^\s*(SHOW\s+|DESCRIBE\s+|DESC\s+)", sanitized, flags=re.IGNORECASE):
        return True, sanitized, None

    # Oracle specific syntax sanitization
    if dialect == "Oracle SQL":
        sanitized = re.sub(
            r"\b(FROM|JOIN)\s+([a-zA-Z0-9_]+)\s+AS\s+([a-zA-Z0-9_]+)\b",
            r"\1 \2 \3",
            sanitized,
            flags=re.IGNORECASE,
        )
        sanitized = re.sub(r"\)\s*AS\s+([a-zA-Z0-9_]+)\b", r") \1", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\bLIMIT\s+(\d+)\s*;?$", r"FETCH FIRST \1 ROWS ONLY;", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\bFETCH\s+FIRST\s+(\d+)\s+ROW\s+ONLY", r"FETCH FIRST \1 ROWS ONLY", sanitized, flags=re.IGNORECASE)

    # Check matched entity inclusion
    if matched_entities:
        for m in matched_entities:
            tbl = m["table"].upper()
            if tbl not in sanitized.upper():
                return (
                    False,
                    sanitized,
                    f"The query is missing table '{tbl}'. The user question references '{m['value']}' which belongs to table '{tbl}.{m['column']}'. Please JOIN table '{tbl}' and filter WHERE {tbl}.{m['column']} = '{m['value']}'."
                )

    # Validate table and column existence against schema
    if table_cols:
        cte_names = set(re.findall(r"(?:\bWITH\s+|,)\s*([a-zA-Z0-9_]+)\s+AS\s*\(", sanitized, flags=re.IGNORECASE))
        cte_names_upper = {c.upper() for c in cte_names}

        # CTE Exposed Column Scoping: Track output columns explicitly selected inside each CTE
        cte_exposed_cols = {}
        cte_blocks = re.findall(r"([a-zA-Z0-9_]+)\s+AS\s*\(\s*SELECT\b([\s\S]*?)\bFROM\b", sanitized, flags=re.IGNORECASE)
        for cte_name, select_clause in cte_blocks:
            c_name_up = cte_name.upper()
            exposed = set()
            as_aliases = re.findall(r"\bAS\s+([a-zA-Z0-9_]+)\b", select_clause, flags=re.IGNORECASE)
            for a in as_aliases:
                exposed.add(a.upper())
            raw_cols = re.findall(r"\b(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)\b", select_clause)
            sql_kw = {"SELECT", "FROM", "WHERE", "JOIN", "ON", "GROUP", "BY", "ORDER", "AS", "SUM", "COUNT", "AVG", "MIN", "MAX", "ROUND", "NVL", "COALESCE", "CASE", "WHEN", "THEN", "ELSE", "END", "DISTINCT", "ALL"}
            for rc in raw_cols:
                rc_up = rc.upper()
                if rc_up not in sql_kw and not rc.isdigit():
                    exposed.add(rc_up)
            cte_exposed_cols[c_name_up] = exposed

        # 1. Check table existence (dynamic across any schema & allowing system catalogs)
        table_matches = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z0-9_\.]+)(?:\s+(?:AS\s+)?([a-zA-Z0-9_]+))?", sanitized, flags=re.IGNORECASE)
        alias_to_table = {}
        alias_to_cte = {}
        tables_in_query = []

        active_schema_tables = sorted([t for t in table_cols.keys() if t not in cte_names_upper])

        for t, alias in table_matches:
            t_clean = t.strip().rstrip(";")
            t_upper = t_clean.upper()
            parts = t_upper.split(".")

            # Check if it is a CTE
            if t_upper in cte_names_upper or t_upper in cte_exposed_cols:
                if alias and alias.upper() not in ("ON", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "CROSS", "SELECT", "SET"):
                    cte_names_upper.add(alias.upper())
                    alias_to_cte[alias.upper()] = t_upper
                alias_to_cte[t_upper] = t_upper
                continue

            # Check if it is a system catalog table, view, or dual table
            if any(p in SYSTEM_CATALOG_TABLES for p in parts) or t_upper in SYSTEM_CATALOG_TABLES or t_upper in ("DUAL", "SELECT", "LATERAL"):
                if alias and alias.upper() not in ("ON", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "CROSS", "SELECT", "SET"):
                    alias_to_table[alias.upper()] = t_upper
                alias_to_table[t_upper] = t_upper
                continue

            # Check user table existence in active schema
            matched_schema_tbl = None
            for s_tbl in table_cols:
                if s_tbl.upper() == t_upper or (len(parts) > 1 and s_tbl.upper() == parts[-1]):
                    matched_schema_tbl = s_tbl.upper()
                    break

            if not matched_schema_tbl:
                col_found_in = [tbl for tbl, c_set in table_cols.items() if t_upper in c_set or (len(parts) > 1 and parts[-1] in c_set)]
                if col_found_in:
                    return (
                        False,
                        sanitized,
                        f"Table '{t}' does not exist in schema. '{t}' is actually a column in table '{col_found_in[0]}'. Available valid tables are: {', '.join(active_schema_tables)}. Query '{t}' directly from '{col_found_in[0]}'."
                    )
                return (
                    False,
                    sanitized,
                    f"Table '{t}' does not exist in the connected database schema. Available tables are: {', '.join(active_schema_tables)}. Do not invent non-existent table names."
                )

            tables_in_query.append(matched_schema_tbl)
            if alias and alias.upper() not in ("ON", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "CROSS"):
                alias_to_table[alias.upper()] = matched_schema_tbl
            alias_to_table[matched_schema_tbl] = matched_schema_tbl

        # 2. Check join condition validity
        join_conditions = re.findall(r"\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\b", sanitized)
        for a1, c1, a2, c2 in join_conditions:
            for a_curr, c_curr in ((a1, c1), (a2, c2)):
                a_up, c_up = a_curr.upper(), c_curr.upper()
                if a_up in alias_to_table and alias_to_table[a_up] in table_cols:
                    t_target = alias_to_table[a_up]
                    if c_up not in table_cols[t_target]:
                        return (
                            False,
                            sanitized,
                            f"Invalid JOIN condition: Column '{c_curr}' does not exist in table '{t_target}'. Available columns in '{t_target}' are: {', '.join(sorted(table_cols[t_target]))}."
                        )

        # 3. Check qualified column references: alias.column
        qualified_cols = re.findall(r"\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\b", sanitized)
        for alias, col in qualified_cols:
            alias_up = alias.upper()
            col_up = col.upper()
            if alias_up in alias_to_table:
                target_table = alias_to_table[alias_up]
                # Skip checking columns for system catalog tables
                if target_table in SYSTEM_CATALOG_TABLES or any(p in SYSTEM_CATALOG_TABLES for p in target_table.split(".")):
                    continue
                if target_table in table_cols and col_up not in table_cols[target_table]:
                    tables_with_col = [tbl for tbl, c_set in table_cols.items() if col_up in c_set]
                    hint = f" (Column exists in table: {', '.join(tables_with_col)})" if tables_with_col else ""
                    best_match = _find_best_column_match(col, table_cols[target_table], target_table)
                    concept_hint = f" Did you mean '{best_match}' in '{target_table}'?" if best_match else ""
                    return (
                        False,
                        sanitized,
                        f"Column '{col}' does not exist in table '{target_table}'{hint}.{concept_hint} Available columns in '{target_table}' are: {', '.join(sorted(table_cols[target_table]))}. Do NOT invent column names."
                    )
            elif alias_up in alias_to_cte:
                target_cte = alias_to_cte[alias_up]
                exposed = cte_exposed_cols.get(target_cte, set())
                if exposed and col_up not in exposed:
                    return (
                        False,
                        sanitized,
                        f"CTE Column Reference Error: Column '{col}' is not exposed by CTE '{target_cte}'. CTE '{target_cte}' only exposes the following selected columns: {', '.join(sorted(exposed))}. Every column referenced from a CTE in the outer query must be explicitly selected inside that CTE's SELECT clause."
                    )

        # 4. Check unqualified column references in SELECT/WHERE/GROUP BY/ORDER BY
        clean_sql_no_literals = re.sub(r"'[^']*'", "", sanitized)
        select_as_aliases = {a.upper() for a in re.findall(r"\bAS\s+([a-zA-Z0-9_]+)\b", clean_sql_no_literals, flags=re.IGNORECASE)}
        subquery_aliases = {a.upper() for a in re.findall(r"\)\s*(?:AS\s+)?([a-zA-Z0-9_]+)\b", clean_sql_no_literals, flags=re.IGNORECASE)}
        clean_sql_no_subqueries = re.sub(r"\(SELECT[\s\S]*?\)", "", clean_sql_no_literals, flags=re.IGNORECASE)
        unqualified = re.findall(r"\b([a-zA-Z0-9_]+)\b", clean_sql_no_subqueries)
        sql_keywords = {
            "SELECT", "FROM", "WHERE", "JOIN", "ON", "LEFT", "RIGHT", "INNER", "CROSS", "GROUP", "BY",
            "ORDER", "HAVING", "FETCH", "FIRST", "ROWS", "ONLY", "WITH", "AS", "AND", "OR", "NOT",
            "NULL", "IS", "SUM", "COUNT", "AVG", "MIN", "MAX", "ROUND", "NVL", "COALESCE", "NULLIF",
            "CASE", "WHEN", "THEN", "ELSE", "END", "DESC", "ASC", "DUAL", "LIMIT", "LIKE", "IN",
            "SHOW", "DESCRIBE", "DESC", "TABLES", "COLUMNS", "DATABASE", "TABLE", "SCHEMA",
        }
        all_known_cols = set()
        for t_in_q in tables_in_query:
            if t_in_q in table_cols:
                all_known_cols.update(table_cols[t_in_q])

        for cand in unqualified:
            cand_up = cand.upper()
            if (
                cand_up not in sql_keywords
                and cand_up not in alias_to_table
                and cand_up not in cte_names_upper
                and cand_up not in select_as_aliases
                and cand_up not in subquery_aliases
                and cand_up not in table_cols
                and cand_up not in SYSTEM_CATALOG_TABLES
                and not cand.isdigit()
            ):
                if all_known_cols and cand_up not in all_known_cols:
                    best_match = _find_best_column_match(cand, all_known_cols)
                    concept_hint = f" Did you mean '{best_match}'?" if best_match else ""
                    return (
                        False,
                        sanitized,
                        f"Invalid column '{cand}': Every column in your query MUST exist in the schema.{concept_hint} Do NOT invent column names."
                    )

        # 5. Dynamic Row Multiplication / Fan-Out Prevention
        if schema_metadata and "foreign_keys" in schema_metadata:
            fk_tuples = schema_metadata["foreign_keys"]
            parent_to_children: dict[str, set[str]] = {}
            for child_tbl, child_col, parent_tbl, parent_col in fk_tuples:
                parent_to_children.setdefault(parent_tbl.upper(), set()).add(child_tbl.upper())

            for parent_tbl, child_set in parent_to_children.items():
                joined_children = [t for t in tables_in_query if t in child_set]
                if len(joined_children) >= 2 and not cte_names and any(agg in sanitized.upper() for agg in ("SUM(", "COUNT(", "AVG(")):
                    return (
                        False,
                        sanitized,
                        f"Row Multiplication Error: Directly joining multiple one-to-many child tables ({', '.join(joined_children)}) to {parent_tbl} in a single FROM clause before aggregation multiplies row counts, causing incorrect business totals. You MUST pre-aggregate each child table independently in a CTE (WITH clause) grouped by the foreign key first, and then join the pre-aggregated CTEs."
                    )

        # 6. Check Oracle SELECT alias usage in WHERE / HAVING
        if dialect == "Oracle SQL":
            main_sql = re.sub(r"WITH[\s\S]*?\)\s*(SELECT\b)", r"\1", sanitized, flags=re.IGNORECASE)
            select_match = re.search(r"\bSELECT\b([\s\S]*?)\bFROM\b", main_sql, flags=re.IGNORECASE)
            where_match = re.search(r"\bWHERE\b([\s\S]*?)(?:\bGROUP\b|\bORDER\b|\bFETCH\b|;|$)", main_sql, flags=re.IGNORECASE)
            having_match = re.search(r"\bHAVING\b([\s\S]*?)(?:\bORDER\b|\bFETCH\b|;|$)", main_sql, flags=re.IGNORECASE)
            if select_match:
                aliases = set(re.findall(r"\bAS\s+([a-zA-Z0-9_]+)\b", select_match.group(1), flags=re.IGNORECASE))
                for target_clause in (where_match, having_match):
                    if target_clause:
                        clause_txt = target_clause.group(1)
                        clean_clause = re.sub(r"\(SELECT[\s\S]*?\)", "", clause_txt, flags=re.IGNORECASE)
                        for a in aliases:
                            if re.search(rf"(?<!\.)\b{re.escape(a)}\b", clean_clause, flags=re.IGNORECASE):
                                return (
                                    False,
                                    sanitized,
                                    f"Oracle SQL error: Column alias '{a}' cannot be referenced in WHERE or HAVING clauses. Repeat the expression or use a subquery/CTE."
                                )

    return True, sanitized, None


def _validate_query_results(sql: str, columns: list[str], rows: list[list], table_cols: dict[str, set[str]] = None) -> tuple[bool, str]:
    if not rows or not columns:
        return True, "Query executed successfully; returned 0 rows matching criteria."
    # Check if all aggregate values in row 0 are None (meaning 0 rows matched the WHERE filter)
    if len(rows) == 1 and all(cell is None for cell in rows[0]):
        where_match = re.search(r"\bWHERE\b([\s\S]*?)(?:\bGROUP\b|\bORDER\b|\bFETCH\b|;|$)", sql, flags=re.IGNORECASE)
        hint = ""
        if where_match and table_cols:
            filter_text = where_match.group(1).strip()
            literal_match = re.search(r"'([^']+)'", filter_text)
            if literal_match:
                val = literal_match.group(1)
                hint = f" The filter value '{val}' yielded 0 rows. Check if '{val}' belongs to a column in another table (e.g. DEPARTMENTS.DEPARTMENT_NAME) and JOIN that table using foreign keys."
        return False, f"Query returned NULL (0 rows matched the WHERE filter condition).{hint}"
    if len(rows) > 500 and "CROSS JOIN" in sql.upper():
        return False, "Query returned a large number of rows with CROSS JOIN; verify Cartesian product did not occur."
    return True, f"Query returned {len(rows)} validated rows."


def execute_natural_language_query(
    db: Session,
    data: QueryRequest,
    user_id: int,
    include_all: Optional[bool] = None,
    use_mcp_tools: Optional[bool] = None,
) -> QueryResponse:
    if include_all is None:
        include_all = _user_has_manage_permission(db, user_id)
    db_conn = get_database(
        db, data.database_id, user_id=user_id, include_all=include_all,
    )
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database not found")

    user = db.query(User).filter(User.id == user_id).first()
    company_id = db_conn.company_id or (user.company_id if user else None)

    # Check if we should use MCP tools
    if use_mcp_tools is None:
        use_mcp_tools = getattr(settings, 'USE_MCP_TOOLS', False)
    
    if use_mcp_tools:
        try:
            # Use MCP query_data tool which handles NL->SQL and execution
            import httpx
            
            # Prepare MCP request
            mcp_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "query_data",
                    "arguments": {
                        "database_id": data.database_id,
                        "question": data.natural_language
                    }
                },
                "id": 1
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            if settings.MCP_API_KEY:
                headers["X-API-Key"] = settings.MCP_API_KEY
            
            # Make HTTP request to MCP server
            with httpx.Client(timeout=30.0) as client:
                mcp_response = client.post(
                    f"{settings.APP_URL}/mcp",
                    json=mcp_payload,
                    headers=headers
                )
                mcp_response.raise_for_status()
                
                mcp_result = mcp_response.json()
                
                if "error" in mcp_result:
                    raise Exception(f"MCP error: {mcp_result['error']}")
                
                result_data = mcp_result.get("result", {})
                
                # Extract information from MCP response
                explanation = result_data.get("text", "Query executed successfully via MCP.")
                sql = result_data.get("sql", "")
                
                # Create query record
                query_record = Query(
                    user_id=user_id,
                    company_id=company_id,
                    database_id=data.database_id,
                    natural_language=data.natural_language,
                    generated_sql=sql,
                    explanation=explanation,
                    status="completed",
                    tokens_used=len(data.natural_language.split()) * 3 + len(sql.split()) * 2,
                    conversation_id=data.conversation_id,
                )
                
                # Handle results if present in structured format
                if "structuredContent" in result_data and result_data["structuredContent"]:
                    structured = result_data["structuredContent"]
                    if isinstance(structured, dict) and "rows" in structured:
                        columns = structured.get("columnNames", [])
                        rows = structured.get("rows", [])
                        
                        query_record.result_columns = columns
                        query_record.result_rows = rows[:1000]
                        query_record.row_count = len(rows)
                        query_record.execution_time_ms = 0
                        
                        db.add(query_record)
                        db.commit()
                        db.refresh(query_record)
                        
                        # Add visualization suggestions before returning
                        result = _db_conn_to_query_response(query_record)
                        result.suggested_visualizations = _get_visualization_suggestions(query_record)
                        return result
                
                # If we couldn't process structured results, create minimal record
                query_record.result_columns = []
                query_record.result_rows = []
                query_record.row_count = 0
                
                db.add(query_record)
                db.commit()
                db.refresh(query_record)
                
                # Add visualization suggestions before returning
                result = _db_conn_to_query_response(query_record)
                result.suggested_visualizations = _get_visualization_suggestions(query_record)
                return result
                
        except Exception:
            # Fall back to traditional approach if MCP fails
            pass
    
    schema_context, table_cols, schema_metadata = _get_schema_context(db_conn)
    dialect = llm_service._get_db_dialect(db_conn.connection_type)

    # 1. Analyze Intent & Resolve Entities Dynamically
    intent_status, intent_message, matched_entities, dynamic_guidance = _analyze_intent_and_resolve(
        data.natural_language, schema_metadata, dialect
    )

    if intent_status in ("UNRELATED", "AMBIGUOUS"):
        query_record = Query(
            user_id=user_id,
            company_id=company_id,
            database_id=data.database_id,
            natural_language=data.natural_language,
            generated_sql=None,
            explanation=intent_message,
            status="completed",
            tokens_used=10,
            conversation_id=data.conversation_id,
            result_columns=[],
            result_rows=[],
            row_count=0,
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)
        return _db_conn_to_query_response(query_record)

    prompt_nl = f"Write a single executable {dialect} query strictly inside a ```sql ... ``` code block to retrieve data for:\n{data.natural_language}"
    if dynamic_guidance:
        prompt_nl += "\n\n" + dynamic_guidance
    sql, explanation, tokens_used = llm_service.generate_sql(
        prompt_nl, schema_context, db_conn.connection_type,
    )

    if not sql or sql.strip() in (";", ""):
        sql = "SELECT 1 FROM DUAL WHERE 1=0;" if dialect == "Oracle SQL" else "SELECT 1 WHERE 1=0;"
        explanation = "Could not generate a valid SQL query from your question. Try rephrasing or specifying the entity name."

    # 2. Pre-execution SQL Validation & auto-repair loop
    for _ in range(3):
        is_valid, sanitized_sql, val_err = _validate_sql_before_execution(sql, table_cols, dialect, matched_entities, data.natural_language, schema_metadata)
        if is_valid:
            sql = sanitized_sql
            break
        fixed_sql, fix_explanation, fix_tokens = llm_service.fix_sql(
            prompt_nl, sql, val_err, schema_context, db_conn.connection_type,
        )
        sql = fixed_sql
        explanation = fix_explanation
        tokens_used = (tokens_used or 0) + (fix_tokens or 0)
        is_valid_after, sanitized_after, _ = _validate_sql_before_execution(sql, table_cols, dialect, matched_entities, data.natural_language, schema_metadata)
        if is_valid_after:
            sql = sanitized_after
            break
    else:
        is_valid, sanitized_sql, _ = _validate_sql_before_execution(sql, table_cols, dialect, matched_entities, data.natural_language, schema_metadata)
        sql = sanitized_sql

    query_record = Query(
        user_id=user_id,
        company_id=company_id,
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

    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            is_valid, exec_sql, val_err = _validate_sql_before_execution(sql, table_cols, dialect, matched_entities, data.natural_language, schema_metadata)
            if not is_valid:
                if attempt < max_retries:
                    sql, explanation, retry_tokens = llm_service.fix_sql(
                        prompt_nl, sql, val_err, schema_context, db_conn.connection_type,
                    )
                    query_record.generated_sql = sql
                    query_record.explanation = explanation
                    query_record.tokens_used = (query_record.tokens_used or 0) + (retry_tokens or 0)
                    db.commit()
                    continue
                else:
                    raise Exception(f"SQL Validation Error: {val_err}")

            connector = get_connector(db_conn)
            start = time.time()

            raw_results = connector.execute_query(exec_sql)
            elapsed = int((time.time() - start) * 1000)

            columns = raw_results.get("columns", [])
            rows = _serialize_rows(raw_results.get("rows", []))
            row_count = len(rows)

            # Result validation & recovery
            val_ok, val_notes = _validate_query_results(exec_sql, columns, rows, table_cols)
            if not val_ok and attempt < max_retries:
                sql, explanation, retry_tokens = llm_service.fix_sql(
                    prompt_nl, exec_sql, val_notes, schema_context, db_conn.connection_type,
                )
                query_record.generated_sql = sql
                query_record.explanation = explanation
                query_record.tokens_used = (query_record.tokens_used or 0) + (retry_tokens or 0)
                db.commit()
                continue

            query_record.status = "completed"
            query_record.generated_sql = exec_sql
            query_record.result_columns = columns
            query_record.result_rows = rows[:1000]
            query_record.row_count = row_count
            query_record.execution_time_ms = elapsed

            summary_explanation = llm_service.synthesize_data_summary(
                data.natural_language, exec_sql, columns, rows
            )
            if summary_explanation:
                query_record.explanation = summary_explanation

            break
        except Exception as e:
            raw_err = str(e)

            # Construct exact technical diagnostic for the LLM
            error_diagnostic = raw_err
            inv_col_match = re.search(r'ORA-00904:\s*(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?', raw_err, flags=re.IGNORECASE)
            if inv_col_match:
                alias_or_table = inv_col_match.group(1)
                bad_col = inv_col_match.group(2).upper()
                table_hint = ""
                target_table = None
                if alias_or_table:
                    for t in table_cols:
                        if t.startswith(alias_or_table.upper()) or alias_or_table.upper() in (t[0], t):
                            target_table = t
                            break
                if target_table and target_table in table_cols:
                    best = _find_best_column_match(bad_col, table_cols[target_table], target_table)
                    table_hint = f" In table '{target_table}', available columns are: {', '.join(sorted(table_cols[target_table]))}."
                    if best:
                        table_hint += f" Did you mean '{best}'? Use '{target_table}.{best}'."
                else:
                    for t in table_cols:
                        if t in sql.upper():
                            best = _find_best_column_match(bad_col, table_cols[t], t)
                            if best:
                                table_hint += f" Did you mean '{t}.{best}'? Available columns in '{t}': {', '.join(sorted(table_cols[t]))}."
                                break
                error_diagnostic = f"Database Error: ORA-00904 invalid identifier '{bad_col}'.{table_hint} Never invent column names."
            elif "ORA-00942" in raw_err.upper():
                error_diagnostic = f"Database Error: ORA-00942 table does not exist. Available tables in schema are: {', '.join(sorted(table_cols.keys()))}. Do not invent tables."

            if attempt < max_retries:
                sql, explanation, retry_tokens = llm_service.fix_sql(
                    prompt_nl, sql, error_diagnostic, schema_context, db_conn.connection_type,
                )
                query_record.generated_sql = sql
                query_record.explanation = explanation
                query_record.tokens_used = (query_record.tokens_used or 0) + (retry_tokens or 0)
                db.commit()
                if sql.startswith("ERROR:"):
                    break
            else:
                query_record.status = "failed"
                query_record.error_message = friendly_error(raw_err)
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
    db_conn = get_database(
        db, data.database_id, user_id=user_id,
        include_all=_user_has_manage_permission(db, user_id),
    )
    user = db.query(User).filter(User.id == user_id).first()
    company_id = db_conn.company_id or (user.company_id if user else None)

    query_record = Query(
        user_id=user_id,
        company_id=company_id,
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
    valid_types = {"bar_chart", "line_chart", "pie_chart", "table", "kpi", "scatter_plot", "area_chart", "heatmap", "histogram"}
    normalized = []
    for s in suggestions:
        v_type = s.get("type", "table")
        if v_type not in valid_types:
            if "kpi" in v_type:
                v_type = "kpi"
            elif "bar" in v_type:
                v_type = "bar_chart"
            elif "line" in v_type:
                v_type = "line_chart"
            elif "pie" in v_type:
                v_type = "pie_chart"
            else:
                v_type = "table"
        normalized.append(VisualizationSuggestion(
            type=v_type,
            title=s.get("title"),
            config=s.get("config"),
        ))
    return normalized
