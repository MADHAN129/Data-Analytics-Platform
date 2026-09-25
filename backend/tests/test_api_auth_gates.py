"""Comprehensive API Authentication & Authorization Security Test Suite.

Verifies and asserts that:
1. Every protected endpoint across backend/app/api/ returns HTTP 401 Unauthorized
   when accessed without an Authorization token.
2. Token boundary cases (malformed, expired, refresh token as access, deactivated user,
   insufficient permissions) are strictly handled with proper 401/403 status codes.
3. Public endpoints (/health, /api/v1/auth/login, register, forgot-password) are functional
   without Bearer token and do not disclose internal secrets, credentials, or keys.
"""

from datetime import timedelta
import re
import pytest

from app.main import app
from app.utils.security import create_access_token, create_refresh_token
from tests.conftest import auth_headers


# ============================================================================
# 1. QUERIES ENDPOINTS AUTH GATES
# ============================================================================

class TestQueriesAuthGates:
    """Verifies that all queries and LLM execution endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/queries", None),
            ("POST", "/api/v1/queries", {"prompt": "Show total sales", "database_id": 1}),
            ("POST", "/api/v1/queries/sql", {"sql": "SELECT 1", "database_id": 1}),
            ("GET", "/api/v1/queries/suggestions", None),
            ("GET", "/api/v1/queries/1", None),
            ("POST", "/api/v1/queries/1/follow-up", {"prompt": "Group by month"}),
            ("POST", "/api/v1/queries/1/favorite", None),
            ("DELETE", "/api/v1/queries/1", None),
            ("GET", "/api/v1/queries/1/export", None),
            ("POST", "/api/v1/queries/1/cancel", None),
            ("GET", "/api/v1/queries/1/explain", None),
            ("POST", "/api/v1/queries/1/optimize", None),
            ("POST", "/api/v1/queries/1/visualize", None),
        ],
    )
    def test_unauthenticated_queries_endpoint_returns_401(self, client, method, path, payload):
        response = client.request(method, path, json=payload if payload else None)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 2. CONNECTIONS / DATABASES ENDPOINTS AUTH GATES
# ============================================================================

class TestConnectionsAuthGates:
    """Verifies that all connection and schema exploration endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/connections", None),
            ("POST", "/api/v1/connections", {
                "name": "Test DB",
                "connection_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database_name": "test_db",
                "username": "user",
                "password": "pwd",
            }),
            ("POST", "/api/v1/connections/test", {
                "name": "Test DB",
                "connection_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database_name": "test_db",
                "username": "user",
                "password": "pwd",
            }),
            ("GET", "/api/v1/connections/1", None),
            ("PUT", "/api/v1/connections/1", {"name": "Updated DB"}),
            ("DELETE", "/api/v1/connections/1", None),
            ("POST", "/api/v1/connections/1/test", None),
            ("GET", "/api/v1/connections/health/batch", None),
            ("GET", "/api/v1/connections/1/health", None),
            ("GET", "/api/v1/connections/1/schema", None),
            ("POST", "/api/v1/connections/1/sync", None),
            ("POST", "/api/v1/connections/1/refresh-schema", None),
            ("GET", "/api/v1/connections/1/tables", None),
            ("GET", "/api/v1/connections/1/tables/users", None),
        ],
    )
    def test_unauthenticated_connections_endpoint_returns_401(self, client, method, path, payload):
        response = client.request(method, path, json=payload if payload else None)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 3. CONVERSATIONS ENDPOINTS AUTH GATES
# ============================================================================

class TestConversationsAuthGates:
    """Verifies that all conversational analytics endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/conversations", None),
            ("POST", "/api/v1/conversations", {"title": "Sales Analysis"}),
            ("GET", "/api/v1/conversations/1", None),
            ("PUT", "/api/v1/conversations/1", {"title": "Updated Analysis"}),
            ("PATCH", "/api/v1/conversations/1", {"title": "Patched Analysis"}),
            ("DELETE", "/api/v1/conversations/1", None),
            ("GET", "/api/v1/conversations/1/messages", None),
            ("POST", "/api/v1/conversations/1/messages", {"content": "What was yesterday revenue?"}),
        ],
    )
    def test_unauthenticated_conversations_endpoint_returns_401(self, client, method, path, payload):
        response = client.request(method, path, json=payload if payload else None)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 4. DASHBOARDS ENDPOINTS AUTH GATES
# ============================================================================

class TestDashboardsAuthGates:
    """Verifies that all dashboard and widget endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/dashboards", None),
            ("POST", "/api/v1/dashboards", {"title": "Executive KPI Dashboard"}),
            ("GET", "/api/v1/dashboards/1", None),
            ("PUT", "/api/v1/dashboards/1", {"title": "Updated Title"}),
            ("DELETE", "/api/v1/dashboards/1", None),
            ("POST", "/api/v1/dashboards/1/widgets", {"title": "Revenue Chart", "widget_type": "bar"}),
            ("PUT", "/api/v1/dashboards/1/widgets/1", {"title": "Renamed Widget"}),
            ("DELETE", "/api/v1/dashboards/1/widgets/1", None),
            ("PUT", "/api/v1/dashboards/1/layout", {"layout": [{"id": 1, "x": 0, "y": 0, "w": 6, "h": 4}]}),
            ("POST", "/api/v1/dashboards/auto-generate", {"database_id": 1, "prompt": "Revenue trends"}),
        ],
    )
    def test_unauthenticated_dashboards_endpoint_returns_401(self, client, method, path, payload):
        response = client.request(method, path, json=payload if payload else None)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 5. TEMPLATES ENDPOINTS AUTH GATES
# ============================================================================

class TestTemplatesAuthGates:
    """Verifies that all query template management endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/templates", None),
            ("POST", "/api/v1/templates", {
                "name": "Daily Revenue",
                "template_sql": "SELECT SUM(amount) FROM orders WHERE date = :date",
            }),
            ("GET", "/api/v1/templates/1", None),
            ("PUT", "/api/v1/templates/1", {"name": "Updated Daily Revenue"}),
            ("DELETE", "/api/v1/templates/1", None),
            ("POST", "/api/v1/templates/1/instantiate", None),
        ],
    )
    def test_unauthenticated_templates_endpoint_returns_401(self, client, method, path, payload):
        response = client.request(method, path, json=payload if payload else None)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 6. AUDIT ENDPOINTS AUTH GATES
# ============================================================================

class TestAuditAuthGates:
    """Verifies that all audit log inspection and export endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/audit/logs"),
            ("GET", "/api/v1/audit/logs/export"),
            ("GET", "/api/v1/audit/stats"),
        ],
    )
    def test_unauthenticated_audit_endpoint_returns_401(self, client, method, path):
        response = client.request(method, path)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 7. USERS ENDPOINTS AUTH GATES
# ============================================================================

class TestUsersAuthGates:
    """Verifies that all user management and profile endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/users/me", None),
            ("PUT", "/api/v1/users/me", {"full_name": "Updated Name"}),
            ("PUT", "/api/v1/users/me/password", {"current_password": "OldPassword1!", "new_password": "NewPassword2!"}),
            ("GET", "/api/v1/users", None),
            ("POST", "/api/v1/users", {
                "email": "user@test.com",
                "password": "Password123!",
                "full_name": "Test User",
            }),
            ("GET", "/api/v1/users/1", None),
            ("PUT", "/api/v1/users/1", {"full_name": "Renamed User"}),
            ("DELETE", "/api/v1/users/1", None),
            ("POST", "/api/v1/users/1/activate", None),
            ("POST", "/api/v1/users/1/deactivate", None),
            ("GET", "/api/v1/users/1/roles", None),
            ("POST", "/api/v1/users/1/roles", {"role_id": 1}),
            ("DELETE", "/api/v1/users/1/roles/1", None),
        ],
    )
    def test_unauthenticated_users_endpoint_returns_401(self, client, method, path, payload):
        response = client.request(method, path, json=payload if payload else None)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 8. ROLES & PERMISSIONS ENDPOINTS AUTH GATES
# ============================================================================

class TestRolesAndPermissionsAuthGates:
    """Verifies that RBAC role and permission inspection/mutation endpoints strictly require auth."""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/roles", None),
            ("POST", "/api/v1/roles", {"name": "CustomAuditor", "description": "Audit role"}),
            ("GET", "/api/v1/roles/1", None),
            ("PUT", "/api/v1/roles/1", {"name": "RenamedRole"}),
            ("DELETE", "/api/v1/roles/1", None),
            ("POST", "/api/v1/roles/1/permissions", {"permission_id": 1}),
            ("DELETE", "/api/v1/roles/1/permissions/1", None),
            ("GET", "/api/v1/permissions", None),
            ("GET", "/api/v1/permissions/1", None),
        ],
    )
    def test_unauthenticated_roles_permissions_endpoint_returns_401(self, client, method, path, payload):
        response = client.request(method, path, json=payload if payload else None)
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 9. ACTIVITY ENDPOINT AUTH GATE
# ============================================================================

class TestActivityAuthGates:
    """Verifies that activity telemetry endpoint strictly requires auth."""

    def test_unauthenticated_activity_overview_returns_401(self, client):
        response = client.get("/api/v1/activity/overview")
        assert response.status_code == 401
        assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
        assert "Bearer" in response.headers.get("www-authenticate", "")


# ============================================================================
# 10. DYNAMIC FULL-APP PROTECTED ROUTE SCANNER
# ============================================================================

class TestAllProtectedRoutesDynamicScanner:
    """Programmatically discovers and asserts 401 for EVERY protected endpoint in app."""

    PUBLIC_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/refresh",
    }

    def test_every_cataloged_endpoint_without_token_returns_401(self, client):
        openapi = app.openapi()
        paths = openapi.get("paths", {})
        scanned_count = 0

        for path, path_item in paths.items():
            if path in self.PUBLIC_PATHS:
                continue

            for method in ("get", "post", "put", "patch", "delete"):
                if method not in path_item:
                    continue

                # Substitute route parameters with dummy numeric or string IDs
                concrete_path = re.sub(r"\{[^}]+\}", "1", path)

                response = client.request(method.upper(), concrete_path)
                assert response.status_code == 401, (
                    f"Expected 401 Unauthorized for unauthenticated {method.upper()} {concrete_path}, "
                    f"got {response.status_code}: {response.text}"
                )
                assert response.json().get("detail") in ("Not authenticated", "Invalid or expired token")
                scanned_count += 1

        # Must scan at least 60+ distinct HTTP method/path operations across the platform
        assert scanned_count >= 60, f"Expected to scan at least 60 protected routes, scanned {scanned_count}"


# ============================================================================
# 11. TOKEN BOUNDARY CASES & NEGATIVE TESTING
# ============================================================================

class TestTokenBoundaryCases:
    """Verifies edge cases: malformed tokens, expired tokens, token type mismatch,
    deactivated users, and insufficient permissions."""

    def test_malformed_token_returns_401(self, client):
        headers = {"Authorization": "Bearer invalid_garbage_token_value_xyz"}
        response = client.get("/api/v1/queries", headers=headers)
        assert response.status_code == 401
        assert response.json().get("detail") == "Invalid or expired token"

    def test_expired_jwt_token_returns_401(self, client, analyst):
        expired_token = create_access_token({"sub": str(analyst.id)}, expires_delta=timedelta(seconds=-60))
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/queries", headers=headers)
        assert response.status_code == 401
        assert response.json().get("detail") == "Invalid or expired token"

    def test_refresh_token_used_as_access_token_returns_401(self, client, analyst):
        refresh_token = create_refresh_token({"sub": str(analyst.id)})
        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = client.get("/api/v1/queries", headers=headers)
        assert response.status_code == 401
        assert response.json().get("detail") == "Invalid or expired token"

    def test_deactivated_user_account_returns_403(self, client, db_session, analyst):
        analyst.is_active = False
        db_session.commit()

        token = create_access_token({"sub": str(analyst.id)})
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/queries", headers=headers)
        assert response.status_code == 403
        assert "User account is deactivated" in response.json().get("detail", "")

    def test_user_lacking_specific_permission_returns_403(self, client, viewer):
        """Viewer has database.read and dashboard.read, but lacks query.execute and user.create."""
        headers = auth_headers(viewer)

        # Attempt query execution (requires query.execute) -> 403
        response = client.post(
            "/api/v1/queries",
            json={"prompt": "Select 1", "database_id": 1},
            headers=headers,
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json().get("detail", "")

        # Attempt raw SQL execution (requires query.execute) -> 403
        response = client.post(
            "/api/v1/queries/sql",
            json={"sql": "SELECT 1", "database_id": 1},
            headers=headers,
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json().get("detail", "")

        # Attempt user creation (requires user.create) -> 403
        response = client.post(
            "/api/v1/users",
            json={"email": "newbie@test.com", "password": "Password123!", "full_name": "Newbie"},
            headers=headers,
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json().get("detail", "")

        # Attempt audit log reading (requires audit.read) -> 403
        response = client.get("/api/v1/audit/logs", headers=headers)
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json().get("detail", "")


# ============================================================================
# 12. PUBLIC ENDPOINTS SAFETY & NO LEAKAGE
# ============================================================================

class TestPublicEndpointsSafety:
    """Verifies that public endpoints function without Bearer tokens and strictly
    prevent leakage of database URLs, credentials, password hashes, or LLM keys."""

    def test_health_check_returns_200_without_secrets(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "services" in data

        # Check for forbidden sensitive keywords in the raw response text
        raw_text = response.text.lower()
        forbidden_keywords = [
            "password",
            "secret",
            "postgresql://",
            "mysql://",
            "oracle://",
            "mongodb://",
            "sqlite://",
            "sk-",
            "private_key",
            "token_urlsafe",
        ]
        for keyword in forbidden_keywords:
            assert keyword not in raw_text, f"Potential credential leak: '{keyword}' found in /health response"

    def test_auth_login_public_and_safe_without_token(self, client, plain_user):
        # 1. Invalid login attempt
        bad_response = client.post(
            "/api/v1/auth/login",
            json={"email": "plain@test.com", "password": "WrongPassword!"},
        )
        assert bad_response.status_code == 401
        assert bad_response.json().get("detail") == "Invalid email or password"
        assert "password_hash" not in bad_response.text

        # 2. Valid login attempt
        good_response = client.post(
            "/api/v1/auth/login",
            json={"email": "plain@test.com", "password": "Password123!"},
        )
        assert good_response.status_code == 200
        data = good_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "password_hash" not in str(data)

    def test_auth_register_public_and_safe_without_token(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "fresh_user@example.com",
                "password": "StrongPassword123!",
                "full_name": "Fresh User",
                "company_name": "Fresh Org",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "password_hash" not in str(data)

        # Duplicate registration should return 409 without internal stack traces
        dup_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "fresh_user@example.com",
                "password": "StrongPassword123!",
                "full_name": "Fresh User",
                "company_name": "Fresh Org",
            },
        )
        assert dup_response.status_code == 409
        assert dup_response.json().get("detail") == "Email already registered"

    def test_auth_forgot_password_enumeration_safe_without_token(self, client, plain_user):
        # Existing email
        r1 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "plain@test.com"},
        )
        assert r1.status_code == 200
        assert r1.json().get("message") == "If the email exists, a reset link has been sent"

        # Non-existing email
        r2 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent_email_9988@example.com"},
        )
        assert r2.status_code == 200
        assert r2.json().get("message") == "If the email exists, a reset link has been sent"
