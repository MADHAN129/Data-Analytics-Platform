import json
import re
from typing import Optional

import httpx

from app.config import settings


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

    def _build_schema_prompt(self, schema_context: str, dialect: str) -> str:
        return f"""You are a SQL generation expert. Given a database schema and a user question, generate valid {dialect} SQL.

DATABASE SCHEMA:
{schema_context}

RULES:
- Only use tables and columns that exist in the schema above
- Return ONLY the raw SQL query — no markdown fences, no backticks, no explanations
- Use proper {dialect} syntax
- Add LIMIT clause (or TOP for SQL Server) if the result could have many rows
- Use table aliases where helpful
- For MongoDB, generate valid MongoDB aggregation pipeline JSON, not SQL
- If the question is ambiguous, choose the most reasonable interpretation
- If you cannot generate a valid query from the schema, respond with: ERROR: <reason>"""

    def _fixup_sql(self, raw: str) -> str:
        if not raw or not raw.strip():
            return ""
        raw = raw.strip()
        raw = re.sub(r"^```(?:sql|json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        raw = re.sub(r"\n+", "\n", raw).strip()
        raw = raw.rstrip(";") + ";"
        return raw

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

        if not raw.strip():
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        sql = self._fixup_sql(raw)
        tokens = self._estimate_tokens(natural_language, sql)

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
        if dialect == "MySQL":
            return "SHOW TABLES;"
        if dialect == "SQL Server":
            schema_esc = schema.replace("'", "''")
            return f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema_esc}' AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME;"
        schema_esc = schema.replace("'", "''")
        return f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_esc}' AND table_type = 'BASE TABLE' ORDER BY table_name;"

    def _fallback_generate_sql(self, nl: str, dialect: str, schema: str) -> tuple[str, str, int]:
        nl_lower = nl.lower()
        trunc_day = self._date_trunc_day
        trunc_month = self._date_trunc_month
        since = self._where_date_since

        if re.search(r"this\s+month.*user|user.*this\s+month|current.*month.*user|user.*current.*month", nl_lower):
            month_start = trunc_month("u.created_at", dialect)
            today = self._current_date(dialect)
            this_month = trunc_month(today, dialect)
            sql = self._apply_limit(
                f"SELECT {month_start} AS signup_month, COUNT(u.id) AS user_count\nFROM users u\nWHERE {month_start} = {this_month}\nGROUP BY signup_month\nORDER BY signup_month DESC",
                10, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"last\s+(login|log\s+in|sign.in|access)", nl_lower):
            sql = self._apply_limit(
                "SELECT id, name, email, last_login\nFROM users\nWHERE last_login IS NOT NULL\nORDER BY last_login DESC",
                10, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"daily.*active|dau|user.*rate|active.*user.*today|login.*today|login.*rate|login.*per.*day|rate.*login", nl_lower):
            day = trunc_day("u.last_login", dialect)
            sql = self._apply_limit(
                f"SELECT {day} AS login_date, COUNT(DISTINCT u.id) AS active_users\nFROM users u\nWHERE u.last_login IS NOT NULL\nGROUP BY login_date\nORDER BY login_date DESC",
                30, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"user.*login.*graph|login.*graph|login.*trend|user.*activity|login.*over.time", nl_lower):
            day = trunc_day("u.last_login", dialect)
            sql = self._apply_limit(
                f"SELECT {day} AS login_date, COUNT(DISTINCT u.id) AS active_users\nFROM users u\nWHERE u.last_login IS NOT NULL\nGROUP BY login_date\nORDER BY login_date DESC",
                30, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"user.*signup|registration.*trend|sign.up.*over.time|new.*user.*month|user.*growth", nl_lower):
            month = trunc_month("u.created_at", dialect)
            sql = self._apply_limit(
                f"SELECT {month} AS signup_month, COUNT(u.id) AS new_users\nFROM users u\nGROUP BY signup_month\nORDER BY signup_month DESC",
                12, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if "count" in nl_lower and "user" in nl_lower:
            sql = "SELECT COUNT(*) AS user_count FROM users;"
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if "top" in nl_lower and "customer" in nl_lower and "revenue" in nl_lower:
            sql = self._apply_limit(
                "SELECT c.customer_id, c.name, SUM(o.total_amount) AS revenue\nFROM customers c\nJOIN orders o ON c.customer_id = o.customer_id\nGROUP BY c.customer_id, c.name\nORDER BY revenue DESC",
                10, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if "month" in nl_lower and ("sale" in nl_lower or "order" in nl_lower or "revenue" in nl_lower):
            month = trunc_month("o.order_date", dialect)
            since12 = since("o.order_date", 12, dialect)
            sql = f"SELECT {month} AS month, SUM(o.total_amount) AS total\nFROM orders o\nWHERE {since12}\nGROUP BY month\nORDER BY month;"
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        fallback_sql = self._list_tables_sql(dialect, schema) if schema else "SELECT 1;"
        return fallback_sql, self._fallback_explain(nl, fallback_sql), self._estimate_tokens(nl, fallback_sql)

    def _fallback_explain(self, nl: str, sql: str) -> str:
        nl_lower = nl.lower()
        if re.search(r"this\s+month.*user|user.*this\s+month", nl_lower):
            return "Shows how many users signed up this month by grouping users whose creation date falls in the current calendar month."
        if re.search(r"daily.*active|dau|user.*rate", nl_lower):
            return "Shows daily active user counts based on login activity."
        if re.search(r"last\s+login|when.*last.*login", nl_lower):
            return "Shows each user's last login timestamp, sorted with the most recent first."
        if re.search(r"user.*signup|registration.*trend", nl_lower):
            return "Groups users by signup month to show registration trends over time."
        if "count" in nl_lower and "user" in nl_lower:
            return "Counts the total number of users in the database."
        if "top" in nl_lower:
            return "Retrieves top results by aggregating and sorting in descending order."
        if "month" in nl_lower:
            return "Groups data by month, showing totals for each period."
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
