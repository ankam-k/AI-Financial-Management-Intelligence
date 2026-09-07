"""The no-model provider. The default.

Not a test double — this is what runs in production until someone configures
a provider, and it is why the product is fully usable with the model absent
(SRS-7.6, NFR-7). Every narration then comes from the deterministic template
renderer, which loses fluency and nothing factual.
"""

from __future__ import annotations

from typing import Any

from app.llm.base import LLMHealth, LLMUnavailable


class NullLLMClient:
    """Refuses every request, immediately and predictably."""

    provider = "none"

    def __init__(self, model: str = "none") -> None:
        self.model = model

    def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        raise LLMUnavailable(
            "No LLM provider configured. Set AFI_LLM_PROVIDER=ollama to enable "
            "generated narration; template narration is served meanwhile."
        )

    def health(self) -> LLMHealth:
        return LLMHealth(
            provider=self.provider,
            model=self.model,
            available=False,
            detail="No provider configured — narrations are rendered from templates.",
        )
