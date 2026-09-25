"""Adversarial Security Test Harness for Milestone M2 Verification.

Constructed by teamwork_preview_challenger_m2_gen2_1 to empirically probe:
1. Header forgery & scheme manipulation (Basic, Token, Digest, malformed Bearer, SQLi, Buffer overflow).
2. Alg: none unsigned JWT attacks, forged secrets, malformed claims, invalid types.
3. Direct unauthenticated attacks against LLM query endpoints (/api/v1/queries, /sql, /follow-up, /explain, /optimize, /visualize, etc.).
4. Shadow / non-existent LLM routes (/api/v1/queries/generate-sql, /api/v1/queries/execute).
5. Dynamic route scanning and assertion verification.
"""

import os
import pytest
from datetime import timedelta
from jose import jwt
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.utils.security import create_access_token


class TestAdversarialHeaderAttacks:
    """Stress tests authentication boundary with forged and malformed Authorization headers."""

    FORGED_HEADERS = [
        ("Missing Header", None),
        ("Empty Header", ""),
        ("Basic Auth Scheme", "Basic dXNlcjpwYXNz"),
        ("Token Scheme", "Token abcdef1234567890"),
        ("Digest Scheme", "Digest username=admin, realm=realm"),
        ("Bearer without Token", "Bearer"),
        ("Bearer single space", "Bearer "),
        ("Bearer multiple spaces", "Bearer    "),
        ("Bearer lowercase", "bearer "),
        ("Bearer bogus token value", "Bearer bogus.token.value"),
        ("Bearer null", "Bearer null"),
        ("Bearer undefined", "Bearer undefined"),
        ("Bearer SQLi payload", "Bearer ' OR '1'='1"),
        ("Bearer Buffer Overflow attempt", "Bearer " + "A" * 8192),
    ]

    @pytest.mark.parametrize("label,header_val", FORGED_HEADERS)
    def test_forged_headers_rejected_at_queries_endpoint(self, client, label, header_val):
        headers = {"Authorization": header_val} if header_val is not None else {}
        response = client.post(
            "/api/v1/queries",
            json={"prompt": "Adversarial exploit test", "database_id": 1},
            headers=headers,
        )
        # Must be rejected with 401 Unauthorized or 403 Forbidden (never 200 or bypass)
        assert response.status_code in (401, 403), f"Failed for {label}: got {response.status_code}"
        assert "password" not in response.text.lower()
        assert "traceback" not in response.text.lower()

    @pytest.mark.parametrize("label,header_val", FORGED_HEADERS)
    def test_forged_headers_rejected_at_connections_endpoint(self, client, label, header_val):
        headers = {"Authorization": header_val} if header_val is not None else {}
        response = client.get("/api/v1/connections", headers=headers)
        assert response.status_code in (401, 403), f"Failed for {label}: got {response.status_code}"

    @pytest.mark.parametrize("label,header_val", FORGED_HEADERS)
    def test_forged_headers_rejected_at_dashboards_endpoint(self, client, label, header_val):
        headers = {"Authorization": header_val} if header_val is not None else {}
        response = client.get("/api/v1/dashboards", headers=headers)
        assert response.status_code in (401, 403), f"Failed for {label}: got {response.status_code}"


class TestAdversarialJWTForging:
    """Stress tests JWT token decoding against algorithm confusion and forged claims."""

    def test_alg_none_unsigned_token_rejected(self, client):
        """Attackers forge a token with alg: none to bypass signature checking."""
        unsigned_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyJ9."
        response = client.get("/api/v1/queries", headers={"Authorization": f"Bearer {unsigned_token}"})
        assert response.status_code == 401
        assert response.json().get("detail") == "Invalid or expired token"

    def test_wrong_secret_key_token_rejected(self, client):
        """Token signed with arbitrary attacker secret key must be rejected."""
        token = jwt.encode({"sub": "1", "type": "access"}, "attacker-unauthorized-secret-key-12345", algorithm="HS256")
        response = client.get("/api/v1/queries", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json().get("detail") == "Invalid or expired token"

    def test_token_with_missing_sub_rejected(self, client):
        """Token with missing 'sub' claim must not authenticate."""
        token = jwt.encode({"type": "access"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        response = client.get("/api/v1/queries", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json().get("detail") == "Invalid token payload"

    def test_token_with_nonexistent_user_id_rejected(self, client):
        """Token with valid signature but non-existent user ID must return 401 User not found."""
        token = jwt.encode({"sub": "99999999", "type": "access"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        response = client.get("/api/v1/queries", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json().get("detail") == "User not found"

    def test_token_with_non_integer_sub_does_not_bypass(self, db_session):
        """Token with string sub='admin' (cannot cast to int) must not bypass auth."""
        safe_client = TestClient(app, raise_server_exceptions=False)
        token = jwt.encode({"sub": "admin", "type": "access"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        response = safe_client.get("/api/v1/queries", headers={"Authorization": f"Bearer {token}"})
        # int('admin') in deps.py raises ValueError, caught by global exception handler as 500
        assert response.status_code in (401, 500)
        assert response.status_code != 200
        assert "access_granted" not in response.text


class TestLLMQueryEndpointsDirectAttacks:
    """Stress tests direct unauthenticated requests to all LLM query endpoints."""

    def test_direct_execute_query_without_credentials(self, client):
        response = client.post(
            "/api/v1/queries",
            json={"prompt": "SELECT * FROM passwords;", "database_id": 1},
        )
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_direct_execute_sql_without_credentials(self, client):
        response = client.post(
            "/api/v1/queries/sql",
            json={"sql": "SELECT * FROM users;", "database_id": 1},
        )
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_direct_follow_up_without_credentials(self, client):
        response = client.post(
            "/api/v1/queries/1/follow-up",
            json={"prompt": "Explain previous data"},
        )
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_direct_explain_query_without_credentials(self, client):
        response = client.get("/api/v1/queries/1/explain")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_direct_optimize_query_without_credentials(self, client):
        response = client.post("/api/v1/queries/1/optimize")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_direct_visualize_query_without_credentials(self, client):
        response = client.post("/api/v1/queries/1/visualize")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_direct_dashboard_auto_generate_without_credentials(self, client):
        response = client.post(
            "/api/v1/dashboards/auto-generate",
            json={"database_id": 1, "prompt": "Executive overview"},
        )
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_shadow_or_unregistered_llm_routes_blocked(self, client):
        """Probe routes like /generate-sql or /execute:
        - GET matches /{query_id} requiring auth -> 401
        - POST has no /{query_id} route -> 405 Method Not Allowed
        Neither allows bypass or unauthenticated execution.
        """
        for path in ("/api/v1/queries/generate-sql", "/api/v1/queries/execute"):
            get_resp = client.get(path)
            assert get_resp.status_code == 401, f"Expected 401 for GET {path}, got {get_resp.status_code}"
            assert get_resp.json().get("detail") in ("Not authenticated", "Invalid or expired token")

            post_resp = client.post(path, json={"prompt": "dump db"})
            assert post_resp.status_code in (401, 404, 405), f"Expected 401/404/405 for POST {path}, got {post_resp.status_code}"
            assert post_resp.status_code != 200
