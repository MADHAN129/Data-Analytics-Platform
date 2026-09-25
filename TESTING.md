# Testing

The backend has a pytest suite covering security utilities, RBAC permission
checks, connection/dashboard ownership scoping, and API gate behavior (auth,
MCP API-key, role-based access).

## Running the suite

```bash
cd backend
.venv/Scripts/python -m pytest          # Windows
python -m pytest                        # Linux/macOS (venv active)
```

All tests run against an in-memory SQLite database (auto-configured in
`tests/conftest.py`), so no Postgres or Redis is required locally.

### With coverage

```bash
python -m pytest --cov=app --cov-report=term-missing
```

## What is covered

| Area | File | Notes |
|------|------|-------|
| JWT tokens, password hashing, Fernet secret encryption | `tests/test_security_utils.py` | |
| RBAC permission checks (roles, role-permissions, admin `access.manage`) | `tests/test_rbac.py` | |
| RBAC API gates (403/401 responses, audit logs, role assignment) | `tests/test_rbac.py` | |
| Connection/dashboard ownership scoping (service + API 404s) | `tests/test_ownership.py` | |
| MCP server API-key auth | `tests/test_mcp_auth.py` | |

## Conventions

- Fixtures (`db_session`, `client`, `admin`, `analyst`, `viewer`, `permissions`) live in `tests/conftest.py`.
- Each test gets a fresh in-memory database (function-scoped engine with `StaticPool`).
- Use `auth_headers(user)` to make authenticated requests.
- Postgres-only `JSONB` is mapped to portable `JSON` before models load — do not reorder imports in `conftest.py`.

## CI

GitHub Actions runs the backend suite on Postgres (`.github/workflows/test.yml`).
The suite itself uses SQLite; the Postgres service container is available for
integration work.
