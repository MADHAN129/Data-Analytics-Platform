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

    def _build_schema_prompt(self, schema_context: str, dialect: str) -> str:
        dialect_rules = ""
        if dialect == "Oracle SQL":
            dialect_rules = """
- ORACLE SQL SYNTAX RULES:
  * NEVER use the 'AS' keyword for table aliases (write 'FROM EMPLOYEES T1', NOT 'FROM EMPLOYEES AS T1').
  * NEVER use LIMIT. Use 'FETCH FIRST n ROWS ONLY' to limit rows.
  * String concatenation uses || (e.g. FIRST_NAME || ' ' || LAST_NAME).
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

        return f"""You are an expert SQL engineer. Given a database schema and a natural language user question, generate a single valid {dialect} query that accurately answers the question.

DATABASE CONTEXT AND SCHEMA:
{schema_context}

RULES:
1. ONLY reference tables and columns that exist in the schema above.
2. Join related tables using foreign keys and primary keys when answering questions spanning multiple entities.
3. Ensure all non-aggregate selected columns are included in GROUP BY when computing aggregations.
4. Use proper {dialect} syntax:{dialect_rules}
5. Add a reasonable row limit clause (e.g. FETCH FIRST 20 ROWS ONLY for Oracle, TOP 20 for SQL Server, LIMIT 20 for PostgreSQL/MySQL) if querying multiple rows.
6. Return ONLY the raw SQL query. Do NOT include markdown code blocks, backticks, or explanatory text."""

    def _fixup_sql(self, raw: str, dialect: str = "") -> str:
        if not raw or not raw.strip():
            return ""
        raw = raw.strip()

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
            sql = sql_match.group(0).strip() if sql_match else raw

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
            m_limit = re.search(r"\bLIMIT\s+(\d+)\s*;?$", sql, flags=re.IGNORECASE)
            if m_limit:
                limit_num = m_limit.group(1)
                sql = re.sub(r"\bLIMIT\s+\d+\s*;?$", f"FETCH FIRST {limit_num} ROWS ONLY;", sql, flags=re.IGNORECASE)
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

        sql = self._fixup_sql(raw, dialect)
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
            f"The following {dialect} query failed with a database execution error.\n\n"
            f"User Question: {natural_language}\n\n"
            f"Failed SQL:\n{sql}\n\n"
            f"Database Error:\n{error}\n\n"
            f"Please correct the query using the available schema and return ONLY the corrected raw SQL query."
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
                {"type": "kpi_card", "title": title_text, "config": {"metric": columns[0]}},
                {"type": "table", "title": "Data Table", "config": {}},
            ]

        # 2. Single detail record with multiple columns
        if row_count == 1:
            return [{"type": "table", "title": "Record Details", "config": {}}]

        # 3. No numeric metrics (pure tabular text)
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


llm_service = LLMService()
