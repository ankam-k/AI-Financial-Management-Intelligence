"""Chat schemas.

Note what the request does **not** accept: a conversation id, a history array,
a previous-turn reference. Single-turn is enforced by there being no field to
put a prior turn in (SRS-7.7, PDR-037🟠).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.chat.intents import SUPPORTED_EXAMPLES
from app.chat.models import ChatAnswer
from app.chat.service import MAX_QUESTION_CHARS
from app.schemas.insight import WindowRead
from app.schemas.narration import ValidationFailureRead
from app.services.chat_service import ChatTurn


class ChatRequest(BaseModel):
    """One question about the user's own recorded data."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    days: int | None = Field(default=None, ge=1, le=730)
    start_date: str | None = None
    end_date: str | None = None
    #: False forces a template answer. Useful for a fast reply, and the
    #: default when no model is configured.
    generate: bool = True


class CitationRead(BaseModel):
    """An insight the answer drew on, so a claim can be opened and checked."""

    insight_id: str
    insight_type: str
    tier: str


class ChatResponse(BaseModel):
    """An answer, or a refusal that says why.

    A refusal is a 200, not an error. "I won't recommend a fund" and "I have
    no data for that" are both correct outcomes of a well-formed request, and
    a client that had to catch them as exceptions would be a client that
    treats the product's most important behaviour as a failure.
    """

    question: str
    status: str
    answer: str
    intent: str | None
    refusal_reason: str | None
    source: str
    model: str | None
    citations: list[CitationRead] = Field(default_factory=list)
    validation_failures: list[ValidationFailureRead] = Field(default_factory=list)
    fallback_reason: str | None
    context_summary: dict[str, Any] = Field(default_factory=dict)
    window: WindowRead

    @classmethod
    def from_domain(cls, turn: ChatTurn) -> "ChatResponse":
        return cls(**turn.as_dict())


class ChatCapabilitiesRead(BaseModel):
    """What the assistant can be asked, and what it will not do."""

    examples: list[str] = Field(default_factory=lambda: list(SUPPORTED_EXAMPLES))
    intents: list[str]
    max_question_chars: int = MAX_QUESTION_CHARS
    single_turn: bool = True
    note: str = (
        "Each question is answered independently. No conversation history is "
        "kept on the server, and no previous question is visible to the model."
    )


__all__ = [
    "ChatAnswer",
    "ChatCapabilitiesRead",
    "ChatRequest",
    "ChatResponse",
    "CitationRead",
]
