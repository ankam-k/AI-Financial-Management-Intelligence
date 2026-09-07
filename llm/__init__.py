"""LLM adapters — the only place in the application that talks to a model.

Everything above this package works against the :class:`LLMClient` protocol,
so swapping Qwen for another model is a configuration change and a new file
here. Nothing in ``app/narration/`` imports this package's implementations;
the client is injected.

The default provider is ``none``. A fresh clone runs, serves narrations, and
passes its tests with no Ollama installed — the deterministic template
renderer is not a stub for when the model is missing, it is the baseline the
model has to improve on (SRS-7.5, ADR-009).
"""

from app.llm.base import (
    LLMClient,
    LLMError,
    LLMHealth,
    LLMProtocolError,
    LLMTimeout,
    LLMUnavailable,
)
from app.llm.factory import build_llm_client
from app.llm.null import NullLLMClient
from app.llm.ollama import OllamaClient

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMHealth",
    "LLMProtocolError",
    "LLMTimeout",
    "LLMUnavailable",
    "NullLLMClient",
    "OllamaClient",
    "build_llm_client",
]
