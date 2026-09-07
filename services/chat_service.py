"""Loads a window, narrates it, and hands both to the chat engine.

The only file in the chat path that touches a database — which is the
structural form of "the LLM never queries the database directly". There is no
handle below this point for it to query one through.

Narration is rendered from templates rather than generated: the chat engine
quotes those explanations, and paying for a model twice in one request (once
to narrate an insight, again to answer a question about it) buys nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analysis.engine import AnalysisResult
from app.chat.models import ChatAnswer
from app.chat.service import ChatEngine
from app.models.user import User
from app.narration.models import Narration
from app.narration.renderer import NarrationRenderer
from app.services.analysis_service import AnalysisService


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """One question and its answer. Not stored anywhere."""

    answer: ChatAnswer
    analysis: AnalysisResult

    def as_dict(self) -> dict:
        payload = self.answer.as_dict()
        payload["window"] = self.analysis.run["window"]
        return payload


class ChatService:
    """Answers a question about the user's own recorded data."""

    def __init__(
        self,
        analysis: AnalysisService,
        renderer: NarrationRenderer,
        engine: ChatEngine,
    ) -> None:
        self._analysis = analysis
        self._renderer = renderer
        self._engine = engine

    def ask(
        self,
        user: User,
        question: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int | None = None,
        allow_generation: bool = True,
    ) -> ChatTurn:
        """Answer one question. No prior turn is loaded, because none is kept."""
        result = self._analysis.run(
            user, start_date=start_date, end_date=end_date, days=days
        )

        run = self._renderer.narrate_all(
            result.insights + result.notices,
            display_name=user.display_name,
            allow_generation=False,
        )
        narrations: dict[str, Narration] = {
            item.insight_id: item for item in run.narrations
        }

        answer = self._engine.answer(
            question, result, narrations, allow_generation=allow_generation
        )
        return ChatTurn(answer=answer, analysis=result)
