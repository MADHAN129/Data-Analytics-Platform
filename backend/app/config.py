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
    FRONTEND_URL: str = "http://localhost:3000"

    # ── LLM Settings ────────────────────────────────────────────────────────
    # Provider selection: "auto", "openrouter", "grok", "local_proxy", "openai", "local", "mock"
    LLM_PROVIDER: str = "auto"
    LLM_USE_MOCK: bool = False

    # Local LLM (Ollama / vLLM) - Existing default / fallback
    VLLM_API_URL: str = "http://localhost:11434/v1"
    VLLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen2.5-coder:3b"

    # OpenRouter API (https://openrouter.ai)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct"
    OPENROUTER_SITE_URL: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "Data-Analyzer"

    # Grok / xAI API (https://x.ai)
    GROK_API_KEY: str = ""
    XAI_API_KEY: str = ""  # Alias for GROK_API_KEY
    GROK_BASE_URL: str = "https://api.x.ai/v1"
    GROK_MODEL: str = "grok-2-latest"

    # GroqCloud API (https://groq.com)
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Local Proxy / Custom OpenAI-compatible Proxy (LiteLLM, LocalAI, vLLM proxy, etc.)
    LOCAL_PROXY_URL: str = ""
    LOCAL_PROXY_API_KEY: str = ""
    LOCAL_PROXY_MODEL: str = ""

    # OpenAI API (Optional direct support)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

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
