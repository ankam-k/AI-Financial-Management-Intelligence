"""Orchestration: template first, model as an upgrade that must earn it.

```
        Insight
           │
           ▼
   render template  ──────────────┐   always, and first
           │                      │
     model configured? ──no──────▶│
           │ yes                  │
           ▼                      │
     generate (JSON schema)       │
           │                      │
     LLMError ────────────────────┤   timeout · unreachable · bad protocol
           │ ok                   │
           ▼                      │
     validate ──any failure──────▶│   provenance · lexical · advice · shape
           │ pass                 ▼
           ▼                  TEMPLATE
          LLM
```

Two properties this ordering buys:

**The template is always computed**, so a fallback is never a scramble — it is
the value that was already there. There is no path where a failure produces a
degraded object or a 500.

**Failure discards; it never repairs** (ADR-009). Nothing here edits a
generation to make it pass. A generation is used whole or thrown away whole,
which keeps "what the user saw" a two-valued question.

This module performs no I/O. The client is injected and is only ever touched
through the :class:`LLMClient` protocol.
"""

from __future__ import annotations

from app.analysis.models import Insight, InsightTier, InsightType
from app.llm.base import LLMClient, LLMError
from app.narration import templates
from app.narration.models import Narration, NarrationRun, NarrationSource, ValidationFailure
from app.narration.payload import allowed_numbers, build_payload
from app.narration.prompts import GENERATED_FIELDS, OUTPUT_SCHEMA, build_prompt
from app.narration.validators import validate

#: Generation order when a run has more insights than the budget allows.
#: Correlational findings are the ones prose helps most — a total is already
#: legible as a number.
_TIER_PRIORITY: dict[InsightTier, int] = {
    InsightTier.T3_CORRELATIONAL: 0,
    InsightTier.T2_COMPARATIVE: 1,
    InsightTier.T1_DESCRIPTIVE: 2,
}


class NarrationRenderer:
    """Turns insights into five-section explanations."""

    def __init__(self, client: LLMClient, *, max_generated: int = 5) -> None:
        self._client = client
        self._max_generated = max_generated

    # ── Single insight ──────────────────────────────────────────────────────

    def narrate(
        self,
        insight: Insight,
        *,
        display_name: str | None = None,
        allow_generation: bool = True,
    ) -> Narration:
        """Explain one insight, generating only if the result survives review."""
        observation, evidence, interpretation, suggestion = templates.render(insight)
        confidence_text = templates.render_confidence(insight)

        def as_template(reason: str | None, failures: tuple[ValidationFailure, ...] = ()) -> Narration:
            return Narration(
                insight_id=insight.id,
                insight_type=insight.type.value,
                tier=insight.tier.value,
                observation=observation,
                evidence=evidence,
                interpretation=interpretation,
                confidence=confidence_text,
                confidence_value=insight.confidence,
                suggestion=suggestion,
                source=NarrationSource.TEMPLATE,
                validation_failures=failures,
                fallback_reason=reason,
            )

        if not allow_generation:
            return as_template("Generation disabled for this request.")

        payload = build_payload(insight)
        system, user = build_prompt(
            payload,
            insight.tier,
            display_name=display_name,
            is_sufficiency_notice=insight.type is InsightType.DATA_SUFFICIENCY,
        )

        try:
            raw = self._client.complete_json(system=system, user=user, schema=OUTPUT_SCHEMA)
        except LLMError as exc:
            return as_template(f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            # A client that raises something outside the LLMError hierarchy is
            # a bug in that adapter. It must still not take down a request the
            # template could have answered.
            return as_template(f"Unexpected client error: {type(exc).__name__}: {exc}")

        sections = {
            name: value.strip()
            for name in GENERATED_FIELDS
            if isinstance(value := raw.get(name), str)
        }

        failures = validate(
            sections,
            tier=insight.tier,
            allowed_numbers=allowed_numbers(payload),
        )
        if failures:
            return as_template(
                f"Generation rejected by {len(failures)} validator check(s).",
                tuple(failures),
            )

        generated_suggestion = sections.get("suggestion") or None
        return Narration(
            insight_id=insight.id,
            insight_type=insight.type.value,
            tier=insight.tier.value,
            observation=sections["observation"],
            evidence=sections["evidence"],
            interpretation=sections["interpretation"],
            # Never model-authored, even when everything else is.
            confidence=confidence_text,
            confidence_value=insight.confidence,
            suggestion=generated_suggestion,
            source=NarrationSource.LLM,
            model=f"{self._client.provider}:{self._client.model}",
        )

    # ── A whole run ─────────────────────────────────────────────────────────

    def narrate_all(
        self,
        insights: tuple[Insight, ...],
        *,
        display_name: str | None = None,
        allow_generation: bool = True,
    ) -> NarrationRun:
        """Explain every insight, generating for at most ``max_generated``.

        Narration is sequential and a local 7B model is slow, so the budget is
        spent on the highest tier first and the remainder are rendered from
        templates. Every insight is explained either way — the budget changes
        the prose, never the coverage.
        """
        ranked = sorted(
            range(len(insights)),
            key=lambda index: (_TIER_PRIORITY[insights[index].tier], index),
        )
        generating = set(ranked[: self._max_generated]) if allow_generation else set()

        narrations = [
            self.narrate(
                insight,
                display_name=display_name,
                allow_generation=index in generating,
            )
            for index, insight in enumerate(insights)
        ]

        generated = [n for n in narrations if n.source is NarrationSource.LLM]
        rejected = [n for n in narrations if n.validation_failures]

        return NarrationRun(
            narrations=tuple(narrations),
            stats={
                "total": len(narrations),
                "generated": len(generated),
                "templated": len(narrations) - len(generated),
                "generation_attempted": len(generating),
                "rejected_by_validation": len(rejected),
                "provider": self._client.provider,
                "model": self._client.model,
            },
        )
