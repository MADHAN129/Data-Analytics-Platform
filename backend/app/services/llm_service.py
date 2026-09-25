import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.config import settings
from app.services.mcp_client import mcp_client

logger = logging.getLogger(__name__)


@dataclass
class LLMProviderConfig:
    provider: str  # "openrouter", "grok", "local_proxy", "openai", "local", "mock"
    base_url: str
    api_key: str
    model: str
    headers: dict = field(default_factory=dict)
    timeout_seconds: float = 120.0


class LLMService:
    def __init__(self):
        self._clients: dict[str, httpx.Client] = {}

    @property
    def use_mock(self) -> bool:
        return getattr(settings, "LLM_USE_MOCK", False) or getattr(settings, "LLM_PROVIDER", "auto").lower() == "mock"

    @property
    def model_name(self) -> str:
        return self.resolve_provider().model

    @property
    def api_url(self) -> str:
        return self.resolve_provider().base_url

    @property
    def api_key(self) -> str:
        return self.resolve_provider().api_key or "not-needed"

    @property
    def client(self) -> Optional[httpx.Client]:
        config = self.resolve_provider()
        return self._get_client(config)

    def _get_local_provider_config(self) -> LLMProviderConfig:
        return LLMProviderConfig(
            provider="local",
            base_url=getattr(settings, "VLLM_API_URL", "http://localhost:11434/v1").rstrip("/"),
            api_key=getattr(settings, "VLLM_API_KEY", "") or "",
            model=getattr(settings, "LLM_MODEL", "qwen2.5-coder:3b"),
        )

    def get_provider_chain(self) -> list[LLMProviderConfig]:
        """
        Build an ordered sequential chain of all available/configured LLM providers.
        
        Evaluation & Fallback Sequence:
        1. OpenRouter (if OPENROUTER_API_KEY is provided)
        2. GroqCloud (if GROQ_API_KEY is provided or key starts with 'gsk_')
        3. Grok / xAI (if GROK_API_KEY or XAI_API_KEY is provided)
        4. Local Proxy (if LOCAL_PROXY_URL is provided)
        5. OpenAI (if OPENAI_API_KEY is provided)
        6. Local LLM / Ollama (always present at the end of the chain as final fallback)
        """
        if self.use_mock:
            return [
                LLMProviderConfig(
                    provider="mock",
                    base_url="",
                    api_key="",
                    model="mock",
                )
            ]

        provider_override = getattr(settings, "LLM_PROVIDER", "auto").lower().strip()
        chain: list[LLMProviderConfig] = []
        seen_providers: set[str] = set()

        def add_config(cfg: Optional[LLMProviderConfig]):
            if cfg and cfg.provider not in seen_providers:
                chain.append(cfg)
                seen_providers.add(cfg.provider)

        # 1. OpenRouter
        openrouter_key = getattr(settings, "OPENROUTER_API_KEY", "").strip()
        if openrouter_key:
            headers = {
                "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://localhost:3000"),
                "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "Data-Analyzer"),
            }
            add_config(
                LLMProviderConfig(
                    provider="openrouter",
                    base_url=getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
                    api_key=openrouter_key,
                    model=getattr(settings, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"),
                    headers=headers,
                )
            )

        # 2. GroqCloud / Grok detection
        groq_key = getattr(settings, "GROQ_API_KEY", "").strip()
        grok_key = getattr(settings, "GROK_API_KEY", "").strip() or getattr(settings, "XAI_API_KEY", "").strip()

        # If user put a GroqCloud key (gsk_...) into GROK_API_KEY or GROQ_API_KEY
        if groq_key or (grok_key and grok_key.startswith("gsk_")):
            effective_groq_key = groq_key or grok_key
            add_config(
                LLMProviderConfig(
                    provider="groq",
                    base_url=getattr(settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
                    api_key=effective_groq_key,
                    model=getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"),
                )
            )
        elif grok_key:
            # Standard xAI Grok
            add_config(
                LLMProviderConfig(
                    provider="grok",
                    base_url=getattr(settings, "GROK_BASE_URL", "https://api.x.ai/v1").rstrip("/"),
                    api_key=grok_key,
                    model=getattr(settings, "GROK_MODEL", "grok-2-latest"),
                )
            )

        # 3. Local Proxy / Custom OpenAI-compatible proxy (LiteLLM, LocalAI, LM Studio, etc.)
        proxy_url = getattr(settings, "LOCAL_PROXY_URL", "").strip()
        if proxy_url:
            add_config(
                LLMProviderConfig(
                    provider="local_proxy",
                    base_url=proxy_url.rstrip("/"),
                    api_key=getattr(settings, "LOCAL_PROXY_API_KEY", "").strip(),
                    model=getattr(settings, "LOCAL_PROXY_MODEL", "").strip() or getattr(settings, "LLM_MODEL", "qwen2.5-coder:3b"),
                )
            )

        # 4. OpenAI
        openai_key = getattr(settings, "OPENAI_API_KEY", "").strip()
        if openai_key:
            add_config(
                LLMProviderConfig(
                    provider="openai",
                    base_url=getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
                    api_key=openai_key,
                    model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                )
            )

        # 5. Local LLM / Ollama (Always included at end of chain as final fallback)
        add_config(self._get_local_provider_config())

        # If an explicit provider override was requested, move it to the front of the chain
        if provider_override and provider_override not in ("auto", "mock"):
            explicit_config = next((c for c in chain if c.provider == provider_override), None)
            if explicit_config:
                chain.remove(explicit_config)
                chain.insert(0, explicit_config)

        return chain

    def resolve_provider(self) -> LLMProviderConfig:
        """Return the primary (first available) provider in the fallback chain."""
        chain = self.get_provider_chain()
        return chain[0] if chain else self._get_local_provider_config()

    def get_provider_info(self) -> dict:
        chain = self.get_provider_chain()
        primary = chain[0] if chain else self._get_local_provider_config()
        return {
            "active_provider": primary.provider,
            "model": primary.model,
            "base_url": primary.base_url,
            "has_api_key": bool(primary.api_key),
            "fallback_provider": "local",
            "fallback_chain": [f"{c.provider} ({c.model})" for c in chain],
            "total_providers_available": len(chain),
            "local_model": getattr(settings, "LLM_MODEL", "qwen2.5-coder:3b"),
            "local_url": getattr(settings, "VLLM_API_URL", "http://localhost:11434/v1"),
            "is_mock": self.use_mock,
        }

    def _get_client(self, config: LLMProviderConfig) -> Optional[httpx.Client]:
        if not config.base_url:
            return None
        cache_key = f"{config.provider}:{config.base_url}"
        if cache_key not in self._clients:
            try:
                self._clients[cache_key] = httpx.Client(
                    base_url=config.base_url,
                    timeout=httpx.Timeout(config.timeout_seconds, connect=10.0),
                )
            except Exception as e:
                logger.error(f"Failed to create httpx.Client for {config.provider}: {e}")
                return None
        return self._clients[cache_key]

    def _execute_chat_completion(
        self,
        config: LLMProviderConfig,
        messages: list,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        client = self._get_client(config)
        if client is None:
            return None
        try:
            payload = {
                "model": config.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {"Content-Type": "application/json"}
            if config.api_key and config.api_key != "not-needed":
                headers["Authorization"] = f"Bearer {config.api_key}"
            if config.headers:
                headers.update(config.headers)

            resp = client.post("/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"LLM provider '{config.provider}' ({config.model}) execution failed: {e}")
            cache_key = f"{config.provider}:{config.base_url}"
            self._clients.pop(cache_key, None)
            return None

    def _call_llm(self, messages: list, temperature: float = 0.1, max_tokens: int = 1024) -> Optional[str]:
        """
        Execute LLM completion across the sequential provider fallback chain:
        Tries each configured provider sequentially. If a provider fails
        (network error, rate-limit, auth failure), logs a warning and tries
        the next provider in the chain until reaching the local LLM.
        """
        if self.use_mock:
            return None

        chain = self.get_provider_chain()
        attempted_providers = []

        for idx, config in enumerate(chain):
            attempted_providers.append(f"{config.provider} ({config.model})")
            logger.info(f"Attempting LLM call using provider: '{config.provider}' (model: '{config.model}')")
            content = self._execute_chat_completion(config, messages, temperature, max_tokens)
            if content is not None:
                if idx > 0:
                    logger.info(f"Successfully recovered using fallback provider '{config.provider}' after earlier failures.")
                return content

            # If not the last provider in the chain, log fallback attempt
            if idx < len(chain) - 1:
                next_provider = chain[idx + 1].provider
                logger.warning(
                    f"LLM provider '{config.provider}' ({config.model}) failed. "
                    f"Falling back to next provider in chain: '{next_provider}'..."
                )

        logger.error(f"All LLM providers in fallback chain failed: {', '.join(attempted_providers)}")
        return None

    # Backward compatibility alias
    def _call_vllm(self, messages: list, temperature: float = 0.1, max_tokens: int = 1024) -> Optional[str]:
        return self._call_llm(messages, temperature, max_tokens)

    def _get_db_dialect(self, connection_type: str) -> str:
        dialect_map = {
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "mssql": "T-SQL",
            "oracle": "Oracle SQL",
            "mongodb": "MongoDB Query",
            "sqlite": "SQLite",
        }
        return dialect_map.get(connection_type, "SQL")

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

        return f"""You are an expert SQL engineer. Given a database schema and a natural language user question, generate a single valid {dialect} query that accurately answers the user's EXACT question.

DATABASE CONTEXT AND SCHEMA:
{schema_context}

## EXACT SQL GENERATION RULES:

1. NEVER SUBSTITUTE RELATED METRICS:
   - Database columns that sound related are NOT interchangeable!
   - In table PROJECTS:
     * `BUDGET` = allocated project budget
     * `SPENT` = actual project spending (amount spent, money spent, actual spending, total spending)
   - NEVER replace `SPENT` -> `BUDGET` or `BUDGET` -> `SPENT`.
   - In table EMPLOYEES:
     * `SALARY` = employee salary

2. EXACT METRIC MAPPINGS (MANDATORY):
   * 'total employee salary cost' -> `SUM(EMPLOYEES.SALARY)` (or `SUM(salary)` in employee CTE)
   * 'average employee salary' -> `AVG(EMPLOYEES.SALARY)` (or `AVG(salary)` in employee CTE)
   * 'total project budget' -> `SUM(PROJECTS.BUDGET)` (or `SUM(budget)` in project CTE)
   * 'total project spending' -> `SUM(PROJECTS.SPENT)` (or `SUM(spent)` in project CTE)
   * 'project budget utilization percentage' -> `SUM(PROJECTS.SPENT) / SUM(PROJECTS.BUDGET) * 100` (or `CASE WHEN NVL(p.total_project_budget, 0) > 0 THEN NVL(p.total_project_spent, 0) / p.total_project_budget * 100 ELSE 0 END`)
   * 'project spending relative to employee salary cost' -> `SUM(PROJECTS.SPENT) / SUM(EMPLOYEES.SALARY) * 100` (or `CASE WHEN NVL(e.total_salary, 0) > 0 THEN NVL(p.total_project_spent, 0) / e.total_salary * 100 ELSE 0 END`)
   - NEVER calculate `BUDGET / SALARY * 100` when the user asks for project spending relative to salary!

3. REQUESTED METRIC COMPLETENESS:
   - Extract every metric requested by the user. If the user asks for multiple metrics in a single question:
     1. Department name
     2. Total employee salary cost
     3. Average employee salary
     4. Total project budget
     5. Total project spending
     6. Project budget utilization percentage
     7. Project spending relative to employee salary percentage
     ALL requested metrics must be calculated and selected in the final query. Do not omit metrics.

4. PRE-AGGREGATE FIRST, THEN JOIN (ROW MULTIPLICATION / FAN-OUT PREVENTION):
   - When combining EMPLOYEES and PROJECTS by department, aggregate each table separately in independent CTEs before joining to DEPARTMENTS:
     ```sql
     WITH employee_totals AS (
         SELECT department_id, SUM(salary) AS total_salary, AVG(salary) AS average_salary
         FROM employees
         GROUP BY department_id
     ),
     project_totals AS (
         SELECT department_id, SUM(budget) AS total_project_budget, SUM(spent) AS total_project_spent
         FROM projects
         GROUP BY department_id
     )
     SELECT
         d.department_name,
         NVL(e.total_salary, 0) AS total_employee_salary,
         NVL(e.average_salary, 0) AS average_employee_salary,
         NVL(p.total_project_budget, 0) AS total_project_budget,
         NVL(p.total_project_spent, 0) AS total_project_spending,
         CASE WHEN NVL(p.total_project_budget, 0) > 0 THEN NVL(p.total_project_spent, 0) / p.total_project_budget * 100 ELSE 0 END AS project_budget_utilization_percentage,
         CASE WHEN NVL(e.total_salary, 0) > 0 THEN NVL(p.total_project_spent, 0) / e.total_salary * 100 ELSE 0 END AS project_spending_vs_salary_percentage
     FROM departments d
     LEFT JOIN employee_totals e ON d.department_id = e.department_id
     LEFT JOIN project_totals p ON d.department_id = p.department_id
     ORDER BY project_spending_vs_salary_percentage DESC
     FETCH FIRST 1 ROWS ONLY;
     ```

5. RANKING VALIDATION:
   - For ranking (highest, lowest, top), order by the EXACT formula or metric requested (e.g. `ORDER BY project_spending_vs_salary_percentage DESC FETCH FIRST 1 ROWS ONLY`).

6. SYNTAX & DIALECT:{dialect_rules}

INTENT & RELEVANCE RULES:
1. UNRELATED QUESTIONS: Output strictly `UNRELATED: ...` if question cannot be answered from schema.
2. AMBIGUOUS QUESTIONS: Output strictly `AMBIGUOUS: ...` if question lacks specific metric.
3. VALID DATABASE QUESTIONS: Generate a single valid {dialect} query strictly inside a ```sql ... ``` code block."""

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
            sql = sql_match.group(0).strip() if sql_match else ""

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
            f"The following {dialect} query failed preflight structural validation or database execution.\n\n"
            f"User Question: {natural_language}\n\n"
            f"Previous SQL:\n{sql}\n\n"
            f"Validation/Database Error Diagnostic:\n{error}\n\n"
            f"INSTRUCTIONS TO DYNAMICALLY REGENERATE:\n"
            f"1. DO NOT guess column names or perform string replacements.\n"
            f"2. Inspect the schema context above to find the exact verified table and column names.\n"
            f"3. If multiple one-to-many child tables are joined, pre-aggregate each child table in a separate CTE (WITH clause) grouped by department_id BEFORE joining.\n"
            f"4. Regenerate the COMPLETE corrected raw SQL query using ONLY verified tables and columns.\n"
            f"5. Return ONLY the corrected raw SQL query strictly inside a ```sql ... ``` block."
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
        Synthesize exact answer extraction and data summary directly from the executed query
        strictly adhering to EXACT ANSWER EXTRACTION RULES.
        """
        if not rows or not columns:
            return f"Query executed successfully, but returned 0 rows for question: '{natural_language}'."

        sample_rows = rows[:20]
        data_preview = f"Columns: {', '.join(columns)}\nTotal Rows: {len(rows)}\nResults Sample:\n" + "\n".join(str(r) for r in sample_rows)

        system_prompt = (
            "You are the final answer extraction engine for an AI Analytics system.\n"
            "Your job is to answer the user's question EXACTLY AS ASKED using only the validated SQL result and the user's original question.\n\n"
            "## EXACT ANSWER EXTRACTION RULES\n\n"
            "1. EXACT QUESTION COMPLIANCE\n"
            "- Answer every requested part of the user's question.\n"
            "- Do NOT answer a similar question, substitute a related metric, invent a metric, or omit a requested metric.\n"
            "- If the user asks for SPENT, use SPENT. If the user asks for BUDGET, use BUDGET. Never treat them as interchangeable.\n\n"
            "2. COLUMN SEMANTIC ACCURACY\n"
            "- PROJECTS.BUDGET = allocated project budget\n"
            "- PROJECTS.SPENT = actual project spending\n"
            "- EMPLOYEES.SALARY = employee salary\n"
            "- AVG(EMPLOYEES.SALARY) = average employee salary\n"
            "- SUM(EMPLOYEES.SALARY) = total employee salary cost\n"
            "- Never replace SPENT -> BUDGET or BUDGET -> SPENT.\n\n"
            "3. FORMULA ACCURACY\n"
            "- Project budget utilization = total project spending / total project budget * 100 (SUM(SPENT) / SUM(BUDGET) * 100)\n"
            "- Project spending relative to employee salary = total project spending / total employee salary * 100 (SUM(SPENT) / SUM(SALARY) * 100)\n"
            "- These are DIFFERENT metrics. Never substitute one for the other.\n\n"
            "4. REQUESTED METRIC COMPLETENESS\n"
            "- Create an internal checklist of every metric requested by the user and ensure ALL requested metrics are presented.\n\n"
            "5. RANKING QUESTIONS\n"
            "- For questions containing highest, lowest, maximum, minimum, top, bottom, most, least: use ONLY the metric explicitly specified by the user.\n\n"
            "6. EXACT ANSWER ONLY\n"
            "- Provide:\n"
            "  1. The direct answer.\n"
            "  2. Only the values needed to support the answer.\n"
            "  3. The exact calculations requested by the user.\n"
            "- Do NOT add unrelated insights, speculative explanations, or metrics that were not requested.\n\n"
            "Format your output clearly:\n"
            "### 🎯 Direct Answer\n"
            "State the exact direct answer concisely with the validated figures.\n\n"
            "### 📊 Key Calculated Values\n"
            "List the specific metrics and calculated figures requested with proper formatting (currency $, %, commas).\n\n"
            "### 🛠️ Execution Trace & Verification\n"
            "- **Intent**: The exact question answered.\n"
            "- **Metrics Verified**: Exact columns/metrics used from live database records."
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"User Request: {natural_language}\n\n"
                    f"Executed SQL Query:\n{sql}\n\n"
                    f"Database Results Data:\n{data_preview}\n\n"
                    "Extract and provide the exact answer:"
                ),
            },
        ]
        summary = self._call_llm(messages, temperature=0.1, max_tokens=700)
        return summary.strip() if summary else f"Query executed successfully ({len(rows)} rows returned)."

    def _extract_schema_details(self, schema_context: str) -> dict[str, list[str]]:
        """Parse tables and their columns from schema context string."""
        tables: dict[str, list[str]] = {}
        for line in schema_context.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"Table:\s*([^\s\[]+)\s*\[(.*)\]", line)
            if m:
                table_name = m.group(1).strip()
                cols_str = m.group(2).strip()
                cols = [c.split("(")[0].strip() for c in cols_str.split(",") if c.strip()]
                tables[table_name] = cols
            else:
                m2 = re.match(r"Table:\s*([^\s\[]+)", line)
                if m2:
                    table_name = m2.group(1).strip()
                    tables[table_name] = []
        return tables

    def analyze_intent_and_clarify(self, natural_language: str, schema_context: str, dialect: str = "SQL") -> dict:
        """
        Agentic Intent Analyzer & Clarification Generator:
        1. Inspects the schema to see if relevant tables/entities exist.
        2. Determines if the question is broad/ambiguous vs already specific.
        3. If broad (e.g. 'what is the sales'), generates interactive requirement options (Daily, Monthly, Today, By Category, Overall).
        4. If specific, returns {"status": "direct"}.
        5. If unrelated to the schema, returns helpful guidance with available tables.
        """
        if not schema_context or not schema_context.strip():
            return {"status": "direct"}

        prompt_clean = natural_language.strip().lower()
        schema_tables = self._extract_schema_details(schema_context)
        all_table_names = list(schema_tables.keys())
        all_columns = [col.lower() for cols in schema_tables.values() for col in cols]

        # Check if already specific:
        # Check for specific timeframe / specific grouping / specific filter keywords
        specific_time_markers = [
            "today", "yesterday", "this month", "last month", "this year", "last year",
            "last 7 days", "past 7 days", "last 30 days", "past 30 days", "last week", "this week",
            "january", "february", "march", "april", "may", "june", "july", "august",
            "september", "october", "november", "december",
            "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027",
            "daily", "monthly", "yearly", "hourly", "weekly",
            "group by", "order by", "top ", "bottom ", "limit ", "highest", "lowest",
            "most", "least", "where ", "between ", "greater than", "less than"
        ]
        has_specific_time = any(marker in prompt_clean for marker in specific_time_markers)

        specific_dimensions = [
            "by item", "by category", "by product", "by customer", "by user",
            "by status", "by payment", "by role", "by table", "by date", "per day", "per month"
        ]
        has_specific_dim = any(dim in prompt_clean for dim in specific_dimensions)

        # If user gave a specific detailed question, proceed directly
        if (has_specific_time or has_specific_dim) and len(prompt_clean.split()) > 3:
            return {"status": "direct"}

        # Check if question is very short / broad e.g. "what is the sales", "show sales", "revenue", "orders", "sales data", "how much sales"
        broad_keywords = [
            "sales", "revenue", "order", "orders", "income", "earning", "earnings",
            "customer", "customers", "user", "users", "product", "products", "item", "items",
            "transaction", "transactions", "payment", "payments", "booking", "bookings",
            "data", "summary", "report", "analytics", "overview"
        ]
        is_broad = (
            len(prompt_clean.split()) <= 6
            and any(kw in prompt_clean for kw in broad_keywords)
            and not (has_specific_time and has_specific_dim)
        )

        # Detect relevant tables in schema
        sales_tables = [t for t in all_table_names if any(k in t.lower() for k in ("order", "sale", "payment", "bill", "invoice", "transaction", "revenue"))]
        item_tables = [t for t in all_table_names if any(k in t.lower() for k in ("item", "product", "menu", "food", "dish", "category"))]
        user_tables = [t for t in all_table_names if any(k in t.lower() for k in ("user", "customer", "member", "client", "staff", "employee"))]

        # Check if prompt matches sales/revenue concepts
        is_sales_prompt = any(k in prompt_clean for k in ("sale", "sales", "revenue", "earning", "income", "order", "orders", "spent", "amount", "money"))
        is_user_prompt = any(k in prompt_clean for k in ("user", "users", "customer", "customers", "member", "client", "employee", "staff"))
        is_item_prompt = any(k in prompt_clean for k in ("item", "items", "product", "products", "menu", "dish", "category", "food"))

        if is_sales_prompt and sales_tables and (is_broad or not has_specific_time):
            primary_table = sales_tables[0]
            options = [
                {
                    "id": "today",
                    "label": "📅 Today's Sales",
                    "prompt": f"Show today's total sales and order count from {primary_table}",
                    "description": "Total sales revenue and orders placed today",
                },
                {
                    "id": "daily_7d",
                    "label": "📆 Daily (Last 7 Days)",
                    "prompt": f"Show daily sales revenue and orders for the last 7 days from {primary_table}",
                    "description": "Day-by-day sales trend and order volume",
                },
                {
                    "id": "monthly",
                    "label": "📊 Monthly Breakdown",
                    "prompt": f"Show monthly total sales revenue and orders count from {primary_table}",
                    "description": "Monthly revenue performance over time",
                },
            ]
            if item_tables:
                options.append({
                    "id": "top_items",
                    "label": "🍔 Top Items & Categories",
                    "prompt": "Show sales breakdown by top selling items and categories",
                    "description": "Most popular items ranked by total revenue",
                })
            options.append({
                "id": "overall_total",
                "label": "💰 Overall Total Revenue",
                "prompt": f"Show overall total sales revenue, order count, and average order value from {primary_table}",
                "description": "All-time total sales summary and KPIs",
            })

            return {
                "status": "clarify",
                "message": (
                    f"I found sales and order data in the `{primary_table}` table. "
                    f"How would you like to view the sales data?"
                ),
                "options": options,
            }

        if is_user_prompt and user_tables and (is_broad or not has_specific_dim):
            primary_table = user_tables[0]
            options = [
                {
                    "id": "total_users",
                    "label": "👥 Total Count & Growth",
                    "prompt": f"Show total count of users and recent signups from {primary_table}",
                    "description": "Total registered users and latest additions",
                },
                {
                    "id": "users_by_role",
                    "label": "🛡️ Breakdown by Role / Status",
                    "prompt": f"Show user distribution grouped by role or status from {primary_table}",
                    "description": "Active vs inactive users and role assignments",
                },
                {
                    "id": "top_active_users",
                    "label": "⭐ Most Active Customers",
                    "prompt": "Show top customers with the highest orders or activity",
                    "description": "Top customers ranked by total spend or orders",
                },
            ]
            return {
                "status": "clarify",
                "message": (
                    f"I found user and customer records in `{primary_table}`. "
                    f"What aspect of user data would you like to explore?"
                ),
                "options": options,
            }

        if is_item_prompt and item_tables and is_broad:
            primary_table = item_tables[0]
            options = [
                {
                    "id": "all_items_summary",
                    "label": "📋 Items & Categories List",
                    "prompt": f"Show all items with category and pricing from {primary_table}",
                    "description": "Complete list of items and prices",
                },
                {
                    "id": "top_selling_items",
                    "label": "🏆 Top Selling Items",
                    "prompt": "Show top 10 best selling items by revenue and quantity",
                    "description": "Highest revenue generating items",
                },
                {
                    "id": "items_by_category",
                    "label": "📂 Items Count by Category",
                    "prompt": "Show number of items and average price grouped by category",
                    "description": "Category distribution and average price",
                },
            ]
            return {
                "status": "clarify",
                "message": (
                    f"I found menu and catalog items in `{primary_table}`. "
                    f"How would you like to inspect the items?"
                ),
                "options": options,
            }

        # Check if question is completely unrelated to the connected database
        if not any(t.lower() in prompt_clean for t in all_table_names) and len(prompt_clean.split()) <= 5:
            matches_any_column = any(c in prompt_clean for c in all_columns)
            matches_any_table = any(t.lower() in prompt_clean for t in all_table_names)
            if not matches_any_column and not matches_any_table and all_table_names:
                table_list_str = ", ".join(f"`{t}`" for t in all_table_names[:8])
                return {
                    "status": "unrelated",
                    "message": (
                        f"I searched your connected database, but couldn't find data directly matching '{natural_language}'.\n\n"
                        f"Your database contains the following tables: {table_list_str}.\n"
                        f"You can choose one of the suggestions below or ask about any of these tables:"
                    ),
                    "options": [
                        {
                            "id": f"table_{t}",
                            "label": f"📊 Explore {t.replace('_', ' ').title()}",
                            "prompt": f"Show summary and top records from {t}",
                            "description": f"Overview of data in {t}",
                        }
                        for t in all_table_names[:4]
                    ],
                }

        return {"status": "direct"}

    def generate_follow_up_suggestions(
        self, natural_language: str, sql: str, columns: list[str], rows: list[list]
    ) -> list[str]:
        """Generate 3-4 insightful follow-up suggestion prompts based on the executed query."""
        suggestions = []
        nl_lower = natural_language.lower()
        cols_lower = [c.lower() for c in (columns or [])]

        if "today" in nl_lower or "daily" in nl_lower:
            suggestions.append("Compare this with the previous week")
            suggestions.append("Show monthly breakdown for this year")
        elif "month" in nl_lower:
            suggestions.append("Show daily trend for the highest performing month")
            suggestions.append("Compare month-over-month growth rate")
        else:
            suggestions.append("Show daily trend for the last 7 days")

        if any("item" in c or "product" in c or "menu" in c for c in cols_lower):
            suggestions.append("Show top 5 items by total revenue")
            suggestions.append("Break down sales by category")
        elif any("user" in c or "customer" in c for c in cols_lower):
            suggestions.append("Show top customers by total spending")
        else:
            suggestions.append("Break down results by category or item")

        if any("revenue" in c or "total" in c or "amount" in c or "price" in c for c in cols_lower):
            suggestions.append("What is the average order value?")
            suggestions.append("Show the highest and lowest single orders")

        unique_suggestions = []
        for s in suggestions:
            if s.lower() != nl_lower and s not in unique_suggestions:
                unique_suggestions.append(s)
            if len(unique_suggestions) >= 4:
                break

        return unique_suggestions


llm_service = LLMService()
