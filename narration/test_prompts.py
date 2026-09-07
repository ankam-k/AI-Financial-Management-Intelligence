"""Prompt construction and the output grammar."""

from __future__ import annotations

import json

import pytest

from app.analysis.models import Insight, InsightTier
from app.narration.payload import build_payload
from app.narration.prompts import (
    GENERATED_FIELDS,
    OUTPUT_SCHEMA,
    SYSTEM_PROMPT,
    build_prompt,
    build_system_prompt,
    build_user_prompt,
)


class TestOutputSchema:
    def test_it_never_asks_for_a_confidence_field(self) -> None:
        """⭐ "Do not fabricate confidence values" is enforced by never asking.
        Confidence is rendered from the insight's own statistics."""
        assert "confidence" not in OUTPUT_SCHEMA["properties"]

    def test_it_asks_for_the_four_authored_sections(self) -> None:
        assert set(OUTPUT_SCHEMA["properties"]) == set(GENERATED_FIELDS)

    def test_suggestion_is_optional_everything_else_is_not(self) -> None:
        assert set(OUTPUT_SCHEMA["required"]) == {
            "observation",
            "evidence",
            "interpretation",
        }

    def test_it_forbids_extra_keys(self) -> None:
        """Constrained decoding is what keeps the validators inspecting named
        fields rather than parsing prose for structure."""
        assert OUTPUT_SCHEMA["additionalProperties"] is False


class TestSystemPrompt:
    @pytest.mark.parametrize(
        "rule",
        [
            "Use ONLY numbers",
            "Never state a confidence",
            "Never recommend a financial product",
            "Never invent a cause",
        ],
    )
    def test_it_states_every_absolute_rule(self, rule: str) -> None:
        assert rule in SYSTEM_PROMPT

    def test_it_explains_the_paise_convention(self) -> None:
        """Without this the model divides by 100 itself, which is a
        calculation and fails provenance."""
        assert "1 rupee = 100 paise" in SYSTEM_PROMPT

    def test_a_correlational_insight_gets_a_causal_warning(self) -> None:
        prompt = build_system_prompt(InsightTier.T3_CORRELATIONAL)

        assert "This insight is tier T3" in prompt
        assert "discarded" in prompt

    def test_an_arithmetic_insight_gets_no_such_warning(self) -> None:
        """T1 claims are accounting identities where causal phrasing is
        permitted (PDR-036), so the reminder would be wrong. The base prompt
        still describes the T3 rules, since one prompt covers every tier."""
        prompt = build_system_prompt(InsightTier.T1_DESCRIPTIVE)

        assert "This insight is tier T3" not in prompt
        assert prompt == SYSTEM_PROMPT

    def test_a_sufficiency_notice_is_told_not_to_speculate(self) -> None:
        prompt = build_system_prompt(
            InsightTier.T1_DESCRIPTIVE, is_sufficiency_notice=True
        )

        assert "no reliable conclusion" in prompt or "none was found" in prompt


class TestUserPrompt:
    def test_it_contains_the_payload_as_json(self, relationship_insight: Insight) -> None:
        payload = build_payload(relationship_insight)

        prompt = build_user_prompt(payload)
        body = prompt[prompt.index("{") :]

        assert json.loads(body) == payload

    def test_it_personalises_when_a_name_is_known(
        self, relationship_insight: Insight
    ) -> None:
        prompt = build_user_prompt(build_payload(relationship_insight), "Pranay")

        assert "Pranay's insight" in prompt

    def test_it_is_deterministic(self, relationship_insight: Insight) -> None:
        """Two runs over the same insight must produce the same prompt, or a
        generation cannot be reproduced when someone asks why a sentence
        appeared."""
        payload = build_payload(relationship_insight)

        assert build_user_prompt(payload) == build_user_prompt(payload)

    def test_it_carries_no_database_identifiers(
        self, relationship_insight: Insight
    ) -> None:
        """The model receives the finished insight, never the ledger."""
        prompt = build_user_prompt(build_payload(relationship_insight))

        assert "user_id" not in prompt
        assert "SELECT" not in prompt.upper()


class TestBuildPrompt:
    def test_it_returns_system_and_user(self, relationship_insight: Insight) -> None:
        system, user = build_prompt(
            build_payload(relationship_insight), relationship_insight.tier
        )

        assert "ABSOLUTE RULES" in system
        assert "BEHAVIOR_RELATIONSHIP" in user
