"""The model-facing contract.

Deliberately narrow: one method that takes a system prompt, a user prompt and
a JSON schema, and returns a parsed object. There is no streaming, no chat
history, no tool calling, and no free-text completion — every one of those
would widen the surface the validators downstream have to check.

Single-turn is enforced by the absence of a mechanism for anything else
(SRS-7.7). There is no ``conversation_id`` here because there is no
conversation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class LLMError(Exception):
    """Base for every failure reaching a model.

    Callers catch this one type and fall back. They are not expected to
    distinguish a timeout from a refused connection — both mean "no usable
    generation", and both take the same path.
    """


class LLMUnavailable(LLMError):
    """No provider configured, or the service could not be reached."""


class LLMTimeout(LLMError):
    """The model did not answer within the configured budget."""


class LLMProtocolError(LLMError):
    """The service answered, but not with what it promised.

    Malformed JSON, a missing field, an HTTP error body. Kept distinct from
    ``LLMUnavailable`` because it usually means a misconfigured model name
    rather than a service that is down.
    """


@dataclass(frozen=True, slots=True)
class LLMHealth:
    """What ``/api/narrations/status`` reports."""

    provider: str
    model: str
    available: bool
    detail: str


@runtime_checkable
class LLMClient(Protocol):
    """A source of JSON-constrained completions."""

    #: Provider identifier, e.g. ``"ollama"``. Reported on every narration.
    provider: str
    #: Model identifier, e.g. ``"qwen2.5:7b-instruct"``.
    model: str

    def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a parsed object conforming to ``schema``.

        Raises :class:`LLMError` on any failure. Implementations must not
        return partial or unparsed output — a caller that has to guess whether
        it received a generation cannot validate one.
        """

    def health(self) -> LLMHealth:
        """Report reachability without raising."""
