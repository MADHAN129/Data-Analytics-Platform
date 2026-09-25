---
trigger: always_on
description: Strictly enforces zero hardcoding of credentials, emails, URLs, IDs, or secrets across the codebase.
---

# Rule: Never Hardcode Anything

1. **Configuration & Secrets**:
   - Always load credentials, tokens, URLs, ports, and API keys via environment variables or configuration files.
   - Never embed static passwords, JWT secrets, or encryption keys in source files.

2. **User Context & Authorization**:
   - Never hardcode user emails (e.g., admin emails or personal user emails), user IDs, or company IDs in business logic, routes, or seed routines.
   - Resolve identity, role status, and permissions dynamically via authenticated JWT session context (`current_user`) and database records.

3. **Dynamic Multi-Tenancy**:
   - Always filter queries by `current_user.company_id` dynamically.

4. **Dynamic Database Introspection**:
   - Parameterize all dynamic queries and introspect schemas/tables dynamically rather than hardcoding static database schema structures.

5. **Frontend API & Links**:
   - Always use environment variables (`NEXT_PUBLIC_*`) for endpoints and external URLs.
