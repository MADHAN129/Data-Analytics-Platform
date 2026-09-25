import json
import re
from typing import Optional

import httpx

from app.config import settings
from app.services.mcp_client import mcp_client


class LLMService:
    def __init__(self):
        self.model_name = settings.LLM_MODEL
        self.api_url = settings.VLLM_API_URL
        self.api_key = settings.VLLM_API_KEY or "not-needed"
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> Optional[httpx.Client]:
        if self._client is None:
            try:
                self._client = httpx.Client(
                    base_url=self.api_url,
                    timeout=httpx.Timeout(120.0, connect=10.0),
                )
            except Exception:
                self._client = None
        return self._client

    def _get_db_dialect(self, connection_type: str) -> str:
        dialect_map = {
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "mariadb": "MySQL",
            "sqlserver": "SQL Server",
            "mongodb": "MongoDB (NoSQL)",
            "oracle": "Oracle SQL",
        }
        return dialect_map.get(connection_type, "SQL")

    def _call_vllm(self, messages: list, temperature: float = 0.1, max_tokens: int = 1024) -> Optional[str]:
        client = self.client
        if client is None:
            return None
        try:
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {"Content-Type": "application/json"}
            if self.api_key and self.api_key != "not-needed":
                headers["Authorization"] = f"Bearer {self.api_key}"

            resp = client.post("/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content
        except Exception:
            self._client = None
            return None

    def _table_names_from_schema(self, schema_context: str) -> list[str]:
        lines = [line.strip() for line in schema_context.split("\n") if line.strip()]
        tables = []
        for line in lines:
            m = re.match(r"Table:\s*(\S+)", line)
            if m:
                tables.append(m.group(1))
        return tables

    def _has_table_in_schema(self, name: str, schema_context: str) -> bool:
        tables = self._table_names_from_schema(schema_context)
        return any(t.lower() == name.lower() for t in tables)

    def _build_schema_prompt(self, schema_context: str, dialect: str) -> str:
<<<<<<< HEAD
        return f"""You are a data analysis assistant that converts natural language questions into {dialect} SQL.
=======
        dialect_rules = ""
        if dialect == "Oracle SQL":
            dialect_rules = """
- ORACLE SQL SYNTAX RULES:
  * NEVER use the 'AS' keyword for table aliases (write 'FROM table_name t', NOT 'FROM table_name AS t').
  * NEVER use LIMIT. Use 'FETCH FIRST n ROWS ONLY' to limit rows.
  * String concatenation uses || (e.g. col1 || ' ' || col2).
  * In GROUP BY queries, every column in the SELECT clause that is not an aggregate function (SUM, AVG, COUNT, etc.) MUST appear in the GROUP BY clause."""
        elif dialect == "SQL Server":
            dialect_rules = """
- SQL SERVER SYNTAX RULES:
  * Use 'SELECT TOP n' to limit rows instead of LIMIT.
  * String concatenation uses +."""
        elif dialect == "PostgreSQL":
            dialect_rules = """
- POSTGRESQL SYNTAX RULES:
  * String concatenation uses || or CONCAT().
  * Use LIMIT n to limit rows."""
        elif dialect == "MySQL":
            dialect_rules = """
- MYSQL SYNTAX RULES:
  * String concatenation uses CONCAT().
  * Use LIMIT n to limit rows."""
>>>>>>> origin/main

        return f"""You are an expert SQL engineer. Given a database schema and a natural language user question, generate a single valid {dialect} query that accurately answers the question.

DATABASE CONTEXT AND SCHEMA:
{schema_context}

<<<<<<< HEAD
EXAMPLES OF CORRECT SQL:
Question: "sales per day"
Schema: orders (order_date (date), total_amount (numeric))
SQL: SELECT order_date, SUM(total_amount) FROM orders GROUP BY order_date ORDER BY order_date

Question: "most ordered items"
Schema: order_items (menu_item_id (int), quantity (int)), menu_items (id (int), name (text))
SQL: SELECT menu_items.name, SUM(order_items.quantity) AS total FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id GROUP BY menu_items.name ORDER BY total DESC

Question: "hello"
Schema: orders (id (int))
Response: GREETING: Hello! I can help you query your database. What would you like to know?

RULES:
- If the user is just greeting you (hi, hello, hey), start your response with GREETING: followed by a friendly message.
- If you cannot find a matching table or column for the question, start with ERROR: No matching table
- For data questions, return ONLY raw SQL — no markdown fences, no backticks, no explanations.
- ONLY use table names and column names that APPEAR in the schema above. NEVER invent columns.
- Use proper {dialect} syntax. Add a LIMIT clause when results may be many rows.
- If the question is ambiguous, choose the most reasonable columns.
- Add a descriptive label (AS name_column) for computed columns."""
=======
CRITICAL RULES FOR SQL GENERATION:
1. STRICT COLUMN GROUNDING: Every column you reference in SELECT, JOIN, WHERE, GROUP BY, or ORDER BY MUST exist under that specific table in the schema above.
   - NEVER invent non-existent column names (e.g. do NOT write 'project_spending', 'total_employee_salary_cost', 'employee_count', 'average_salary').
   - Use the actual column names from the schema: e.g. in table PROJECTS the spending column is 'SPENT', budget is 'BUDGET'. In EMPLOYEES salary is 'SALARY'.
2. SINGLE TABLE COMPLETENESS: If all required metrics and columns exist in a single table (e.g. both SPENT and BUDGET are in table PROJECTS), query ONLY that table. Do NOT join other tables unnecessarily.
3. PRE-AGGREGATE FIRST, THEN JOIN (ROW MULTIPLICATION / FAN-OUT PREVENTION):
   - When a question involves multiple child tables that each have a one-to-many relationship to the same parent table (e.g. EMPLOYEES has many employees per department, and PROJECTS has many projects per department):
     NEVER join multiple child tables directly in a single FROM clause before aggregation! (e.g. 5 employees * 2 projects produces 10 rows, multiplying salaries and spending!).
     Instead, you MUST pre-aggregate each child table independently in a CTE (WITH clause) or subquery grouped by the parent key (department_id), and then join the aggregated totals to the parent table.
4. NO SELECT ALIASES IN HAVING OR WHERE (ORACLE SQL):
   - In Oracle SQL, column aliases defined in SELECT (e.g. `AS total_spent`) CANNOT be referenced in HAVING or WHERE clauses.
   - Instead, wrap the query in a CTE (WITH clause) or subquery, and filter in the outer WHERE clause:
     `WITH dept_totals AS (SELECT d.department_name, NVL(e.total_salary, 0) AS total_salary, NVL(p.total_spent, 0) AS total_spent FROM ...) SELECT * FROM dept_totals WHERE total_spent > total_salary;`
5. FILTERING BY ENTITY OR CATEGORY NAMES: When the user question mentions an entity name or category (e.g. 'Engineering', 'Q2', 'Completed'):
   - Look at the [Sample Values] in the schema to find which table and column holds that value (e.g. DEPARTMENTS.DEPARTMENT_NAME contains 'Engineering').
   - You MUST include a WHERE clause filtering on that column: e.g. `WHERE D.DEPARTMENT_NAME = 'Engineering'`.
   - If querying a related table (e.g. EMPLOYEES), JOIN the parent table on the foreign key relationship:
     `SELECT AVG(E.SALARY) FROM EMPLOYEES E JOIN DEPARTMENTS D ON E.DEPARTMENT_ID = D.DEPARTMENT_ID WHERE D.DEPARTMENT_NAME = 'Engineering';`
6. 'WHO', 'WHICH', AND RANKING QUESTIONS:
   - When asked 'Who ...' (e.g. 'Who has highest salary?', 'Who is the top sales rep?'): SELECT the person's identity (`FIRST_NAME || ' ' || LAST_NAME AS FULL_NAME`) together with the metric, and use `ORDER BY <metric> DESC FETCH FIRST 1 ROWS ONLY`.
   - When asked 'Which department...', 'Which project...', or 'Which quarter...': SELECT the entity name (`DEPARTMENT_NAME`, `PROJECT_NAME`, `QUARTER`, etc.) together with the metric, and `ORDER BY <metric> DESC FETCH FIRST 1 ROWS ONLY`.
7. INDEPENDENT TABLES & MULTI-METRIC CTEs: Independent tables that have no foreign key relationship to other tables (such as company-wide financial tables) must NOT be joined directly in a single FROM clause. Compute each metric in its own Common Table Expression (WITH clause) using FETCH FIRST 1 ROWS ONLY and combine the single-row CTEs using CROSS JOIN.
8. AGGREGATIONS & GROUP BY: All non-aggregated columns in SELECT must appear in GROUP BY.
9. SYNTAX & DIALECT:{dialect_rules}
10. ROW LIMIT: Include FETCH FIRST 20 ROWS ONLY for multi-row queries unless answering a top 1 ranking question.

INTENT & RELEVANCE RULES:
1. UNRELATED QUESTIONS: If the user question is completely unrelated to the available tables and columns in the schema (such as general knowledge, weather, movies, sports, recipes, or outside domains not in the schema), do NOT generate any SQL query. Output strictly:
   UNRELATED: The connected database does not contain information to answer this question.
2. AMBIGUOUS QUESTIONS: If the user asks a question with subjective or undefined criteria (e.g. 'Who is the best?', 'Which is greatest?') with no specified metric, do NOT guess. Output strictly:
   AMBIGUOUS: The question is ambiguous. Please clarify which metric you would like to evaluate (e.g., salary, revenue, budget, performance).
3. VALID DATABASE QUESTIONS: Generate a single valid {dialect} query that accurately answers the question. Output your query strictly inside a ```sql ... ``` code block. Return ONLY the ```sql ... ``` block without explanation or conversational text."""
>>>>>>> origin/main

    def _fixup_sql(self, raw: str, dialect: str = "") -> str:
        if not raw or not raw.strip():
            return ""
        raw = raw.strip()

<<<<<<< HEAD
    def _is_sql_hallucinated(self, sql: str, schema_context: str) -> bool:
        if not sql or sql.strip() in (";", ""):
            return True
        nl = sql.lower().strip()
        if nl.startswith("greeting:") or nl.startswith("error:"):
            return False
        if "information_schema.tables" in nl or "information_schema.columns" in nl or "information_schema.schemata" in nl:
            return True
        table_markers = ["table:", " tables ", " columns "]
        marker_count = sum(1 for m in table_markers if m in nl)
        ctx_markers = ["(character varying)", "(integer)", "(timestamp", "(jsonb)", "(boolean)"]
        ctx_count = sum(1 for m in ctx_markers if m in nl)
        if marker_count >= 3 or ctx_count >= 3:
            return True
        if "select table_name from" in nl or "select column_name from" in nl:
            return True
        return False
=======
        # 1. Search for markdown code block anywhere in the text
        match = re.search(r"```(?:sql|json)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
        else:
            # 2. Extract starting from the first SQL keyword
            sql_match = re.search(
                r"\b(WITH\s+[a-zA-Z0-9_]+\s+AS|SELECT\b|INSERT\s+INTO|UPDATE\b|DELETE\s+FROM|SHOW\b|DESCRIBE\b)[\s\S]*",
                raw,
                flags=re.IGNORECASE,
            )
            sql = sql_match.group(0).strip() if sql_match else ""
>>>>>>> origin/main

        if not sql:
            return ""

        # 3. Strip any conversational text after the ending semicolon
        if ";" in sql:
            parts = sql.split(";")
            for p in parts:
                if p.strip():
                    sql = p.strip()
                    break

        sql = re.sub(r"\n+", "\n", sql).strip()
        sql = sql.rstrip(";") + ";"

        if dialect == "Oracle SQL":
            # Sanitize Oracle table aliases: Oracle does not accept 'FROM table AS alias'
            sql = re.sub(r"\b(FROM|JOIN)\s+([a-zA-Z0-9_]+)\s+AS\s+([a-zA-Z0-9_]+)\b", r"\1 \2 \3", sql, flags=re.IGNORECASE)
            # Replace LIMIT with FETCH FIRST n ROWS ONLY
            sql = re.sub(r"\bLIMIT\s+(\d+)\s*;?$", r"FETCH FIRST \1 ROWS ONLY;", sql, flags=re.IGNORECASE)
            # Normalize FETCH FIRST 1 ROW ONLY to FETCH FIRST 1 ROWS ONLY
            sql = re.sub(r"\bFETCH\s+FIRST\s+(\d+)\s+ROW\s+ONLY", r"FETCH FIRST \1 ROWS ONLY", sql, flags=re.IGNORECASE)
        return sql

    def _estimate_tokens(self, nl: str, sql: str) -> int:
        return len(nl.split()) * 3 + len(sql.split()) * 2

    def generate_sql(self, natural_language: str, schema_context: str, connection_type: str) -> tuple[str, str, int]:
        dialect = self._get_db_dialect(connection_type)
        system_prompt = self._build_schema_prompt(schema_context, dialect)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": natural_language},
        ]

        raw = self._call_vllm(messages, temperature=0.1)
        if not raw or raw.strip().startswith("ERROR:"):
            return "", "The AI model was unable to generate a SQL query for this question.", 0

        raw_trimmed = raw.strip()
        if raw_trimmed.startswith("UNRELATED:"):
            msg = raw_trimmed[len("UNRELATED:"):].strip()
            return "UNRELATED", msg, self._estimate_tokens(natural_language, msg)
        if raw_trimmed.startswith("AMBIGUOUS:"):
            msg = raw_trimmed[len("AMBIGUOUS:"):].strip()
            return "AMBIGUOUS", msg, self._estimate_tokens(natural_language, msg)

<<<<<<< HEAD
        if raw.startswith("GREETING:"):
            greeting = raw[len("GREETING:"):].strip()
            return "SELECT 1;", greeting, 2

        if not raw.strip():
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        sql = self._fixup_sql(raw)
=======
        sql = self._fixup_sql(raw, dialect)
>>>>>>> origin/main
        tokens = self._estimate_tokens(natural_language, sql)

        # Ask the LLM to explain the generated SQL
        explanation_messages = [
            {"role": "system", "content": "You are a database assistant. Explain what the following SQL query does in 1-2 concise, clear sentences."},
            {"role": "user", "content": f"User question: {natural_language}\nGenerated SQL:\n{sql}"},
        ]
        explanation_raw = self._call_vllm(explanation_messages, temperature=0.1, max_tokens=256)
        explanation = explanation_raw.strip() if explanation_raw else f"Executes query for: {natural_language}"

        return sql, explanation, tokens

    def fix_sql(self, natural_language: str, sql: str, error: str, schema_context: str, connection_type: str) -> tuple[str, str, int]:
        dialect = self._get_db_dialect(connection_type)
        system_prompt = self._build_schema_prompt(schema_context, dialect)
        fix_prompt = (
            f"The following {dialect} query failed with a database error.\n\n"
            f"User Question: {natural_language}\n\n"
            f"Failed SQL:\n{sql}\n\n"
            f"Database Error:\n{error}\n\n"
            f"INSTRUCTIONS TO FIX DYNAMICALLY:\n"
            f"1. Understand what caused the error (e.g. ORA-00904 = column does not exist, ORA-00918 = ambiguous column, ORA-00937 = non-aggregated column in SELECT missing from GROUP BY).\n"
            f"2. Inspect the schema context above to find the exact table and column names.\n"
            f"3. Regenerate the corrected query using ONLY tables and columns verified in the schema.\n"
            f"4. Return ONLY the corrected raw SQL query without conversational text."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": fix_prompt},
        ]
        raw = self._call_vllm(messages, temperature=0.1)
        if not raw or raw.strip().startswith("ERROR:"):
            return sql, f"Query execution failed: {error}", 0

        fixed_sql = self._fixup_sql(raw, dialect)
        tokens = self._estimate_tokens(natural_language, fixed_sql)

        explanation_messages = [
            {"role": "system", "content": "Explain briefly in 1-2 sentences what correction was made to fix the query error."},
            {"role": "user", "content": f"Question: {natural_language}\nFixed SQL:\n{fixed_sql}\nPrevious Error:\n{error}"},
        ]
        explanation_raw = self._call_vllm(explanation_messages, temperature=0.1, max_tokens=256)
        explanation = explanation_raw.strip() if explanation_raw else f"Corrected SQL to resolve: {error}"

        return fixed_sql, explanation, tokens

    def explain_sql(self, sql: str, natural_language: str) -> str:
        messages = [
            {"role": "system", "content": "You are a database assistant. Explain what the SQL query does in 1-2 concise sentences."},
            {"role": "user", "content": f"Question: {natural_language}\nSQL:\n{sql}"},
        ]
        raw = self._call_vllm(messages, temperature=0.1, max_tokens=256)
        return raw.strip() if raw else "Executes the specified SQL query."

    def optimize_query(self, sql: str) -> list[dict]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a database performance expert. Analyze the SQL query and provide performance optimization suggestions. "
                    "Return ONLY a valid JSON array of objects with keys: 'type' (string), 'description' (string), 'impact' ('high'|'medium'|'low'). "
                    "Do NOT wrap with backticks or markdown."
                ),
            },
            {"role": "user", "content": f"Analyze and optimize this SQL query:\n{sql}"},
        ]
        raw = self._call_vllm(messages, temperature=0.1, max_tokens=512)
        if raw:
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw).strip()
            try:
                suggestions = json.loads(raw)
                if isinstance(suggestions, list):
                    return suggestions
            except (json.JSONDecodeError, TypeError):
                pass
        return [{
            "type": "general",
            "description": "Ensure appropriate indexes exist on filtered and joined columns.",
            "impact": "medium",
        }]

    def suggest_visualizations(self, columns: list[str], rows: list[list] = None, natural_language: str = "") -> list[dict]:
        """
        Dynamically suggest appropriate visualizations based purely on data shape,
        column types, and values (no hardcoded query rules).
        """
        if not columns or not rows:
            return [{"type": "table", "title": "Data Table", "config": {}}]

        row_count = len(rows)

        def is_col_numeric(idx: int) -> bool:
            num_count = 0
            sample = rows[:20]
            for r in sample:
                if idx < len(r) and r[idx] is not None:
                    try:
                        float(r[idx])
                        num_count += 1
                    except (ValueError, TypeError):
                        pass
            return num_count >= min(len(sample), 1)

        num_indices = [i for i in range(len(columns)) if is_col_numeric(i)]
        text_indices = [i for i in range(len(columns)) if i not in num_indices]

        # 1. Single scalar number (e.g. single aggregate metric)
        if row_count == 1 and len(columns) == 1 and len(num_indices) == 1:
            title_text = columns[0].replace("_", " ").title()
            return [
                {"type": "kpi", "title": title_text, "config": {"metric": columns[0]}},
                {"type": "table", "title": "Data Table", "config": {}},
            ]

        # 2. Single detail record with label dimension and metric
        if row_count == 1 and num_indices and text_indices:
            dim_col = columns[text_indices[0]]
            metric_col = columns[num_indices[0]]
            y_label = metric_col.replace("_", " ").title()
            x_label = dim_col.replace("_", " ").title()
            return [
                {"type": "bar_chart", "title": f"{y_label} by {x_label}", "config": {"x": dim_col, "y": metric_col}},
                {"type": "table", "title": "Data Table", "config": {}},
            ]

        # 3. Single record with no numeric metrics
        if row_count == 1:
            return [{"type": "table", "title": "Record Details", "config": {}}]

        # 4. No numeric metrics (pure tabular text)
        if not num_indices:
            return [{"type": "table", "title": "Data Table", "config": {}}]

        # 4. Multi-row tabular dataset with numerical metrics
        suggestions = []
        metric_col = columns[num_indices[0]]
        dim_col = columns[text_indices[0]] if text_indices else columns[0]

        is_time_series = any(k in dim_col.lower() for k in ("date", "time", "month", "quarter", "year", "day"))
        y_label = metric_col.replace("_", " ").title()
        x_label = dim_col.replace("_", " ").title()

        if is_time_series:
            suggestions.append({
                "type": "line_chart",
                "title": f"{y_label} Trend by {x_label}",
                "config": {"x": dim_col, "y": metric_col, "sort": "asc"},
            })
            suggestions.append({
                "type": "area_chart",
                "title": f"{y_label} Area by {x_label}",
                "config": {"x": dim_col, "y": metric_col},
            })
        else:
            suggestions.append({
                "type": "bar_chart",
                "title": f"{y_label} by {x_label}",
                "config": {"x": dim_col, "y": metric_col, "sort": "desc"},
            })
            if row_count <= 10:
                suggestions.append({
                    "type": "pie_chart",
                    "title": f"{y_label} Distribution by {x_label}",
                    "config": {"label": dim_col, "value": metric_col},
                })

        suggestions.append({"type": "table", "title": "Data Table", "config": {}})
        return suggestions

    def synthesize_data_summary(self, natural_language: str, sql: str, columns: list[str], rows: list[list]) -> str:
        """
        Synthesize rich data insights and visualization label assessment directly from the executed query.
        """
        if not rows or not columns:
            return f"Query executed successfully, but returned 0 rows for question: '{natural_language}'."

        sample_rows = rows[:10]
        data_preview = f"Columns: {', '.join(columns)}\nTotal Rows: {len(rows)}\nSample Rows:\n" + "\n".join(str(r) for r in sample_rows)

<<<<<<< HEAD
    def _date_trunc_day(self, col: str, dialect: str) -> str:
        if dialect == "MySQL":
            return f"DATE({col})"
        if dialect == "SQL Server":
            return f"CAST({col} AS DATE)"
        return f"DATE_TRUNC('day', {col})"

    def _date_trunc_month(self, col: str, dialect: str) -> str:
        if dialect == "MySQL":
            return f"DATE_FORMAT({col}, '%Y-%m-01')"
        if dialect == "SQL Server":
            return f"DATEFROMPARTS(YEAR({col}), MONTH({col}), 1)"
        return f"DATE_TRUNC('month', {col})"

    def _current_date(self, dialect: str) -> str:
        if dialect == "MySQL":
            return "CURDATE()"
        if dialect == "SQL Server":
            return "GETDATE()"
        return "CURRENT_DATE"

    def _where_date_since(self, col: str, months: int, dialect: str) -> str:
        if dialect == "MySQL":
            return f"{col} >= {self._current_date(dialect)} - INTERVAL {months} MONTH"
        if dialect == "SQL Server":
            return f"{col} >= DATEADD(month, -{months}, GETDATE())"
        return f"{col} >= {self._current_date(dialect)} - INTERVAL '{months} months'"

    def _limit_clause(self, dialect: str) -> str:
        return "" if dialect == "SQL Server" else "LIMIT"

    def _apply_limit(self, sql: str, n: int, dialect: str) -> str:
        if dialect == "SQL Server":
            return re.sub(r"^SELECT\b", f"SELECT TOP {n}", sql, count=1)
        return f"{sql}\nLIMIT {n};"

    def _list_tables_sql(self, dialect: str, schema: str) -> str:
        if not schema or schema.startswith("Table:"):
            schema = "public"
        if dialect == "MySQL":
            return "SHOW TABLES;"
        if dialect == "SQL Server":
            schema_esc = schema.replace("'", "''")
            return f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema_esc}' AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME;"
        schema_esc = schema.replace("'", "''")
        return f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_esc}' AND table_type = 'BASE TABLE' ORDER BY table_name;"

    def _parse_schema(self, schema: str) -> dict[str, list[tuple[str, str]]]:
        result: dict[str, list[tuple[str, str]]] = {}
        for line in schema.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"Table:\s*(\S+)\s*\[(.+)\]", line)
            if m:
                table = m.group(1)
                cols_str = m.group(2)
                cols = []
                for part in cols_str.split(","):
                    part = part.strip()
                    cm = re.match(r"(\S+)\s*\((.+?)\)", part)
                    if cm:
                        cols.append((cm.group(1), cm.group(2)))
                    elif part:
                        cols.append((part, "unknown"))
                result[table] = cols
        return result

    def _find_date_col(self, cols: list[tuple[str, str]]) -> str:
        date_types = {"date", "datetime", "timestamp", "timestamptz", "timestamp without time zone", "timestamp with time zone"}
        for name, dtype in cols:
            if any(t in dtype.lower() for t in {"date", "timestamp"}):
                return name
        for name, _ in cols:
            if name in ("created_at", "updated_at", "order_date", "created_date", "date"):
                return name
        return cols[0][0] if cols else "created_at"

    def _find_numeric_col(self, cols: list[tuple[str, str]]) -> str:
        num_types = {"int", "integer", "bigint", "smallint", "numeric", "decimal", "float", "double", "real", "money"}
        for name, dtype in cols:
            dt = dtype.lower()
            if any(t in dt for t in num_types):
                return name
        for name, _ in cols:
            if name in ("total_amount", "amount", "total", "price", "revenue", "quantity", "cost"):
                return name
        return cols[0][0] if cols else "total_amount"

    def _find_table_col(self, schema_dict: dict, table: str, hint_type: str) -> str:
        for tname, cols in schema_dict.items():
            if tname.lower() == table.lower():
                if hint_type == "date":
                    return self._find_date_col(cols)
                if hint_type == "numeric":
                    return self._find_numeric_col(cols)
                return cols[0][0] if cols else "id"
        return table

    def _fallback_generate_sql(self, nl: str, dialect: str, schema: str) -> tuple[str, str, int]:
        nl_lower = nl.lower()
        trunc_day = self._date_trunc_day
        trunc_month = self._date_trunc_month
        since = self._where_date_since
        schema_dict = self._parse_schema(schema) if schema else {}

        has = lambda t: self._has_table_in_schema(t, schema) if schema else False

        # ── GREETINGS ─────────────────────────────────────────────────────
        if re.search(r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|what'?s?\s*up|howdy)\b", nl_lower):
            table_list = ", ".join(schema_dict.keys()) if schema_dict else "no tables"
            return "SELECT 1;", f"Hello! I can help you explore your database. Available tables: {table_list}. Try asking me something like 'Show me sales' or 'List users'.", 2

        # ── SALES REPORT (comprehensive: orders + items + menu) ─────────
        if (has("orders") or has("order_items")) and any(w in nl_lower for w in ["sale", "sales", "report", "revenue", "earning"]):
            if has("order_items") and has("menu_items"):
                od = self._find_table_col(schema_dict, "orders", "date") or "order_date"
                ta = self._find_table_col(schema_dict, "order_items", "numeric") or "quantity"
                month = trunc_month(f"o.{od}", dialect)
                sql = self._apply_limit(
                    f"SELECT {month} AS month, mi.name AS item, SUM(oi.{ta}) AS total_sold, SUM(oi.{ta} * mi.price) AS revenue\n"
                    f"FROM orders o\n"
                    f"JOIN order_items oi ON oi.order_id = o.id\n"
                    f"JOIN menu_items mi ON mi.id = oi.menu_item_id\n"
                    f"GROUP BY month, mi.name\n"
                    f"ORDER BY month DESC, revenue DESC",
                    50, dialect,
                )
                return sql, "Comprehensive sales report showing monthly sales by menu item, including quantity sold and revenue.", self._estimate_tokens(nl, sql)
            else:
                od = self._find_table_col(schema_dict, "orders", "date") or "order_date"
                ta = self._find_table_col(schema_dict, "orders", "numeric") or "total_amount"
                month = trunc_month(f"o.{od}", dialect)
                sql = self._apply_limit(
                    f"SELECT {month} AS month, SUM(o.{ta}) AS total_revenue, COUNT(o.id) AS order_count\n"
                    f"FROM orders o\n"
                    f"GROUP BY month\n"
                    f"ORDER BY month DESC",
                    24, dialect,
                )
                return sql, "Monthly revenue summary showing total sales and order count.", self._estimate_tokens(nl, sql)

        # ── MONTHLY SALES ───────────────────────────────────────────────
        if has("orders") and ("month" in nl_lower or "daily" in nl_lower):
            od = self._find_table_col(schema_dict, "orders", "date") or "order_date"
            ta = self._find_table_col(schema_dict, "orders", "numeric") or "total_amount"
            if "daily" in nl_lower:
                day = trunc_day(f"o.{od}", dialect)
                sql = self._apply_limit(
                    f"SELECT {day} AS day, SUM(o.{ta}) AS total_revenue, COUNT(o.id) AS order_count\n"
                    f"FROM orders o\n"
                    f"GROUP BY day\n"
                    f"ORDER BY day DESC",
                    30, dialect,
                )
                return sql, "Daily revenue breakdown with order counts.", self._estimate_tokens(nl, sql)
            else:
                month = trunc_month(f"o.{od}", dialect)
                since12 = since(f"o.{od}", 12, dialect)
                sql = self._apply_limit(
                    f"SELECT {month} AS month, SUM(o.{ta}) AS total_revenue, COUNT(o.id) AS order_count\n"
                    f"FROM orders o\n"
                    f"WHERE {since12}\n"
                    f"GROUP BY month\n"
                    f"ORDER BY month DESC",
                    24, dialect,
                )
                return sql, "Monthly revenue for the last 12 months.", self._estimate_tokens(nl, sql)

        # ── POPULAR / TOP SELLING ITEMS ────────────────────────────────
        if has("order_items") and has("menu_items") and any(w in nl_lower for w in ["popular", "top", "best", "selling", "favorite", "trend"]):
            sql = self._apply_limit(
                "SELECT mi.name AS menu_item, mi.category, SUM(oi.quantity) AS total_ordered, SUM(oi.quantity * mi.price) AS revenue\n"
                "FROM order_items oi\n"
                "JOIN menu_items mi ON mi.id = oi.menu_item_id\n"
                "GROUP BY mi.name, mi.category\n"
                "ORDER BY total_ordered DESC",
                20, dialect,
            )
            return sql, "Most popular menu items ranked by quantity ordered.", self._estimate_tokens(nl, sql)

        # ── TOTAL REVENUE / TOTAL SALES ─────────────────────────────────
        if has("orders") and any(w in nl_lower for w in ["total", "sum", "overall"]) and any(w in nl_lower for w in ["sale", "revenue", "earning", "amount"]):
            ta = self._find_table_col(schema_dict, "orders", "numeric") or "total_amount"
            sql = f"SELECT COUNT(id) AS total_orders, SUM({ta}) AS total_revenue FROM orders;"
            return sql, "Total orders and overall revenue.", self._estimate_tokens(nl, sql)

        # ── ORDERS ──────────────────────────────────────────────────────
        if has("orders") and any(w in nl_lower for w in ["order", "orders"]):
            od = self._find_table_col(schema_dict, "orders", "date") or "order_date"
            cols = [c[0] for c in schema_dict.get("orders", [])[:8]]
            col_str = ", ".join(cols)
            sql = self._apply_limit(
                f"SELECT {col_str} FROM orders ORDER BY {od} DESC",
                20, dialect,
            )
            return sql, "Recent orders sorted by date.", self._estimate_tokens(nl, sql)

        # ── USERS / CUSTOMERS ───────────────────────────────────────────
        if has("users") and any(w in nl_lower for w in ["user", "users", "customer", "customers", "member", "members", "person"]):
            if "count" in nl_lower or "how many" in nl_lower:
                sql = "SELECT COUNT(*) AS user_count FROM users;"
                return sql, "Total number of users in the database.", self._estimate_tokens(nl, sql)
            if "new" in nl_lower or "recent" in nl_lower or "signup" in nl_lower or "registration" in nl_lower:
                uc = self._find_table_col(schema_dict, "users", "date") or "created_at"
                sql = self._apply_limit(
                    f"SELECT id, email, full_name, {uc} AS joined_at FROM users ORDER BY {uc} DESC",
                    10, dialect,
                )
                return sql, "Most recently registered users.", self._estimate_tokens(nl, sql)
            if "active" in nl_lower or "login" in nl_lower:
                lc = self._find_table_col(schema_dict, "users", "date") or "last_login"
                if lc:
                    sql = self._apply_limit(
                        f"SELECT id, email, full_name, {lc} AS last_login FROM users WHERE {lc} IS NOT NULL ORDER BY {lc} DESC",
                        10, dialect,
                    )
                    return sql, "Users sorted by most recent login activity.", self._estimate_tokens(nl, sql)
            cols = [c[0] for c in schema_dict.get("users", [])[:8]]
            col_str = ", ".join(cols)
            sql = self._apply_limit(
                f"SELECT {col_str} FROM users ORDER BY id",
                20, dialect,
            )
            return sql, "List of all users in the system.", self._estimate_tokens(nl, sql)

        if re.search(r"this\s+month.*user|user.*this\s+month|current.*month.*user|user.*current.*month", nl_lower):
            dc = self._find_table_col(schema_dict, "users", "date") or "created_at"
            month_start = trunc_month(f"u.{dc}", dialect)
            today = self._current_date(dialect)
            this_month = trunc_month(today, dialect)
            sql = self._apply_limit(
                f"SELECT {month_start} AS signup_month, COUNT(u.id) AS user_count\nFROM users u\nWHERE {month_start} = {this_month}\nGROUP BY signup_month\nORDER BY signup_month DESC",
                10, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"last\s+(login|log\s+in|sign.in|access)", nl_lower):
            sql = self._apply_limit(
                "SELECT id, email, full_name, last_login\nFROM users\nWHERE last_login IS NOT NULL\nORDER BY last_login DESC",
                10, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"(daily.*active|dau|user.*rate|active.*user|login.*per.*day)", nl_lower):
            lc = self._find_table_col(schema_dict, "users", "date") or "last_login"
            day = trunc_day(f"u.{lc}", dialect)
            sql = self._apply_limit(
                f"SELECT {day} AS login_date, COUNT(DISTINCT u.id) AS active_users\nFROM users u\nWHERE u.{lc} IS NOT NULL\nGROUP BY login_date\nORDER BY login_date DESC",
                30, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"user.*signup|registration.*trend|new.*user.*(month|trend)", nl_lower):
            uc = self._find_table_col(schema_dict, "users", "date") or "created_at"
            month = trunc_month(f"u.{uc}", dialect)
            sql = self._apply_limit(
                f"SELECT {month} AS signup_month, COUNT(u.id) AS new_users\nFROM users u\nGROUP BY signup_month\nORDER BY signup_month DESC",
                12, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        # ── MENU ITEMS ──────────────────────────────────────────────────
        if has("menu_items") and any(w in nl_lower for w in ["menu", "item", "items", "food", "drink", "product", "price", "category"]):
            cols = [c[0] for c in schema_dict.get("menu_items", [])[:8]]
            col_str = ", ".join(cols)
            if "category" in nl_lower or "categor" in nl_lower:
                if "category" in [c[0] for c in schema_dict.get("menu_items", [])]:
                    sql = "SELECT category, COUNT(*) AS item_count FROM menu_items GROUP BY category ORDER BY category;"
                    return sql, "Menu items grouped by category.", self._estimate_tokens(nl, sql)
            if ("cheapest" in nl_lower or "cheap" in nl_lower or "lowest" in nl_lower or "price" in nl_lower) and any("price" in c[0].lower() for c in schema_dict.get("menu_items", [])):
                sql = self._apply_limit(f"SELECT {col_str} FROM menu_items ORDER BY price ASC", 10, dialect)
                return sql, f"Menu items sorted by price (lowest first).", self._estimate_tokens(nl, sql)
            sql = self._apply_limit(f"SELECT {col_str} FROM menu_items ORDER BY name", 50, dialect)
            return sql, "All menu items in the system.", self._estimate_tokens(nl, sql)

        # ── BILLS / PAYMENTS ────────────────────────────────────────────
        if has("bills") and any(w in nl_lower for w in ["bill", "bills", "payment", "payments", "invoice", "unpaid", "paid"]):
            cols = [c[0] for c in schema_dict.get("bills", [])[:8]]
            col_str = ", ".join(cols)
            if "unpaid" in nl_lower or "pending" in nl_lower:
                sql = self._apply_limit(
                    f"SELECT {col_str} FROM bills WHERE status = 'pending' OR paid_at IS NULL ORDER BY created_at DESC",
                    20, dialect,
                )
                return sql, "Unpaid/pending bills.", self._estimate_tokens(nl, sql)
            if "total" in nl_lower or "sum" in nl_lower:
                sql = "SELECT COUNT(*) AS total_bills, SUM(amount) AS total_amount FROM bills;"
                return sql, "Total bills and sum of all amounts.", self._estimate_tokens(nl, sql)
            sql = self._apply_limit(f"SELECT {col_str} FROM bills ORDER BY created_at DESC", 20, dialect)
            return sql, "Recent bills.", self._estimate_tokens(nl, sql)

        # ── ACTIVITY LOGS ───────────────────────────────────────────────
        if has("activity_logs") and any(w in nl_lower for w in ["activity", "log", "logs", "audit", "action", "event", "track"]):
            cols = [c[0] for c in schema_dict.get("activity_logs", [])[:8]]
            col_str = ", ".join(cols)
            if "user" in nl_lower:
                sql = self._apply_limit(
                    f"SELECT {col_str} FROM activity_logs WHERE user_id IS NOT NULL ORDER BY created_at DESC",
                    20, dialect,
                )
                return sql, "Recent user activity logs.", self._estimate_tokens(nl, sql)
            sql = self._apply_limit(f"SELECT {col_str} FROM activity_logs ORDER BY created_at DESC", 20, dialect)
            return sql, "Most recent activity log entries.", self._estimate_tokens(nl, sql)

        # ── USER SESSIONS ──────────────────────────────────────────────
        if has("user_sessions") and any(w in nl_lower for w in ["session", "sessions", "login", "online", "visit"]):
            cols = [c[0] for c in schema_dict.get("user_sessions", [])[:8]]
            col_str = ", ".join(cols)
            sql = self._apply_limit(f"SELECT {col_str} FROM user_sessions ORDER BY login_at DESC", 20, dialect)
            return sql, "Recent user session activity.", self._estimate_tokens(nl, sql)

        # ── GENERIC TABLE QUERY ─────────────────────────────────────────
        for tname, tcols in schema_dict.items():
            tname_lower = tname.lower()
            if re.search(rf"\b{re.escape(tname_lower)}\b", nl_lower):
                col_names = [c[0] for c in tcols[:8]]
                col_str = ", ".join(col_names)
                sql = self._apply_limit(f"SELECT {col_str} FROM {tname}", 20, dialect)
                return sql, f"Showing {tname} data.", self._estimate_tokens(nl, sql)

        # ── CATCH-ALL: intelligent fallback ─────────────────────────────
        if schema_dict:
            table_keywords = {
                "orders": ["order", "sale", "revenue", "amount", "total", "report", "spend", "purchase"],
                "users": ["user", "person", "people", "customer", "employee", "member"],
                "menu_items": ["menu", "item", "food", "drink", "price", "product"],
                "bills": ["bill", "payment", "paid", "invoice", "charge"],
                "activity_logs": ["log", "activity", "event", "action", "history"],
                "user_sessions": ["session", "login", "visit", "online"],
                "order_items": ["quantity", "product", "order detail"],
            }
            best_table = list(schema_dict.keys())[0]
            best_score = 0
            for tbl, keywords in table_keywords.items():
                if tbl in schema_dict:
                    score = sum(1 for kw in keywords if kw in nl_lower)
                    if score > best_score:
                        best_score = score
                        best_table = tbl
            cols = [c[0] for c in schema_dict[best_table][:6]]
            col_str = ", ".join(cols)
            sql = self._apply_limit(f"SELECT {col_str} FROM {best_table}", 20, dialect)
            return sql, f"Showing sample data from {best_table}. Try asking a more specific question.", self._estimate_tokens(nl, sql)

        fallback_sql = "SELECT 1;"
        return fallback_sql, self._fallback_explain(nl, fallback_sql), self._estimate_tokens(nl, fallback_sql)

    def _fallback_explain(self, nl: str, sql: str) -> str:
        nl_lower = nl.lower()
        if re.search(r"^(hi|hello|hey|good|what'?s?\s*up|howdy)", nl_lower):
            return "Greeting response."
        if re.search(r"sale|sales|report|revenue|earning", nl_lower):
            return "Shows sales and revenue data, broken down by period."
        if re.search(r"popular|top.*(item|selling|product)|best.*seller|favorite|trending", nl_lower):
            return "Shows most popular items ranked by order frequency or quantity."
        if re.search(r"this\s+month.*user|user.*this\s+month", nl_lower):
            return "Shows how many users signed up this month by grouping users whose creation date falls in the current calendar month."
        if re.search(r"daily.*active|dau|user.*rate", nl_lower):
            return "Shows daily active user counts based on login activity."
        if re.search(r"last\s+login|when.*last.*login", nl_lower):
            return "Shows each user's last login timestamp, sorted with the most recent first."
        if re.search(r"user.*signup|registration.*trend|new.*user", nl_lower):
            return "Groups users by signup month to show registration trends over time."
        if "count" in nl_lower and "user" in nl_lower:
            return "Counts the total number of users in the database."
        if "top" in nl_lower:
            return "Retrieves top results by aggregating and sorting in descending order."
        if "month" in nl_lower:
            return "Groups data by month, showing totals for each period."
        if re.search(r"menu|item|food|drink|product", nl_lower):
            return "Lists menu items and their details."
        if re.search(r"bill|payment|invoice", nl_lower):
            return "Shows billing and payment information."
        if re.search(r"activity|log|audit|event", nl_lower):
            return "Shows activity log entries sorted by recency."
        if re.search(r"session|login|visit", nl_lower):
            return "Shows user session information."
        return f"Executes the generated SQL to answer: \"{nl}\""

    def _fallback_optimize(self, sql: str) -> list[dict]:
        suggestions = []
        if "SELECT *" in sql:
            suggestions.append({
                "type": "select_star",
                "description": "Avoid SELECT *; specify only needed columns to reduce I/O.",
                "impact": "medium",
            })
        if "WHERE" in sql.upper():
            suggestions.append({
                "type": "missing_index",
                "description": "Consider indexes on WHERE columns for faster filtering.",
                "impact": "high",
            })
        if " JOIN " in sql.upper():
            suggestions.append({
                "type": "join_condition",
                "description": "Ensure join columns are indexed for better performance.",
                "impact": "high",
            })
        if "ORDER BY" in sql.upper() and "LIMIT" not in sql.upper() and "TOP" not in sql.upper():
            suggestions.append({
                "type": "missing_limit",
                "description": "Add LIMIT with ORDER BY to reduce sorting overhead.",
                "impact": "low",
            })
        suggestions.append({
            "type": "analyze",
            "description": "Run EXPLAIN ANALYZE to identify bottlenecks.",
            "impact": "medium",
        })
        return suggestions
=======
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert AI Database Analyst with live database tool access. "
                    "Analyze the query results returned from the database to answer the user's question. "
                    "Provide your response adhering to this format:\n\n"
                    "### 🎯 Direct Answer\n"
                    "State the direct answer clearly and concisely using the live database values.\n\n"
                    "### 📊 Key Calculated Values\n"
                    "List the specific metrics and calculated figures using proper formatting (currency $, percentages %, totals, commas).\n\n"
                    "### 💡 Insights & Explanation\n"
                    "Provide a brief 1-2 sentence analytical explanation of the findings and data limitations if any.\n\n"
                    "### 🛠️ Execution Trace & Details\n"
                    "- **Intent**: The analytical goal.\n"
                    "- **Tables & Columns Used**: Tables and columns from the executed query.\n"
                    "- **Validation**: Validated against live database records.\n"
                    "- **Visualizable Labels Assessment**: State whether chartable labels are present and recommend the best visualization type."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User Request: {natural_language}\n\n"
                    f"Executed SQL Query:\n{sql}\n\n"
                    f"Database Results Data:\n{data_preview}\n\n"
                    "Please provide the complete analysis and label assessment:"
                ),
            },
        ]
        summary = self._call_vllm(messages, temperature=0.2, max_tokens=700)
        return summary.strip() if summary else f"Query executed successfully ({len(rows)} rows returned)."
>>>>>>> origin/main


llm_service = LLMService()
