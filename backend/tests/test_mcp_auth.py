import pytest

from app.config import Settings


class TestMCPAuth:
    def test_mcp_rejects_missing_key(self, client):
        r = client.get("/mcp/")
        assert r.status_code == 401

    def test_mcp_rejects_wrong_key(self, client):
        r = client.get("/mcp/", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401

    def test_mcp_accepts_valid_key(self, client):
        import os

        r = client.get("/mcp/", headers={"X-API-Key": os.environ["MCP_API_KEY"]})
        assert r.status_code in (307, 308, 200, 404)


class TestConfigValidators:
    def test_weak_secret_key_rejected(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings(SECRET_KEY="", _env_file=None)

    def test_default_secret_key_rejected(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings(SECRET_KEY="super-secret-key-change-in-production-abc123",
                      ENCRYPTION_KEY="qyJzC2nA8m1vK5pE6tW3xR7uB9yD4fG8hJ2kL5nQ7sT1=",
                      _env_file=None)

    def test_empty_encryption_key_rejected(self):
        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            Settings(SECRET_KEY="a" * 64, ENCRYPTION_KEY="", _env_file=None)

    def test_mcp_enabled_without_key_rejected(self):
        with pytest.raises(ValueError, match="MCP_API_KEY"):
            Settings(
                SECRET_KEY="a" * 64,
                ENCRYPTION_KEY="qyJzC2nA8m1vK5pE6tW3xR7uB9yD4fG8hJ2kL5nQ7sT1=",
                MCP_ENABLED=True,
                MCP_API_KEY="",
                _env_file=None,
            )

    def test_valid_settings_pass(self):
        s = Settings(
            SECRET_KEY="a" * 64,
            ENCRYPTION_KEY="qyJzC2nA8m1vK5pE6tW3xR7uB9yD4fG8hJ2kL5nQ7sT1=",
            MCP_ENABLED=True,
            MCP_API_KEY="some-key",
            _env_file=None,
        )
        assert s.MCP_API_KEY == "some-key"
