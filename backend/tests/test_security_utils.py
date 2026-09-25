from datetime import timedelta

from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_secret,
    decrypt_secret,
)


class TestTokens:
    def test_access_token_roundtrip(self):
        token = create_access_token({"sub": "7"})
        payload = decode_token(token)
        assert payload["sub"] == "7"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        token = create_refresh_token({"sub": "7"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_expired_token_rejected(self):
        token = create_access_token({"sub": "7"}, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None

    def test_tampered_token_rejected(self):
        token = create_access_token({"sub": "7"})
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalid_signature"
        assert decode_token(tampered) is None


class TestSecretEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        encrypted = encrypt_secret("hunter2")
        assert encrypted != "hunter2"
        assert decrypt_secret(encrypted) == "hunter2"

    def test_legacy_plaintext_fallback(self):
        assert decrypt_secret("plaintext-legacy-password") == "plaintext-legacy-password"

    def test_empty_value_passthrough(self):
        assert decrypt_secret("") == ""
