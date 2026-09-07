r"""Three independent, deterministic validators. Failure discards; never repairs.

The prompt asks the model to behave. These check whether it did. A prompt is a
request and a request is not a control (07_AI_Architecture §4.3), so every rule
that matters is restated here as code that can reject a generation.

**Provenance** (SRS-7.3) — every numeric literal in the prose must appear in
the payload the model was given. This is what makes "must not fabricate
numerical results" enforceable rather than merely stated.

**Lexical** (SRS-7.4) — tier-aware. Causal connectives are rejected in T3
content, where the claim is an association. They are permitted in T1, where
the claim is an accounting identity and *"your total rose because an annual
premium was debited"* is provable by summation (PDR-036🟠).

**Advice guard** (ADR-010) — runs independently of the other two and on every
tier. The boundary is PDR-027's: describing the user's own recorded history is
always permitted; directing future capital allocation is always refused.

All three run on every generation and all failures are collected, so the
recorded reason is complete rather than whichever check happened to run first.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping

from app.analysis.models import InsightTier
from app.narration.models import ValidationFailure
from app.narration.payload import extract_numbers

# ── Lexical ─────────────────────────────────────────────────────────────────

#: Causal connectives. Rejected in T3 content, permitted in T1/T2.
CAUSAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bbecause\b",
        r"\bcaus(e|es|ed|ing)\b",
        r"\bdue to\b",
        r"\bled to\b",
        r"\bleads? to\b",
        r"\bresult(s|ed) (in|from)\b",
        r"\bas a result of\b",
        r"\bmade? you\b",
        r"\bmakes? you\b",
        r"\bdr(o|i)ve(n|s)? by\b",
        r"\bdrives\b",
        r"\bconsequently\b",
        r"\btherefore\b",
        r"\bthanks to\b",
        r"\bthe reason\b",
        r"\bexplains? why\b",
    )
)

#: Explicit denials of causation, removed before the causal scan runs.
#:
#: Without this, "this is an association, not a cause" trips the causal check
#: on the word "cause" — penalising the exact disclaimer the design wants and
#: pushing generations toward vaguer language than the honest phrasing. Only
#: complete denial phrases are stripped, so "caused by" elsewhere in the same
#: sentence still fails.
DISCLAIMER_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"not (a |an |any )?cause\b",
        r"rather than a cause\b",
        # The verb list is broad on purpose. qwen2.5:7b wrote "it does not
        # indicate a cause" — a correct disclaimer that a narrower list
        # rejected, which is the worst kind of false positive: it penalises
        # the exact phrasing the design is trying to elicit.
        r"does(n't| not) (prove|imply|establish|show|indicate|mean|demonstrate|confirm)"
        r"( a| an| any)? caus\w*",
        r"no(t)? causal\b",
        r"without implying caus\w*",
        r"correlation (is|does) not caus\w*",
    )
)

#: At least one of these must appear in a T3 interpretation. Positive evidence
#: that the association was framed as one, rather than merely the absence of a
#: banned word.
CORRELATIONAL_MARKERS: tuple[str, ...] = (
    "associat",
    "correlat",
    "coincid",
    "alongside",
    "relationship",
    "pattern",
    "tended",
    "tend to",
    "observed",
    "in weeks",
    "during weeks",
    "does not prove",
    "doesn't prove",
    "not prove causation",
)

# ── Advice guard ────────────────────────────────────────────────────────────

#: Prohibited topics (ADR-010, PDR-027). Phrase-level where a bare word would
#: be ambiguous: an insurance *premium* may legitimately appear as an expense,
#: so the pattern targets the product, not the payment.
PROHIBITED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\binvest(s|ed|ing|ment|ments)?\b",
        r"\bmutual fund",
        r"\bSIP\b",
        r"\bstock(s|market)?\b",
        r"\bshare market\b",
        r"\bequit(y|ies)\b",
        r"\bIPO\b",
        r"\bportfolio\b",
        r"\bcrypto",
        r"\bbitcoin\b",
        r"\bfixed deposit\b",
        r"\brecurring deposit\b",
        r"\binsurance (policy|plan|cover|product)",
        r"\btake (out )?(a|an) (loan|policy|mortgage)\b",
        r"\brefinanc",
        r"\bcredit score\b",
        r"\btax(-| )sav(ing|er)",
        r"\btax (benefit|deduction|planning)\b",
        r"\b80C\b",
        r"\bITR\b",
        r"\bwealth manage",
        r"\bfinancial advis(or|er)\b",
        r"\bhigh(-| )(yield|interest) (account|savings)\b",
    )
)

#: A suggestion must hedge. An unhedged imperative reads as advice, which is
#: the register this product does not operate in.
HEDGE_MARKERS: tuple[str, ...] = (
    "may ",
    "might ",
    "could ",
    "consider",
    "if you",
    "you may want",
    "one option",
    "worth ",
    "tend",
)


def _joined(sections: Mapping[str, str | None]) -> str:
    return "\n".join(value for value in sections.values() if value)


def check_provenance(
    sections: Mapping[str, str | None], allowed: Iterable[str]
) -> list[ValidationFailure]:
    """Reject any numeric literal absent from the model's input."""
    permitted = set(allowed)
    failures: list[ValidationFailure] = []

    for name, text in sections.items():
        if not text:
            continue
        invented = [number for number in extract_numbers(text) if number not in permitted]
        if invented:
            failures.append(
                ValidationFailure(
                    validator="provenance",
                    detail=(
                        f"'{name}' contains {len(invented)} number(s) absent from the "
                        f"analysis payload: {', '.join(sorted(set(invented))[:5])}"
                    ),
                )
            )
    return failures


def check_lexical(
    sections: Mapping[str, str | None], tier: InsightTier
) -> list[ValidationFailure]:
    """Tier-aware language rules.

    **Only T1 is exempt**, matching PDR-036 exactly. A T1 signal carries its
    largest contributing expenses as evidence, so *"your total rose because a
    ₹40,000 premium was debited"* is provable by summation.

    T2 gets the same causal ban as T3, which is a correction rather than an
    extension: a period comparison establishes *that* spending moved, never
    *why*. Running qwen2.5:7b against a real monthly comparison produced
    "this increase could be due to seasonal changes or unexpected expenses" —
    fluent, plausible, and entirely absent from the input. Exempting T2 had
    licensed the model to invent a cause.
    """
    if tier is InsightTier.T1_DESCRIPTIVE:
        return []

    failures: list[ValidationFailure] = []

    for name, text in sections.items():
        if not text:
            continue
        scannable = text
        for pattern in DISCLAIMER_PATTERNS:
            scannable = pattern.sub(" ", scannable)
        hits = sorted(
            {m.group(0).lower() for p in CAUSAL_PATTERNS for m in p.finditer(scannable)}
        )
        if hits:
            failures.append(
                ValidationFailure(
                    validator="lexical",
                    detail=(
                        f"'{name}' uses causal language for a correlational claim: "
                        f"{', '.join(hits[:5])}"
                    ),
                )
            )

    if tier is not InsightTier.T3_CORRELATIONAL:
        return failures

    # Positive framing is required only where there is an association to frame.
    interpretation = (sections.get("interpretation") or "").lower()
    if interpretation and not any(marker in interpretation for marker in CORRELATIONAL_MARKERS):
        failures.append(
            ValidationFailure(
                validator="lexical",
                detail=(
                    "'interpretation' does not frame the finding as an association. "
                    "A T3 claim must be visibly correlational, not merely free of "
                    "causal words."
                ),
            )
        )

    return failures


def check_advice(sections: Mapping[str, str | None]) -> list[ValidationFailure]:
    """The prohibited-topic guard (ADR-010).

    Independent of tier and of the other validators: a generation that already
    failed provenance is still checked here, so the recorded reason is
    complete. This function has no model dependency and is testable on its own
    (SRS-7.10).
    """
    failures: list[ValidationFailure] = []
    text = _joined(sections)

    hits = sorted({m.group(0).lower() for p in PROHIBITED_PATTERNS for m in p.finditer(text)})
    if hits:
        failures.append(
            ValidationFailure(
                validator="advice_guard",
                detail=f"prohibited topic: {', '.join(hits[:5])}",
            )
        )

    suggestion = sections.get("suggestion")
    if suggestion and not any(marker in suggestion.lower() for marker in HEDGE_MARKERS):
        failures.append(
            ValidationFailure(
                validator="advice_guard",
                detail=(
                    "'suggestion' is phrased as an instruction rather than a hedged "
                    "observation"
                ),
            )
        )

    return failures


def check_shape(sections: Mapping[str, str | None]) -> list[ValidationFailure]:
    """The required sections must be present and non-trivial."""
    failures: list[ValidationFailure] = []
    for name in ("observation", "evidence", "interpretation"):
        text = (sections.get(name) or "").strip()
        if len(text) < 10:
            failures.append(
                ValidationFailure(
                    validator="shape",
                    detail=f"'{name}' is missing or too short to be an explanation",
                )
            )
    return failures


def validate(
    sections: Mapping[str, str | None],
    *,
    tier: InsightTier,
    allowed_numbers: Iterable[str],
) -> list[ValidationFailure]:
    """Run every validator and return all failures.

    Order carries no meaning — any single failure discards the generation. All
    four run so the reason recorded on the fallback is the whole reason.
    """
    permitted = set(allowed_numbers)
    return [
        *check_shape(sections),
        *check_provenance(sections, permitted),
        *check_lexical(sections, tier),
        *check_advice(sections),
    ]
