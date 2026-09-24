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
  * NEVER use the 'AS' keyword for table aliases (write 'FROM EMPLOYEES T1', NOT 'FROM EMPLOYEES AS T1')
  * NEVER use LIMIT. Use 'FETCH FIRST n ROWS ONLY' to limit rows
  * Use 'SELECT 1 FROM DUAL;' for constant queries
  * String concatenation uses || (e.g. FIRST_NAME || ' ' || LAST_NAME)"""

        return f"""You are a SQL generation expert. Given a database schema and a user question, generate valid {dialect} SQL.

DATABASE SCHEMA (only these tables and columns exist):
{schema_context}

CRITICAL RULES - YOU MUST FOLLOW:
- ONLY use table names and column names that are listed in the schema above. NEVER guess column names.
- If you cannot find a matching table or column, respond with EXACTLY: ERROR: No matching table found for this question
- Return ONLY the raw SQL query — no markdown fences, no backticks, no explanations
- Use proper {dialect} syntax{dialect_rules}
- Add LIMIT clause (or TOP for SQL Server, or FETCH FIRST n ROWS ONLY for Oracle) if the result could have many rows
- Use table aliases where helpful
- For MongoDB, generate valid MongoDB aggregation pipeline JSON, not SQL
- If the question is ambiguous, choose the most reasonable interpretation
- Do NOT query information_schema. Do NOT embed schema text in your output."""

    def _fixup_sql(self, raw: str, dialect: str = "") -> str:
        if not raw or not raw.strip():
            return ""
        raw = raw.strip()
        raw = re.sub(r"^```(?:sql|json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        raw = re.sub(r"\n+", "\n", raw).strip()
        raw = raw.rstrip(";") + ";"

        if dialect == "Oracle SQL":
            # Remove AS keyword from table aliases (e.g. FROM table AS t -> FROM table t)
            raw = re.sub(r"\b(FROM|JOIN)\s+([a-zA-Z0-9_]+)\s+AS\s+([a-zA-Z0-9_]+)\b", r"\1 \2 \3", raw, flags=re.IGNORECASE)
            # Fix LIMIT in Oracle
            m_limit = re.search(r"\bLIMIT\s+(\d+)\s*;?$", raw, flags=re.IGNORECASE)
            if m_limit:
                limit_num = m_limit.group(1)
                raw = re.sub(r"\bLIMIT\s+\d+\s*;?$", f"FETCH FIRST {limit_num} ROWS ONLY;", raw, flags=re.IGNORECASE)
        return raw

    def _is_sql_hallucinated(self, sql: str, schema_context: str) -> bool:
        if not sql or sql.strip() in (";", ""):
            return True
        nl = sql.lower()
        table_markers = ["table:", " tables ", " columns "]
        marker_count = sum(1 for m in table_markers if m in nl)
        ctx_markers = ["(character varying)", "(integer)", "(timestamp", "(jsonb)", "(boolean)"]
        ctx_count = sum(1 for m in ctx_markers if m in nl)
        if marker_count >= 2 or ctx_count >= 2:
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
        fixed_sql = self._fixup_sql(raw, dialect)
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

        if not raw.strip():
            return self._fallback_generate_sql(natural_language, dialect, schema_context)

        sql = self._fixup_sql(raw, dialect)
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
        if dialect == "Oracle SQL":
            return f"TRUNC({col})"
        return f"DATE_TRUNC('day', {col})"

    def _date_trunc_month(self, col: str, dialect: str) -> str:
        if dialect == "MySQL":
            return f"DATE_FORMAT({col}, '%Y-%m-01')"
        if dialect == "SQL Server":
            return f"DATEFROMPARTS(YEAR({col}), MONTH({col}), 1)"
        if dialect == "Oracle SQL":
            return f"TRUNC({col}, 'MM')"
        return f"DATE_TRUNC('month', {col})"

    def _current_date(self, dialect: str) -> str:
        if dialect == "MySQL":
            return "CURDATE()"
        if dialect == "SQL Server":
            return "GETDATE()"
        if dialect == "Oracle SQL":
            return "SYSDATE"
        return "CURRENT_DATE"

    def _where_date_since(self, col: str, months: int, dialect: str) -> str:
        if dialect == "MySQL":
            return f"{col} >= {self._current_date(dialect)} - INTERVAL {months} MONTH"
        if dialect == "SQL Server":
            return f"{col} >= DATEADD(month, -{months}, GETDATE())"
        if dialect == "Oracle SQL":
            return f"{col} >= ADD_MONTHS(SYSDATE, -{months})"
        return f"{col} >= {self._current_date(dialect)} - INTERVAL '{months} months'"

    def _limit_clause(self, dialect: str) -> str:
        return "" if dialect == "SQL Server" else "LIMIT"

    def _apply_limit(self, sql: str, n: int, dialect: str) -> str:
        sql = sql.rstrip(";")
        if dialect == "SQL Server":
            return re.sub(r"^SELECT\b", f"SELECT TOP {n}", sql, count=1) + ";"
        if dialect == "Oracle SQL":
            return f"{sql}\nFETCH FIRST {n} ROWS ONLY;"
        if dialect == "MongoDB (NoSQL)":
            return sql
        return f"{sql}\nLIMIT {n};"

    def _list_tables_sql(self, dialect: str, schema: str = "") -> str:
        if dialect == "MySQL":
            return "SHOW TABLES;"
        if dialect == "SQL Server":
            return "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME;"
        if dialect == "Oracle SQL":
            return "SELECT table_name FROM user_tables ORDER BY table_name;"
        if dialect == "MongoDB (NoSQL)":
            return '{"listCollections": 1}'
        return "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;"

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
            if any(k in name.lower() for k in ("date", "time", "created", "updated", "login", "at")):
                return name
        return cols[0][0] if cols else "created_at"

    def _find_numeric_col(self, cols: list[tuple[str, str]]) -> str:
        num_types = {"int", "integer", "bigint", "smallint", "numeric", "decimal", "float", "double", "real", "money", "number"}
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

        # 1. Check for listing tables / schemas
        if re.search(r"\b(what|show|list|tell|all|display|get|which)\b.*\b(table|tables|all tables|tables availab|tables exist|tabels)\b|\btables\b", nl_lower):
            sql = self._list_tables_sql(dialect, schema)
            return sql, f"Lists all accessible tables in the {dialect} database.", self._estimate_tokens(nl, sql)

        # 2. Check for Entity / Phrase queries (e.g. "Ai Analytics Core Engine budget", "Liam Chen salary", "Acme Global Corp")
        stop_words = {
            "i", "need", "you", "to", "show", "give", "me", "what", "is", "are", "the", "a", "an",
            "name", "names", "of", "person", "persons", "people", "who", "whom", "whose", "which",
            "where", "tell", "about", "for", "in", "with", "and", "please", "fetch", "find", "get",
            "details", "info", "data", "how", "much", "many", "all", "each", "every", "list", "search",
            "check", "want", "would", "like", "see", "can"
        }
        metric_words = {"budget", "salary", "salaries", "revenue", "cost", "price", "spent", "profit", "expenses", "margin", "headcount", "performance", "rating"}
        query_words = [w for w in re.findall(r"[a-zA-Z0-9]+", nl_lower) if w not in stop_words and len(w) > 1]
        
        dept_keywords = {"department", "dept", "departments", "engineering", "human", "resources", "hr", "operations"}
        proj_keywords = {"project", "projects", "engine", "core", "migration", "cloud", "dashboard", "app", "mobile", "crm", "rollout", "sync", "portal", "talent", "erp", "module", "ai"}
        emp_keywords = {"employee", "employees", "staff", "developer", "engineer", "scientist", "manager", "director", "recruiter", "specialist", "architect"}
        sales_keywords = {"client", "customer", "customers", "license", "sale", "sales", "sold", "region", "territory", "acme", "starlight", "apex", "nordic", "pacific", "vertex", "quantum", "atlas", "zenith"}

        structural_words = {
            "department", "dept", "departments", "project", "projects", "sales", "sale",
            "employee", "employees", "details", "info", "data", "record", "records", "table",
            "tables", "list", "show", "count", "all", "total", "manager", "managers", "name",
            "names", "person", "persons", "who", "are", "the", "of", "to", "you"
        }
        
        entity_table = None
        entity_where = None
        best_entity_score = 0

        for tname, cols in schema_dict.items():
            tname_l = tname.lower()
            text_cols = [c[0] for c in cols if not c[0].lower().endswith(("_id", "id")) and any(k in c[0].lower() for k in ("name", "title", "client", "product", "dept", "city", "location", "category", "quarter", "status", "first", "last", "email"))]
            if not text_cols:
                text_cols = [c[0] for c in cols if any(t in c[1].lower() for t in ("char", "text", "str")) and not c[0].lower().endswith(("_id", "id"))]
            col_names_lower = [c[0].lower() for c in cols]

            # Check for composite first_name + last_name
            has_first_last = any("first_name" in cn for cn in col_names_lower) and any("last_name" in cn for cn in col_names_lower)

            for tcol in text_cols:
                col_l = tcol.lower()
                matched_words = [w for w in query_words if w not in metric_words and w not in structural_words]

                if matched_words:
                    score = len(matched_words) * 10
                    # Metric column bonus
                    for mw in metric_words:
                        if mw in query_words and any(mw in cn for cn in col_names_lower):
                            score += 25
                    
                    # Domain affinity bonus
                    if "project" in tname_l or "project" in col_l:
                        if any(w in proj_keywords for w in query_words):
                            score += 25
                    if "department" in tname_l or "dept" in col_l:
                        if any(w in dept_keywords for w in query_words):
                            score += 25
                    if "employee" in tname_l or "first_name" in col_l or "last_name" in col_l:
                        if any(w in emp_keywords for w in query_words):
                            score += 25
                    if "sales" in tname_l or "client" in col_l:
                        if any(w in sales_keywords for w in query_words):
                            score += 25

                    if any(k in col_l for k in ("project", "product", "client", "department", "name")):
                        score += 5
                    if any(w in tname_l for w in matched_words):
                        score += 8
                    
                    if score > best_entity_score and score >= 15:
                        best_entity_score = score
                        entity_table = tname
                        search_term = " ".join(matched_words[:4])
                        if has_first_last and ("employee" in tname_l or "first" in col_l or "last" in col_l):
                            fn = next(c[0] for c in cols if "first" in c[0].lower())
                            ln = next(c[0] for c in cols if "last" in c[0].lower())
                            if dialect in ("Oracle SQL", "PostgreSQL"):
                                entity_where = f"LOWER({fn} || ' ' || {ln}) LIKE '%{search_term}%'"
                            elif dialect == "SQL Server":
                                entity_where = f"LOWER({fn} + ' ' + {ln}) LIKE '%{search_term}%'"
                            else:
                                entity_where = f"LOWER(CONCAT({fn}, ' ', {ln})) LIKE '%{search_term}%'"
                        else:
                            entity_where = f"LOWER({tcol}) LIKE '%{search_term}%'"

        if entity_table and entity_where:
            base_sql = f"SELECT * FROM {entity_table}\nWHERE {entity_where}"
            sql = self._apply_limit(base_sql, 20, dialect)
            return sql, f"Retrieves matching records from '{entity_table}' for '{nl}'.", self._estimate_tokens(nl, sql)

        # 3. Check for matching specific table names or keywords in schema
        best_table = None
        best_score = 0
        best_cols = []
        words = set(re.findall(r"\w+", nl_lower))

        for tname, cols in schema_dict.items():
            tname_lower = tname.lower()
            score = 0
            if tname_lower in nl_lower:
                score += 15
            t_parts = tname_lower.split("_")
            for part in t_parts:
                if len(part) > 2 and (part in words or any(part in w or (len(w) > 3 and w in part) for w in words)):
                    score += 6
            for col_name, _ in cols:
                c_lower = col_name.lower()
                c_parts = c_lower.split("_")
                for cpart in c_parts:
                    if len(cpart) > 2 and (cpart in words or any(cpart in w or (len(w) > 3 and w in cpart) for w in words)):
                        score += 3
            if score > best_score:
                best_score = score
                best_table = tname
                best_cols = cols

        if best_table and best_score >= 3:
            tname = best_table
            is_count = bool(re.search(r"\b(count|how many|total count|number of)\b", nl_lower))
            is_sum = bool(re.search(r"\b(total|sum|revenue|sales|budget|spent|salary|salaries|profit)\b", nl_lower))
            
            group_col = None
            for cname, _ in best_cols:
                cn = cname.lower()
                if any(part in words for part in cn.split("_") if len(part) > 2):
                    if cn not in ("id", "salary", "budget", "spent", "revenue", "total_revenue", "net_profit", "operating_expenses", "units_sold", "unit_price"):
                        group_col = cname
                        break

            num_col = None
            for cname, dtype in best_cols:
                cn = cname.lower()
                if any(k in cn for k in ("revenue", "salary", "budget", "spent", "profit", "amount", "total", "cost")):
                    num_col = cname
                    break

            if is_count and not is_sum and not group_col:
                sql = f"SELECT COUNT(*) AS total_count FROM {tname};"
                return sql, f"Counts total records in '{tname}'.", self._estimate_tokens(nl, sql)
            elif is_sum and num_col and group_col:
                sql = self._apply_limit(
                    f"SELECT {group_col}, SUM({num_col}) AS total_{num_col.lower()}\nFROM {tname}\nGROUP BY {group_col}\nORDER BY total_{num_col.lower()} DESC",
                    20, dialect
                )
                return sql, f"Calculates total {num_col} grouped by {group_col} from '{tname}'.", self._estimate_tokens(nl, sql)
            else:
                base_sql = f"SELECT * FROM {tname}"
                sql = self._apply_limit(base_sql, 20, dialect)
                return sql, f"Retrieves records from table '{tname}'.", self._estimate_tokens(nl, sql)

        # 3. User activity / login templates
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
                "SELECT id, name, email, last_login\nFROM users\nWHERE last_login IS NOT NULL\nORDER BY last_login DESC",
                10, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"daily.*active|dau|user.*rate|active.*user.*today|login.*today|login.*rate|login.*per.*day|rate.*login", nl_lower):
            lc = self._find_table_col(schema_dict, "users", "date") or "last_login"
            day = trunc_day(f"u.{lc}", dialect)
            sql = self._apply_limit(
                f"SELECT {day} AS login_date, COUNT(DISTINCT u.id) AS active_users\nFROM users u\nWHERE u.{lc} IS NOT NULL\nGROUP BY login_date\nORDER BY login_date DESC",
                30, dialect,
            )
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        if re.search(r"user.*signup|registration.*trend|sign.up.*over.time|new.*user.*month|user.*growth", nl_lower):
            uc = self._find_table_col(schema_dict, "users", "date") or "created_at"
            month = trunc_month(f"u.{uc}", dialect)
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
            od = self._find_table_col(schema_dict, "orders", "date") or "order_date"
            ta = self._find_table_col(schema_dict, "orders", "numeric") or "total_amount"
            month = trunc_month(f"o.{od}", dialect)
            since12 = since(f"o.{od}", 12, dialect)
            sql = f"SELECT {month} AS month, SUM(o.{ta}) AS total\nFROM orders o\nWHERE {since12}\nGROUP BY month\nORDER BY month;"
            return sql, self._fallback_explain(nl, sql), self._estimate_tokens(nl, sql)

        lines = [line.strip() for line in schema.split("\n") if line.strip()]
        table_names = [line.split("[")[0].replace("Table:", "").strip() for line in lines]
        if table_names:
            first_table = table_names[0]
            base_sql = f"SELECT * FROM {first_table}"
            sql = self._apply_limit(base_sql, 10, dialect)
            return sql, f"Queries sample records from '{first_table}'. Available tables: {', '.join(table_names[:10])}", self._estimate_tokens(nl, sql)

        if dialect == "Oracle SQL":
            fallback_sql = "SELECT 1 FROM DUAL;"
        elif dialect == "MongoDB (NoSQL)":
            fallback_sql = "{}"
        else:
            fallback_sql = "SELECT 1;"
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
