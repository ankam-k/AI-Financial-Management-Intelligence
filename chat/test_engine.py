"""The chat pipeline: guard, route, select, render, check.

Ordering is the design, so the ordering is what these tests assert. The first
class checks that a refused question never reaches the model at all — which is
the difference between "we filter the output" and ADR-010's "never generated,
never logged, never cached".
"""

from __future__ import annotations

import pytest

from app.analysis.engine import AnalysisResult
from app.chat.models import AnswerStatus, RefusalReason
from app.chat.service import MAX_QUESTION_CHARS, ChatEngine
from app.llm.base import LLMTimeout, LLMUnavailable
from app.llm.null import NullLLMClient
from app.narration.models import Narration, NarrationSource
from tests.narration.conftest import FakeLLMClient

GOOD = {"answer": "You spent more on food in weeks without exercise, which is an association."}


def ask(client, question: str, analysis, narrations, **kwargs):
    return ChatEngine(client).answer(question, analysis, narrations, **kwargs)


class TestTheGuardRunsFirst:
    """⭐ ADR-010: never generated, never logged, never cached."""

    def test_a_prohibited_question_never_reaches_the_model(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        client = FakeLLMClient(GOOD)

        answer = ask(client, "Should I invest my surplus?", analysis, narrations)

        assert answer.status is AnswerStatus.REFUSED
        assert answer.refusal_reason is RefusalReason.PROHIBITED_TOPIC
        assert client.calls == [], "the model must not be called at all"

    def test_the_refusal_is_fixed_text_not_generated(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """A refusal that went through a model would be one the model could
        soften."""
        answer = ask(FakeLLMClient(GOOD), "Should I buy a mutual fund?", analysis, narrations)

        assert "isn't a licensed adviser" in answer.answer
        assert answer.source is NarrationSource.TEMPLATE

    def test_it_is_refused_before_being_classified(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(NullLLMClient(), "Should I invest?", analysis, narrations)

        assert answer.intent is None, "a refused question is never routed"

    def test_a_factual_question_about_a_product_is_answered(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """PDR-027's other half — the case a keyword ban would break."""
        answer = ask(
            NullLLMClient(),
            "How much did I pay in EMIs this quarter?",
            analysis,
            narrations,
        )

        assert answer.status is AnswerStatus.ANSWERED


class TestUnsupportedQuestions:
    def test_an_off_topic_question_is_refused_with_examples(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(NullLLMClient(), "What's the weather tomorrow?", analysis, narrations)

        assert answer.refusal_reason is RefusalReason.NOT_ANSWERABLE_FROM_ANALYSIS
        assert "Things I can answer" in answer.answer

    def test_it_does_not_reach_the_model(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        client = FakeLLMClient(GOOD)

        ask(client, "Who won the cricket?", analysis, narrations)

        assert client.calls == []

    def test_an_empty_question_is_unclear(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(NullLLMClient(), "   ", analysis, narrations)

        assert answer.refusal_reason is RefusalReason.UNCLEAR

    def test_an_overlong_question_is_refused(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(NullLLMClient(), "a" * (MAX_QUESTION_CHARS + 1), analysis, narrations)

        assert answer.refusal_reason is RefusalReason.UNCLEAR


class TestEmptyContext:
    def test_an_intent_with_nothing_behind_it_says_so(
        self, empty_analysis: AnalysisResult
    ) -> None:
        answer = ask(
            NullLLMClient(), "What happened during my trip?", empty_analysis, {}
        )

        assert answer.refusal_reason is RefusalReason.INSUFFICIENT_DATA
        assert "enough recorded data" in answer.answer
        assert answer.intent == "EVENT_CONTEXT", "the routing still happened"

    def test_it_does_not_reach_the_model(self, empty_analysis: AnalysisResult) -> None:
        client = FakeLLMClient(GOOD)

        ask(client, "What happened during my trip?", empty_analysis, {})

        assert client.calls == []

    def test_a_spending_question_over_an_empty_window_is_answered_not_refused(
        self, empty_analysis: AnalysisResult
    ) -> None:
        """Zero spending is a fact the engine reports, so the honest answer is
        "you have no recorded spending" rather than a refusal."""
        from app.narration.renderer import NarrationRenderer

        run = NarrationRenderer(NullLLMClient()).narrate_all(empty_analysis.insights)
        narrations = {item.insight_id: item for item in run.narrations}

        answer = ask(NullLLMClient(), "How much did I spend?", empty_analysis, narrations)

        assert answer.status is AnswerStatus.ANSWERED
        assert "no recorded spending" in answer.answer


class TestTemplateAnswers:
    """The assistant works with the model switched off."""

    def test_it_answers_from_existing_narration(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(NullLLMClient(), "How much did I spend?", analysis, narrations)

        assert answer.status is AnswerStatus.ANSWERED
        assert answer.source is NarrationSource.TEMPLATE
        assert "You spent" in answer.answer

    def test_a_relationship_answer_keeps_its_caveat(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """The correlational disclaimer travels with the claim, never
        separately."""
        answer = ask(
            NullLLMClient(),
            "How has my exercise affected my spending?",
            analysis,
            narrations,
        )

        assert "not a cause" in answer.answer

    def test_an_improvement_answer_refuses_to_invent_a_plan(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(NullLLMClient(), "What should I improve?", analysis, narrations)

        assert "won't invent a plan" in answer.answer

    def test_every_answer_cites_what_it_used(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(NullLLMClient(), "Am I over budget?", analysis, narrations)

        assert answer.citations
        assert all(citation.insight_id for citation in answer.citations)


class TestGeneratedAnswers:
    def test_a_clean_generation_is_used(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(
            FakeLLMClient(GOOD),
            "How has exercise affected my spending?",
            analysis,
            narrations,
        )

        assert answer.source is NarrationSource.LLM
        assert answer.answer == GOOD["answer"]
        assert answer.model == "fake:fake-model"

    def test_the_model_receives_the_question_and_the_findings(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        client = FakeLLMClient(GOOD)

        ask(client, "Am I over budget?", analysis, narrations)

        call = client.calls[0]
        assert "Am I over budget?" in call["user"]
        assert "BUDGET_UTILIZATION" in call["user"]

    def test_the_schema_asks_for_no_citations(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """Citations are the insight ids the context builder selected, recorded
        before generation. A model-authored sources list would be a list it
        could invent."""
        client = FakeLLMClient(GOOD)

        ask(client, "Am I over budget?", analysis, narrations)

        assert set(client.calls[0]["schema"]["properties"]) == {
            "answer",
            "evidence_is_weak",
        }

    def test_generation_can_be_disabled(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        client = FakeLLMClient(GOOD)

        answer = ask(
            client, "How much did I spend?", analysis, narrations, allow_generation=False
        )

        assert answer.source is NarrationSource.TEMPLATE
        assert client.calls == []


class TestHallucinationIsRejected:
    def test_an_invented_number_falls_back(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        client = FakeLLMClient({"answer": "You spent ₹9,876,543 on food this month."})

        answer = ask(client, "How much did I spend?", analysis, narrations)

        assert answer.source is NarrationSource.TEMPLATE
        assert any(f.validator == "provenance" for f in answer.validation_failures)
        assert "9,876,543" not in answer.answer

    def test_a_figure_from_an_unselected_insight_is_still_a_fabrication(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """⭐ It exists in the run, but not in what the model was given — so
        the model cannot have read it."""
        from app.analysis.models import InsightType

        breakdown = next(
            i for i in analysis.insights if i.type is InsightType.SPENDING_BY_CATEGORY
        )
        smuggled = breakdown.metrics["top_category_paise"]
        client = FakeLLMClient({"answer": f"Your habits cost you {smuggled} paise overall."})

        answer = ask(client, "How is my sleep?", analysis, narrations)

        assert answer.source is NarrationSource.TEMPLATE
        assert any(f.validator == "provenance" for f in answer.validation_failures)

    def test_causal_language_about_an_association_falls_back(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        client = FakeLLMClient(
            {"answer": "Your food spending rose because you skipped the gym."}
        )

        answer = ask(
            client, "How has exercise affected spending?", analysis, narrations
        )

        assert answer.source is NarrationSource.TEMPLATE
        assert any(f.validator == "lexical" for f in answer.validation_failures)

    def test_prohibited_advice_in_the_answer_falls_back(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """The guard screens the question; this catches an answer that drifts
        into advice the question never asked for."""
        client = FakeLLMClient(
            {"answer": "You are under budget, so you could invest the surplus in a fund."}
        )

        answer = ask(client, "Am I over budget?", analysis, narrations)

        assert answer.source is NarrationSource.TEMPLATE
        assert any(f.validator == "advice_guard" for f in answer.validation_failures)

    def test_a_stub_answer_falls_back(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        answer = ask(FakeLLMClient({"answer": "Yes."}), "Am I over budget?", analysis, narrations)

        assert answer.source is NarrationSource.TEMPLATE
        assert any(f.validator == "shape" for f in answer.validation_failures)

    def test_the_strictest_tier_in_the_context_wins(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """A reader cannot tell which sentence came from which finding, so an
        answer touching an association is held to correlational language
        throughout."""
        client = FakeLLMClient({"answer": "Your spending rose because of the gym pattern."})

        answer = ask(client, "What should I improve?", analysis, narrations)

        assert answer.source is NarrationSource.TEMPLATE


class TestErrorScenarios:
    @pytest.mark.parametrize(
        "error", [LLMUnavailable("refused"), LLMTimeout("timed out"), RuntimeError("boom")]
    )
    def test_every_client_failure_falls_back_quietly(
        self, analysis: AnalysisResult, narrations: dict[str, Narration], error: Exception
    ) -> None:
        answer = ask(
            FakeLLMClient(error=error), "How much did I spend?", analysis, narrations
        )

        assert answer.status is AnswerStatus.ANSWERED
        assert answer.source is NarrationSource.TEMPLATE
        assert type(error).__name__ in (answer.fallback_reason or "")


class TestStatelessness:
    def test_the_engine_keeps_nothing_between_questions(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """⭐ SRS-7.7 — single-turn is enforced by there being no mechanism
        for anything else."""
        engine = ChatEngine(NullLLMClient())

        first = engine.answer("Am I over budget?", analysis, narrations)
        second = engine.answer("Am I over budget?", analysis, narrations)

        assert first.as_dict() == second.as_dict()

    def test_a_follow_up_is_answered_independently(
        self, analysis: AnalysisResult, narrations: dict[str, Narration]
    ) -> None:
        """"What about groceries?" has no antecedent to resolve, so it routes
        on its own words alone — and here, nowhere."""
        engine = ChatEngine(NullLLMClient())
        engine.answer("Which category did I spend most on?", analysis, narrations)

        follow_up = engine.answer("What about it?", analysis, narrations)

        assert follow_up.status is AnswerStatus.REFUSED
