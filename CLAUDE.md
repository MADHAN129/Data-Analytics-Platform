# CLAUDE.md

## Project

**Data-Taker / Data-Analyzer** — an agentic SQL analytics platform: connect
databases (Postgres, MySQL, MongoDB, SQL Server), ask questions in natural
language, and get queries, results, and dashboards. Stack:

- `backend/` — FastAPI + SQLAlchemy + Postgres. MCP server for LLM tool use.
- `frontend/` — Next.js 16 (App Router) + Tailwind, talks to `/api/v1`.
- `docker-compose.yml` — postgres, redis, mailhog, backend, ollama, frontend.

## Commands

```bash
# Backend (Windows: use .venv\Scripts\python.exe)
cd backend && python -m pytest                 # run test suite (SQLite in-memory)
python seed.py                                 # seed dev data (admin user)

# Frontend
cd frontend && npm run dev                     # dev server on :3000
npm run build && npm run start                 # production
```

Local dev without Docker: start postgres+redis (`docker compose up -d postgres redis`),
set `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, `MCP_API_KEY` in a `.env`,
then `uvicorn app.main:app --reload` from `backend/`.

## Testing

- Suite: pytest in `backend/tests/` — see `TESTING.md` for details and conventions.
- Tests are self-contained: `tests/conftest.py` sets env vars, patches
  `JSONB` → `JSON` before model imports, and gives every test a fresh
  in-memory SQLite DB (StaticPool). Never reorder the imports there.
- CI: `.github/workflows/test.yml` runs backend tests + frontend lint/build.
- The full docker-compose stack needs an NVIDIA runtime (ollama); on machines
  without a GPU run postgres/redis only and set `LLM_USE_MOCK=true`.

## Conventions

- Backend: routers in `app/api/`, business logic in `app/services/`, models in
  `app/models/`, Pydantic schemas in `app/schemas/`.
- RBAC: every protected route depends on `require_permission("<resource>.<action>")`
  from `app/api/deps.py`; admin grants come via the `access.manage` permission.
- Ownership: `list_databases`/`get_database` (and dashboards) take `user_id`
  plus `include_all`; services return `None` when the user cannot see a resource.
- Secrets: DB passwords are encrypted with `app.utils.security.encrypt_secret`
  (Fernet, `ENCRYPTION_KEY`); plaintext `password` is legacy.
- Audit: write `create_audit_log(...)` after mutating actions (see `app/api/audit.py`).
