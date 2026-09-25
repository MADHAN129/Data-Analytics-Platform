"""Unit tests for Multi-Provider LLM Infrastructure (OpenRouter, Grok, Local Proxy, Local LLM, Fallback)."""

import pytest
from unittest.mock import patch, MagicMock

from app.config import settings
from app.services.llm_service import LLMService, LLMProviderConfig


class TestLLMProviderResolution:
    def test_default_fallback_to_local_when_no_keys(self):
        """When no external keys are present, LLMService resolves to local LLM."""
        with patch.object(settings, "LLM_PROVIDER", "auto"), \
             patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(settings, "OPENROUTER_API_KEY", ""), \
             patch.object(settings, "GROK_API_KEY", ""), \
             patch.object(settings, "XAI_API_KEY", ""), \
             patch.object(settings, "LOCAL_PROXY_URL", ""), \
             patch.object(settings, "OPENAI_API_KEY", ""), \
             patch.object(settings, "VLLM_API_URL", "http://localhost:11434/v1"), \
             patch.object(settings, "LLM_MODEL", "qwen2.5-coder:3b"):
            
            service = LLMService()
            config = service.resolve_provider()
            
            assert config.provider == "local"
            assert config.base_url == "http://localhost:11434/v1"
            assert config.model == "qwen2.5-coder:3b"

    def test_openrouter_selected_when_key_present(self):
        """When OPENROUTER_API_KEY is present and provider is auto, OpenRouter is selected."""
        with patch.object(settings, "LLM_PROVIDER", "auto"), \
             patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(settings, "OPENROUTER_API_KEY", "sk-or-v1-test-key-12345"), \
             patch.object(settings, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"), \
             patch.object(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"):
            
            service = LLMService()
            config = service.resolve_provider()
            
            assert config.provider == "openrouter"
            assert config.base_url == "https://openrouter.ai/api/v1"
            assert config.api_key == "sk-or-v1-test-key-12345"
            assert config.model == "meta-llama/llama-3.3-70b-instruct"
            assert "HTTP-Referer" in config.headers

    def test_grok_selected_when_key_present(self):
        """When GROK_API_KEY is present (and no OpenRouter key), Grok is selected."""
        with patch.object(settings, "LLM_PROVIDER", "auto"), \
             patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(settings, "OPENROUTER_API_KEY", ""), \
             patch.object(settings, "GROK_API_KEY", "xai-test-key-67890"), \
             patch.object(settings, "GROK_MODEL", "grok-2-latest"), \
             patch.object(settings, "GROK_BASE_URL", "https://api.x.ai/v1"):
            
            service = LLMService()
            config = service.resolve_provider()
            
            assert config.provider == "grok"
            assert config.base_url == "https://api.x.ai/v1"
            assert config.api_key == "xai-test-key-67890"
            assert config.model == "grok-2-latest"

    def test_local_proxy_selected_when_url_present(self):
        """When LOCAL_PROXY_URL is present (and no cloud keys), Local Proxy is selected."""
        with patch.object(settings, "LLM_PROVIDER", "auto"), \
             patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(settings, "OPENROUTER_API_KEY", ""), \
             patch.object(settings, "GROK_API_KEY", ""), \
             patch.object(settings, "XAI_API_KEY", ""), \
             patch.object(settings, "LOCAL_PROXY_URL", "http://localhost:4000/v1"), \
             patch.object(settings, "LOCAL_PROXY_MODEL", "custom-model"):
            
            service = LLMService()
            config = service.resolve_provider()
            
            assert config.provider == "local_proxy"
            assert config.base_url == "http://localhost:4000/v1"
            assert config.model == "custom-model"

    def test_explicit_provider_override(self):
        """When LLM_PROVIDER is explicitly set, it overrides auto-selection."""
        with patch.object(settings, "LLM_PROVIDER", "grok"), \
             patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(settings, "OPENROUTER_API_KEY", "sk-or-key"), \
             patch.object(settings, "GROK_API_KEY", "xai-key"), \
             patch.object(settings, "GROK_MODEL", "grok-2-latest"):
            
            service = LLMService()
            config = service.resolve_provider()
            
            assert config.provider == "grok"
            assert config.model == "grok-2-latest"

    def test_get_provider_info_metadata(self):
        """get_provider_info returns comprehensive diagnostic details."""
        with patch.object(settings, "LLM_PROVIDER", "openrouter"), \
             patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(settings, "OPENROUTER_API_KEY", "sk-or-key"), \
             patch.object(settings, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"):
            
            service = LLMService()
            info = service.get_provider_info()
            
            assert info["active_provider"] == "openrouter"
            assert info["model"] == "meta-llama/llama-3.3-70b-instruct"
            assert info["has_api_key"] is True
            assert info["fallback_provider"] == "local"


class TestLLMExecutionAndFallback:
    def test_primary_provider_success(self):
        """When the primary cloud provider succeeds, return the result."""
        service = LLMService()
        mock_config = LLMProviderConfig(
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model="test-model",
        )

        with patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(service, "resolve_provider", return_value=mock_config), \
             patch.object(service, "_execute_chat_completion", return_value="SELECT * FROM users;"):
            
            result = service._call_llm([{"role": "user", "content": "list users"}])
            assert result == "SELECT * FROM users;"

    def test_fallback_to_local_llm_on_cloud_provider_failure(self):
        """When cloud provider fails, automatically fallback to local LLM."""
        service = LLMService()
        cloud_config = LLMProviderConfig(
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model="test-model",
        )
        local_config = LLMProviderConfig(
            provider="local",
            base_url="http://localhost:11434/v1",
            api_key="",
            model="qwen2.5-coder:3b",
        )

        def mock_execute(cfg, msgs, temperature, max_tokens):
            if cfg.provider == "openrouter":
                return None  # Simulate network / rate-limit failure
            if cfg.provider == "local":
                return "SELECT * FROM users_from_local;"
            return None

        with patch.object(settings, "LLM_USE_MOCK", False), \
             patch.object(service, "resolve_provider", return_value=cloud_config), \
             patch.object(service, "_get_local_provider_config", return_value=local_config), \
             patch.object(service, "_execute_chat_completion", side_effect=mock_execute):
            
            result = service._call_llm([{"role": "user", "content": "list users"}])
            assert result == "SELECT * FROM users_from_local;"

    def test_mock_mode_returns_none(self):
        """When mock mode is enabled, _call_llm returns None without making HTTP calls."""
        service = LLMService()
        with patch.object(settings, "LLM_USE_MOCK", True):
            result = service._call_llm([{"role": "user", "content": "hello"}])
            assert result is None
