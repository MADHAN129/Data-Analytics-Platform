from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    APP_NAME: str = "Agentic Analytics API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/agentic"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Fernet key (base64, 32 bytes) used to encrypt DB connection passwords at rest
    ENCRYPTION_KEY: str = ""

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    SMTP_HOST: str = ""
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@agentic-analytics.com"
    SMTP_FROM_NAME: str = "Agentic Analytics"
    APP_URL: str = "http://localhost:3000"

    VLLM_API_URL: str = "http://localhost:11434/v1"
    VLLM_API_KEY: str = ""
    LLM_USE_MOCK: bool = False
    LLM_MODEL: str = "qwen3:8b"

    MCP_API_KEY: str = ""
    MCP_ENABLED: bool = True
    USE_MCP_TOOLS: bool = False  # Set to True to enable MCP tool usage in LLM services

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_security_settings(self):
        known_weak_keys = {"", "super-secret-key-change-in-production-abc123"}
        if self.SECRET_KEY in known_weak_keys:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in .env "
                "(e.g. generated with `python -c \"import secrets; print(secrets.token_urlsafe(64))\"`)"
            )
        if self.ENCRYPTION_KEY == "":
            raise ValueError(
                "ENCRYPTION_KEY must be set in .env "
                "(generate with `python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`)"
            )
        if self.MCP_ENABLED and not self.MCP_API_KEY:
            raise ValueError(
                "MCP_API_KEY must be set when MCP_ENABLED is true; "
                "set a strong random key in .env"
            )
        return self


settings = Settings()
