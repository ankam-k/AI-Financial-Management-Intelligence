"""Chat endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.api.deps import ChatServiceDep, CurrentUser
from app.chat.intents import Intent
from app.domain.errors import ValidationError
from app.schemas.chat import ChatCapabilitiesRead, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _parse(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"'{field}' must be an ISO date (YYYY-MM-DD)") from exc


@router.post("", response_model=ChatResponse, summary="Ask one question")
def ask(payload: ChatRequest, user: CurrentUser, chat: ChatServiceDep) -> ChatResponse:
    """Answer a question about the user's own recorded data.

    **Single-turn.** There is no conversation id and no history parameter:
    every question is answered independently from the analysis window, and no
    previous turn is visible to the model (SRS-7.7).

    A refusal is a 200 with `status: "REFUSED"` and a `refusal_reason`.
    Declining to recommend a financial product, and having no data to answer
    from, are both correct outcomes of a well-formed request.
    """
    turn = chat.ask(
        user,
        payload.question,
        start_date=_parse(payload.start_date, "start_date"),
        end_date=_parse(payload.end_date, "end_date"),
        days=payload.days,
        allow_generation=payload.generate,
    )
    return ChatResponse.from_domain(turn)


@router.get(
    "/capabilities",
    response_model=ChatCapabilitiesRead,
    summary="What the assistant can be asked",
)
def read_capabilities() -> ChatCapabilitiesRead:
    """The intent map, as starter questions.

    Exposed so the client's suggested questions come from the routing rules
    rather than a second hand-maintained list that can drift from them.
    """
    return ChatCapabilitiesRead(intents=[intent.value for intent in Intent])
