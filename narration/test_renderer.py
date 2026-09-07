"""Orchestration: when a generation is used, and when it is thrown away.

Every branch is driven through a scripted fake client, so the whole fallback
path is covered without Ollama installed.
"""

from __future__ import annotations

import pytest

from app.analysis.models import Insight, InsightType
from app.llm.base import LLMProtocolError, LLMTimeout, LLMUnavailable
from app.llm.null import NullLLMClient
from app.narration.models import NarrationSource
from app.narration.renderer import NarrationRenderer
from tests.narration.conftest import FakeLLMClient

GOOD = {
    "observation": "Your food spending was higher in weeks without exercise.",
    "evidence": "The weeks group cleanly on that split.",
    "interpretation": "The two are associated, which does not prove causation.",
    "suggestion": "You may want to watch food spending in those weeks.",
}


def render_with(client, insight: Insight, **kwargs):
    return NarrationRenderer(client).narrate(insight, **kwargs)


class TestGeneratedPath:
    def test_a_clean_generation_is_used(self, relationship_insight: Insight) -> None:
        narration = render_with(FakeLLMClient(GOOD), relationship_insight)

        assert narration.source is NarrationSource.LLM
        assert narration.observation == GOOD["observation"]
        assert narration.model == "fake:fake-model"
        assert narration.validation_failures == ()
        assert narration.fallback_reason is None

    def test_confidence_is_never_taken_from_the_model(
        self, relationship_insight: Insight
    ) -> None:
        """⭐ Even a fully accepted generation gets its confidence sentence
        from code. The model is never asked for one, so it cannot invent one."""
        client = FakeLLMClient({**GOOD, "confidence": "I am 99.99% certain."})

        narration = render_with(client, relationship_insight)

        assert narration.source is NarrationSource.LLM
        assert "99.99" not in narration.confidence
        assert narration.confidence_value == relationship_insight.confidence

    def test_the_model_receives_the_insight_and_a_schema(
        self, relationship_insight: Insight
    ) -> None:
        client = FakeLLMClient(GOOD)

        render_with(client, relationship_insight)

        call = client.calls[0]
        assert "BEHAVIOR_RELATIONSHIP" in call["user"]
        assert call["schema"]["additionalProperties"] is False

    def test_an_omitted_suggestion_is_allowed(
        self, relationship_insight: Insight
    ) -> None:
        client = FakeLLMClient({k: v for k, v in GOOD.items() if k != "suggestion"})

        narration = render_with(client, relationship_insight)

        assert narration.source is NarrationSource.LLM
        assert narration.suggestion is None


class TestHallucinationIsRejected:
    """The generation is discarded whole. It is never edited to make it pass."""

    def test_an_invented_number_falls_back(self, relationship_insight: Insight) -> None:
        client = FakeLLMClient({**GOOD, "evidence": "You spent ₹9,876,543 on food."})

        narration = render_with(client, relationship_insight)

        assert narration.source is NarrationSource.TEMPLATE
        assert any(f.validator == "provenance" for f in narration.validation_failures)
        assert "9876543" not in narration.evidence

    def test_causal_language_falls_back(self, relationship_insight: Insight) -> None:
        client = FakeLLMClient(
            {**GOOD, "interpretation": "Your spending rose because you skipped the gym."}
        )

        narration = render_with(client, relationship_insight)

        assert narration.source is NarrationSource.TEMPLATE
        assert any(f.validator == "lexical" for f in narration.validation_failures)

    def test_prohibited_advice_falls_back(self, relationship_insight: Insight) -> None:
        client = FakeLLMClient({**GOOD, "suggestion": "Consider a mutual fund."})

        narration = render_with(client, relationship_insight)

        assert narration.source is NarrationSource.TEMPLATE
        assert any(f.validator == "advice_guard" for f in narration.validation_failures)

    def test_a_stub_generation_falls_back(self, relationship_insight: Insight) -> None:
        client = FakeLLMClient({"observation": "ok", "evidence": "", "interpretation": ""})

        narration = render_with(client, relationship_insight)

        assert narration.source is NarrationSource.TEMPLATE
        assert any(f.validator == "shape" for f in narration.validation_failures)

    def test_the_fallback_is_the_full_template_not_a_patch(
        self, relationship_insight: Insight
    ) -> None:
        """Failure discards; it never repairs — so a rejected generation
        leaves no trace in the prose."""
        from app.narration import templates

        client = FakeLLMClient({**GOOD, "evidence": "You spent ₹9,876,543."})
        expected = templates.render(relationship_insight)

        narration = render_with(client, relationship_insight)

        assert (
            narration.observation,
            narration.evidence,
            narration.interpretation,
        ) == expected[:3]

    def test_every_failing_validator_is_recorded(
        self, relationship_insight: Insight
    ) -> None:
        client = FakeLLMClient(
            {
                "observation": "Spending rose ₹9,999,999 because of the gym.",
                "evidence": "Consider a mutual fund.",
                "interpretation": "It is associated with that.",
            }
        )

        narration = render_with(client, relationship_insight)
        validators = {f.validator for f in narration.validation_failures}

        assert {"provenance", "lexical", "advice_guard"} <= validators


class TestErrorScenarios:
    @pytest.mark.parametrize(
        "error",
        [
            LLMUnavailable("connection refused"),
            LLMTimeout("timed out after 60s"),
            LLMProtocolError("model returned prose"),
        ],
    )
    def test_every_client_failure_falls_back_quietly(
        self, relationship_insight: Insight, error: Exception
    ) -> None:
        narration = render_with(FakeLLMClient(error=error), relationship_insight)

        assert narration.source is NarrationSource.TEMPLATE
        assert type(error).__name__ in narration.fallback_reason
        assert narration.validation_failures == ()

    def test_an_unexpected_client_error_is_contained(
        self, relationship_insight: Insight
    ) -> None:
        """A misbehaving adapter is a bug in that adapter. It must not take
        down a request the template could have answered."""
        narration = render_with(
            FakeLLMClient(error=RuntimeError("boom")), relationship_insight
        )

        assert narration.source is NarrationSource.TEMPLATE
        assert "RuntimeError" in narration.fallback_reason

    def test_no_provider_configured_uses_templates(
        self, relationship_insight: Insight
    ) -> None:
        narration = render_with(NullLLMClient(), relationship_insight)

        assert narration.source is NarrationSource.TEMPLATE
        assert "LLMUnavailable" in narration.fallback_reason

    def test_generation_can_be_disabled_per_request(
        self, relationship_insight: Insight
    ) -> None:
        client = FakeLLMClient(GOOD)

        narration = render_with(client, relationship_insight, allow_generation=False)

        assert narration.source is NarrationSource.TEMPLATE
        assert client.calls == [], "the model must not be called at all"


class TestWholeRun:
    def test_every_insight_is_narrated(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        insights = tuple(every_insight.values())

        run = NarrationRenderer(NullLLMClient()).narrate_all(insights)

        assert len(run.narrations) == len(insights)
        assert run.stats["total"] == len(insights)
        assert run.stats["generated"] == 0

    def test_the_generation_budget_is_spent_on_the_highest_tier(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        """A local 7B model is slow, so the budget goes where prose helps most.
        A total is already legible as a number; an association is not."""
        insights = tuple(every_insight.values())
        client = FakeLLMClient(GOOD)

        run = NarrationRenderer(client, max_generated=1).narrate_all(insights)

        generated = [n for n in run.narrations if n.source is NarrationSource.LLM]
        assert len(generated) == 1
        assert generated[0].tier == "T3"

    def test_insights_beyond_the_budget_are_still_explained(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        """The budget changes the prose, never the coverage."""
        insights = tuple(every_insight.values())

        run = NarrationRenderer(FakeLLMClient(GOOD), max_generated=2).narrate_all(insights)

        assert all(n.observation for n in run.narrations)
        assert run.stats["templated"] == len(insights) - 2

    def test_stats_report_how_the_prose_was_produced(
        self, relationship_insight: Insight
    ) -> None:
        client = FakeLLMClient({**GOOD, "evidence": "You spent ₹9,876,543."})

        run = NarrationRenderer(client).narrate_all((relationship_insight,))

        assert run.stats == {
            "total": 1,
            "generated": 0,
            "templated": 1,
            "generation_attempted": 1,
            "rejected_by_validation": 1,
            "provider": "fake",
            "model": "fake-model",
        }

    def test_an_empty_run_is_not_an_error(self) -> None:
        run = NarrationRenderer(NullLLMClient()).narrate_all(())

        assert run.narrations == ()
        assert run.stats["total"] == 0


class TestArithmeticInsightsAreLessConstrained:
    def test_causal_phrasing_is_accepted_for_a_t1_claim(
        self, total_insight: Insight
    ) -> None:
        """PDR-036 — an accounting identity may say "because"."""
        client = FakeLLMClient(
            {
                "observation": "Your total rose over the window.",
                "evidence": "A single large payment cleared during the period.",
                "interpretation": "The total rose because that payment cleared.",
            }
        )

        narration = render_with(client, total_insight)

        assert narration.source is NarrationSource.LLM

    def test_a_t1_narration_carries_no_confidence_figure(
        self, total_insight: Insight
    ) -> None:
        narration = render_with(FakeLLMClient(GOOD), total_insight)

        assert narration.confidence_value is None
        assert "no confidence figure applies" in narration.confidence
