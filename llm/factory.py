"""Provider selection.

The switch point ADR-008 needs: replacing Qwen with another model is a new
module here plus one config value. Nothing above this file names a provider.
"""

from __future__ import annotations

from app.core.config import Settings, settings as default_settings
from app.llm.base import LLMClient
from app.llm.null import NullLLMClient
from app.llm.ollama import OllamaClient


def build_llm_client(settings: Settings = default_settings) -> LLMClient:
    """Construct the configured client.

    An unknown provider name falls back to :class:`NullLLMClient` rather than
    raising. A typo in an environment variable should degrade narration to
    templates, not stop the API from starting.
    """
    provider = (settings.llm_provider or "none").strip().lower()

    if provider == "ollama":
        return OllamaClient(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
        )

    return NullLLMClient()
