"""The deterministic renderer.

The most valuable test here runs the full validator suite over template
output. Templates are correct by construction — every number they print is
read from the insight — but "by construction" is an argument, and the
validators are a check. A template that drifted into causal phrasing for a T3
claim, or cited a value the payload truncates away, fails the build exactly as
a model would.
"""

from __future__ import annotations

import pytest

from app.analysis.models import Insight, InsightTier, InsightType
from app.narration import templates
from app.narration.payload import allowed_numbers, build_payload
from app.narration.validators import validate


class TestCoverage:
    @pytest.mark.parametrize("insight_type", list(InsightType), ids=lambda t: t.value)
    def test_every_insight_type_has_a_template(self, insight_type: InsightType) -> None:
        """An insight the product cannot explain without a model is an insight
        it cannot explain at all — the model is optional."""
        assert insight_type in templates.TEMPLATES

    def test_the_fixture_covers_every_type(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        """Guards the tests below: a missing type would make them silently
        weaker rather than failing."""
        assert set(every_insight) == set(InsightType)


class TestRendering:
    def test_every_type_renders_four_usable_sections(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        for insight_type, insight in every_insight.items():
            observation, evidence, interpretation, suggestion = templates.render(insight)

            for name, text in (
                ("observation", observation),
                ("evidence", evidence),
                ("interpretation", interpretation),
            ):
                assert len(text.strip()) >= 20, f"{insight_type.value}.{name} too short"
            assert suggestion is None or len(suggestion.strip()) >= 20

    def test_rendering_is_deterministic(self, relationship_insight: Insight) -> None:
        assert templates.render(relationship_insight) == templates.render(
            relationship_insight
        )

    def test_money_is_formatted_from_integer_paise(self) -> None:
        assert templates.money(412050) == "₹4,120.50"
        assert templates.money(5) == "₹0.05"
        assert templates.money(100000000) == "₹1,000,000.00"

    def test_percentages_are_formatted_from_ratios(self) -> None:
        assert templates.percent(0.4939) == "49.4%"
        assert templates.percent(0.4939, 2) == "49.39%"


class TestTemplateOutputSurvivesTheValidators:
    """⭐ The templates are held to the same standard as the model."""

    def test_every_template_passes_every_validator(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        for insight_type, insight in every_insight.items():
            observation, evidence, interpretation, suggestion = templates.render(insight)
            sections = {
                "observation": observation,
                "evidence": evidence,
                "interpretation": interpretation,
                "suggestion": suggestion,
            }

            failures = validate(
                sections,
                tier=insight.tier,
                allowed_numbers=allowed_numbers(build_payload(insight)),
            )

            assert failures == [], (
                f"template for {insight_type.value} would be rejected: "
                f"{[f.detail for f in failures]}"
            )

    def test_the_correlational_template_is_visibly_correlational(
        self, relationship_insight: Insight
    ) -> None:
        _, _, interpretation, _ = templates.render(relationship_insight)

        assert "not a cause" in interpretation
        assert "association" in interpretation


class TestConfidenceRendering:
    """Never model-authored — derived from the insight's own statistics."""

    def test_a_correlational_insight_reports_its_figure(
        self, relationship_insight: Insight
    ) -> None:
        text = templates.render_confidence(relationship_insight)

        assert "Confidence" in text
        assert "%" in text
        assert "associations tested" in text

    def test_an_arithmetic_insight_reports_no_figure(
        self, total_insight: Insight
    ) -> None:
        """A sum is not uncertain, and inventing 100% would be inventing a
        number."""
        text = templates.render_confidence(total_insight)

        assert "no confidence figure applies" in text
        assert "%" not in text

    def test_a_comparison_says_why_it_has_no_figure(
        self, every_insight: dict[InsightType, Insight]
    ) -> None:
        text = templates.render_confidence(
            every_insight[InsightType.SPENDING_MONTHLY_COMPARISON]
        )

        assert "two complete periods" in text

    def test_a_sufficiency_notice_claims_nothing(
        self, sufficiency_insight: Insight
    ) -> None:
        text = templates.render_confidence(sufficiency_insight)

        assert "No conclusion is drawn" in text


class TestEmptyAndSparseData:
    def test_an_empty_window_is_explained_not_left_blank(self, now) -> None:
        from datetime import date

        from app.analysis.dataset import AnalysisDataset
        from app.analysis.engine import analyse
        from app.analysis.window import AnalysisWindow

        result = analyse(
            AnalysisDataset(window=AnalysisWindow(date(2026, 6, 1), date(2026, 6, 30))),
            now,
        )
        total = result.first(InsightType.SPENDING_TOTAL)

        observation, evidence, interpretation, _ = templates.render(total)

        assert "no recorded spending" in observation
        assert "nothing to analyse" in interpretation.lower()

    def test_a_sufficiency_notice_states_what_is_missing(
        self, sufficiency_insight: Insight
    ) -> None:
        """PDR-030 — under-claiming costs a session, over-claiming costs the
        user, and saying nothing costs both."""
        observation, evidence, interpretation, suggestion = templates.render(
            sufficiency_insight
        )

        assert "not yet enough" in observation or "No reliable conclusion" in observation
        assert "required" in evidence or "needed" in evidence
        assert suggestion is not None
