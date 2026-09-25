# Antigravity Rules - Data-Taker / Data-Analyzer

## Core Principle: NEVER HARDCODE ANYTHING

### 1. Configuration, Secrets, and Environment Variables
- **Never hardcode secrets, API keys, credentials, hostnames, ports, or URLs** in source code.
- Backend settings must be defined in `backend/app/config.py` using Pydantic `BaseSettings` and loaded via environment variables (`.env`).
- Frontend settings must be read from `process.env` (e.g. `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_MAILHOG_URL`) with graceful runtime fallbacks.
- Never commit actual production secrets or private keys to version control.

### 2. User Identities, Roles, and Permissions
- **Never hardcode specific user emails, names, IDs, or company IDs** in application logic, route handlers, guards, middleware, seed scripts, or test assertions.
- Superuser/admin bootstrapping in seed scripts must read from `ADMIN_EMAIL` / `FIRST_SUPERUSER` / `ADMIN_PASSWORD` environment variables.
- Authentication, authorization, and RBAC must always be evaluated dynamically using the authenticated `current_user`, active session JWT claims, database-backed roles, and permissions (`require_permission`).
- Self-operation protections (such as prohibiting a user from deactivating or deleting their own account) must compare dynamic entity IDs (`target_user.id == current_user.id`), never hardcoded strings or IDs.

### 3. Multi-Tenancy & Data Isolation
- Always isolate tenant data dynamically using `current_user.company_id`.
- Never hardcode company/tenant IDs or assume a static single-tenant scope.

### 4. Database Queries & Dynamic Schemas
- Never hardcode table names, schema names, or query literals when introspecting or executing user database operations.
- Always use parameterized queries, SQLAlchemy ORM queries, and metadata introspection to safeguard against SQL injection and cross-tenant leakage.

### 5. Frontend Navigation & Component Design
- Centralize all API requests through `frontend/src/lib/api-client.ts` and `frontend/src/lib/api-cache.ts`.
- Avoid hardcoding navigation endpoints, external redirect URLs, or port numbers inside individual React components.
