import os
from typing import Optional

from querymind.llm.base import LLMClient
from querymind.llm.openai_compatible_client import OpenAICompatibleLLMClient


def create_llm_client_from_env() -> Optional[LLMClient]:
    if os.getenv("QUERYMIND_LLM_ENABLED", "").lower() not in {"1", "true", "yes"}:
        return None

    provider = os.getenv("QUERYMIND_LLM_PROVIDER", "openai-compatible").lower()
    if provider in {"openai-compatible", "deepseek", "openai"}:
        api_key = os.getenv("QUERYMIND_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            return None
        return OpenAICompatibleLLMClient(
            api_key=api_key,
            base_url=os.getenv("QUERYMIND_LLM_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("QUERYMIND_LLM_MODEL", "deepseek-chat"),
            max_tokens=int(os.getenv("QUERYMIND_LLM_MAX_TOKENS", "2048")),
            timeout=int(os.getenv("QUERYMIND_LLM_TIMEOUT", "60")),
            max_retries=int(os.getenv("QUERYMIND_LLM_MAX_RETRIES", "2")),
        )

    if provider == "anthropic":
        from querymind.llm.anthropic_client import AnthropicLLMClient

        return AnthropicLLMClient(
            model=os.getenv("QUERYMIND_LLM_MODEL", "claude-sonnet-4-5"),
            api_key=os.getenv("QUERYMIND_LLM_API_KEY") or None,
            max_tokens=int(os.getenv("QUERYMIND_LLM_MAX_TOKENS", "2048")),
        )

    raise ValueError(f"Unsupported QUERYMIND_LLM_PROVIDER: {provider}")
