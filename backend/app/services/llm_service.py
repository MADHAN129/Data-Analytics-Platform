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
        self.use_mock = settings.LLM_USE_MOCK
        self._client: Optional[httpx.Client] = None
        self._mock_cache = {}

    @property
    def client(self) -> Optional[httpx.Client]:
        if self._client is None and not self.use_mock:
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
        return f"""You are a data analysis assistant that converts natural language questions into {dialect} SQL.

DATABASE SCHEMA (only these tables and columns exist):
{schema_context}

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

    def _fixup_sql(self, raw: str) -> str:
        if not raw or not raw.strip():
            return ""
        raw = raw.strip()
        raw = re.sub(r"^```(?:sql|json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        raw = re.sub(r"\n+", "\n", raw).strip()
        raw = raw.rstrip(";") + ";"
        return raw

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

    def fix_sql(self, natural_language: str, sql: str, error: str, schema_context: str, connection_type: str) -> tuple[str, str, int]:
        dialect = self._get_db_dialect(connection_type)
        if self.use_mock:
            return self._fallback_generate_sql(natural_language, dialect, schema_context)
        system_prompt = self._build_schema_prompt(schema_context, dialect)
        fix_prompt = (
            f"The SQL query below failed with an error. Please fix it and return ONLY the corrected SQL.\n\n"
            f"Original question: {natural_language}\n\n"
            f"Failed SQL:\n{sql}\n\n"
            f"Error:\n{error}\n\n"
            f"IMPORTANT: Only use table and column names from the schema above. "
            f"The most likely cause of this error is a wrong table or column name.\n\n"
            f"Return ONLY the corrected raw SQL. No markdown, no explanations."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": fix_prompt},
        ]
        raw = self._call_vllm(messages, temperature=0.1)
        if raw is None or raw.startswith("ERROR:") or not raw.strip():
            return self._fallback_generate_sql(natural_language, dialect, schema_context)
        fixed_sql = self._fixup_sql(raw)
        tokens = self._estimate_tokens(natural_language, fixed_sql)
        explanation_messages = [
            {"role": "system", "content": "Explain the SQL query briefly in 1-2 sentences. Be concise."},
            {"role": "user", "content": f"Question: {natural_language}\nSQL: {fixed_sql}"},
        ]
        explanation_raw = self._call_vllm(explanation_messages, temperature=0, max_tokens=256)
        explanation = explanation_raw if explanation_raw else self._fallback_explain(natural_language, fixed_sql)
        return fixed_sql, explanation, tokens

    def generate_sql(self, natural_language: str, schema_context: str, connection_type: str) -> tuple[str, str, int]:
        dialect = self._get_db_dialect(connection_type)

        if self.use_mock:
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        system_prompt = self._build_schema_prompt(schema_context, dialect)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": natural_language},
        ]

        raw = self._call_vllm(messages, temperature=0.1)
        if raw is None:
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        if raw.startswith("ERROR:"):
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        if raw.startswith("GREETING:"):
            greeting = raw[len("GREETING:"):].strip()
            return "SELECT 1;", greeting, 2

        if not raw.strip():
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        sql = self._fixup_sql(raw)
        tokens = self._estimate_tokens(natural_language, sql)

        if self._is_sql_hallucinated(sql, schema_context):
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        explanation_messages = [
            {"role": "system", "content": "Explain the SQL query briefly in 1-2 sentences. Be concise."},
            {"role": "user", "content": f"Question: {natural_language}\nSQL: {sql}"},
        ]
        explanation_raw = self._call_vllm(explanation_messages, temperature=0, max_tokens=256)
        explanation = explanation_raw if explanation_raw else self._fallback_explain(natural_language, sql)

        return sql, explanation, tokens

    def explain_sql(self, sql: str, natural_language: str) -> str:
        if self.use_mock:
            return self._fallback_explain(natural_language, sql)
        messages = [
            {"role": "system", "content": "Explain the SQL query briefly in 1-2 sentences. Be concise."},
            {"role": "user", "content": f"Question: {natural_language}\nSQL: {sql}"},
        ]
        raw = self._call_vllm(messages, temperature=0, max_tokens=256)
        return raw if raw else self._fallback_explain(natural_language, sql)

    def optimize_query(self, sql: str) -> list[dict]:
        if self.use_mock:
            return self._fallback_optimize(sql)
        messages = [
            {"role": "system", "content": "You are a SQL optimization expert. Analyze the SQL and return a JSON array of optimization suggestions. Each suggestion has fields: type, description, impact (high/medium/low). Return valid JSON only, no markdown."},
            {"role": "user", "content": f"Optimize this SQL:\n{sql}"},
        ]
        raw = self._call_vllm(messages, temperature=0, max_tokens=512)
        if raw:
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)
            try:
                suggestions = json.loads(raw)
                if isinstance(suggestions, list):
                    return suggestions
            except (json.JSONDecodeError, TypeError):
                pass
        return self._fallback_optimize(sql)

    def suggest_visualizations(self, columns: list[str]) -> list[dict]:
        suggestions = []
        if len(columns) >= 2:
            suggestions.append({
                "type": "bar_chart",
                "title": f"{columns[0]} by {columns[1]}",
                "config": {"x": columns[1], "y": columns[0], "sort": "desc"},
            })
            suggestions.append({
                "type": "pie_chart",
                "title": f"{columns[0]} distribution",
                "config": {"label": columns[1], "value": columns[0]},
            })
        if len(columns) >= 1:
            suggestions.append({"type": "table", "title": "Data Table", "config": {}})
        return suggestions

    # -- fallback / mock methods (used when vLLM is unavailable) --

    def _estimate_tokens(self, nl: str, sql: str) -> int:
        return len(nl.split()) * 3 + len(sql.split()) * 2

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


llm_service = LLMService()
