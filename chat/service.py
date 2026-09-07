"""The pipeline: guard, route, select, render, check.

Ordering is the design. The guard runs before intent detection so a prohibited
question is refused without ever being classified, contextualised, or sent
anywhere. Intent detection runs before context building so nothing is loaded
for a question the system cannot answer. The template answer is built before
generation so a rejected generation falls back to a value that already exists.

This module performs no I/O. The model client arrives through the
``LLMClient`` protocol; the analysis result and narrations arrive already
loaded.
"""

from __future__ import annotations

from app.analysis.engine import AnalysisResult
from app.analysis.models import InsightTier
from app.chat import templates
from app.chat.context import ChatContext, build_context
from app.chat.guard import REFUSAL_TEXT, screen_question
from app.chat.intents import SUPPORTED_EXAMPLES, detect_intent
from app.chat.models import AnswerStatus, ChatAnswer, Citation, RefusalReason
from app.chat.prompts import OUTPUT_SCHEMA, build_prompt
from app.llm.base import LLMClient, LLMError
from app.narration.models import Narration, NarrationSource, ValidationFailure
from app.narration.validators import check_advice, check_lexical, check_provenance

#: Longer than this is not a question, it is a document.
MAX_QUESTION_CHARS = 500

#: Shorter than this cannot be routed.
MIN_ANSWER_CHARS = 20


def _not_answerable_text() -> str:
    examples = "\n".join(f'- "{item}"' for item in SUPPORTED_EXAMPLES)
    return (
        "I can't answer that from your recorded data. This assistant only "
        "reports what the analysis engine has already worked out, so if there "
        "is no finding behind a question, I have nothing to ground an answer "
        "in.\n\nThings I can answer:\n" + examples
    )


class ChatEngine:
    """Answers one question. Holds no state between calls, by design."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def answer(
        self,
        question: str,
        analysis: AnalysisResult,
        narrations: dict[str, Narration],
        *,
        allow_generation: bool = True,
    ) -> ChatAnswer:
        text = question.strip()

        if not text or len(text) > MAX_QUESTION_CHARS:
            return ChatAnswer(
                question=text[:MAX_QUESTION_CHARS],
                status=AnswerStatus.REFUSED,
                refusal_reason=RefusalReason.UNCLEAR,
                answer=(
                    "I didn't catch a question there. Ask me something about your "
                    "spending, your habits, or a life event you recorded."
                ),
            )

        # ── The guard, first. Nothing downstream ever sees a refused question.
        verdict = screen_question(text)
        if verdict.is_prohibited:
            return ChatAnswer(
                question=text,
                status=AnswerStatus.REFUSED,
                refusal_reason=RefusalReason.PROHIBITED_TOPIC,
                answer=REFUSAL_TEXT,
                context_summary={"guard": verdict.detail},
            )

        # ── Intent → capability. No match is a first-class outcome.
        match = detect_intent(text)
        if match.intent is None:
            return ChatAnswer(
                question=text,
                status=AnswerStatus.REFUSED,
                refusal_reason=RefusalReason.NOT_ANSWERABLE_FROM_ANALYSIS,
                answer=_not_answerable_text(),
                context_summary={"routing": match.matched},
            )

        context = build_context(match.intent, analysis, narrations)
        citations = tuple(
            Citation(
                insight_id=insight.id,
                insight_type=insight.type.value,
                tier=insight.tier.value,
            )
            for insight in context.insights
        )

        if context.is_empty:
            return ChatAnswer(
                question=text,
                status=AnswerStatus.REFUSED,
                refusal_reason=RefusalReason.INSUFFICIENT_DATA,
                answer=templates.EMPTY_CONTEXT_TEXT,
                intent=match.intent.value,
                context_summary=context.summary(),
            )

        return self._render(text, context, citations, allow_generation)

    # ── Rendering ───────────────────────────────────────────────────────────

    def _render(
        self,
        question: str,
        context: ChatContext,
        citations: tuple[Citation, ...],
        allow_generation: bool,
    ) -> ChatAnswer:
        fallback = templates.render(question, context)

        def as_template(reason: str | None, failures: tuple[ValidationFailure, ...] = ()) -> ChatAnswer:
            return ChatAnswer(
                question=question,
                status=AnswerStatus.ANSWERED,
                answer=fallback,
                intent=context.intent.value,
                source=NarrationSource.TEMPLATE,
                citations=citations,
                validation_failures=failures,
                fallback_reason=reason,
                context_summary=context.summary(),
            )

        if not allow_generation:
            return as_template("Generation disabled for this request.")

        system, user = build_prompt(question, context)

        try:
            raw = self._client.complete_json(system=system, user=user, schema=OUTPUT_SCHEMA)
        except LLMError as exc:
            return as_template(f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            return as_template(f"Unexpected client error: {type(exc).__name__}: {exc}")

        generated = raw.get("answer")
        if not isinstance(generated, str) or len(generated.strip()) < MIN_ANSWER_CHARS:
            return as_template(
                "Generation rejected by 1 validator check(s).",
                (ValidationFailure("shape", "answer is missing or too short"),),
            )

        sections = {"answer": generated.strip()}
        failures = [
            *check_provenance(sections, context.allowed_numbers()),
            *check_lexical(sections, _tier_for(context)),
            *check_advice(sections),
        ]
        if failures:
            return as_template(
                f"Generation rejected by {len(failures)} validator check(s).",
                tuple(failures),
            )

        return ChatAnswer(
            question=question,
            status=AnswerStatus.ANSWERED,
            answer=generated.strip(),
            intent=context.intent.value,
            source=NarrationSource.LLM,
            model=f"{self._client.provider}:{self._client.model}",
            citations=citations,
            context_summary=context.summary(),
        )


def _tier_for(context: ChatContext) -> InsightTier:
    """Which language rules the answer is held to.

    An answer that draws on a correlational finding is held to correlational
    language, even if it also mentions a total. The strictest tier in the
    context wins, because the reader cannot tell which sentence came from
    which finding.
    """
    tiers = {insight.tier for insight in context.insights}
    if InsightTier.T3_CORRELATIONAL in tiers:
        return InsightTier.T3_CORRELATIONAL
    if InsightTier.T2_COMPARATIVE in tiers:
        return InsightTier.T2_COMPARATIVE
    return InsightTier.T1_DESCRIPTIVE
