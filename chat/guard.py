r"""The prohibited-topic guard (ADR-010, PDR-027).

**Runs before anything else, including intent detection.** Prohibited content
is never generated, never logged, never cached — a claim that only holds if
nothing downstream of this function ever receives the question. No model
dependency; independently testable (SRS-7.10).

## The boundary

PDR-027's, exactly:

> Describing the user's own recorded history is **always permitted**;
> directing future capital allocation is **always refused**.

That is why this is not a keyword ban. *"How much did I pay in loan EMIs last
quarter?"* names a loan and is a factual query about recorded data — it is
answered. *"Should I switch to a cheaper loan?"* names the same product and
asks the system to direct capital — it is refused.

So a refusal needs **a product topic and a directive frame**, except for the
handful of asks that are directive however they are phrased.

## Where ambiguity goes

To refusal. A false refusal costs a session; a false answer is a regulatory
event (07_AI_Architecture.md §6). Where the two readings of a question differ
in kind rather than degree, this file prefers the safe one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

#: Financial products and capital-allocation topics. Naming one is not by
#: itself disqualifying — see the module docstring.
PRODUCT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\binvest(s|ed|ing|ment|ments)?\b",
        r"\bmutual fund",
        r"\bSIP\b",
        r"\bstock(s)?\b",
        r"\bshare market\b",
        r"\bequit(y|ies)\b",
        r"\bIPO\b",
        r"\bportfolio\b",
        r"\bcrypto",
        r"\bbitcoin\b",
        r"\bfixed deposit\b",
        r"\brecurring deposit\b",
        r"\binsurance\b",
        r"\bpolicy\b",
        r"\bpremium\b",
        r"\bloan(s)?\b",
        r"\bEMI(s)?\b",
        r"\bmortgage\b",
        r"\brefinanc",
        r"\bcredit card\b",
        r"\bcredit score\b",
        r"\btax(es)?\b",
        r"\b80C\b",
        r"\bITR\b",
        r"\bmutual\b",
        r"\bsavings account\b",
        r"\binterest rate\b",
        r"\bpension\b",
        r"\bNPS\b",
        r"\bPPF\b",
        r"\bgold\b",
        r"\breal estate\b",
        r"\bproperty\b",
        # Speculative wagering. "Can I afford to gamble ₹10,000?" asks the
        # system to bless a bet — a capital-direction question in disguise.
        r"\bgambl(e|es|ed|ing)\b",
        r"\bbet(s|ting)?\b",
        r"\blotter(y|ies)\b",
        # Capital itself, not only the products it goes into. "Where should I
        # put my savings?" names no product and is plainly an allocation
        # question; without these it would slip through on a technicality.
        r"\bsavings\b",
        r"\bsurplus\b",
        r"\bspare (cash|money)\b",
        r"\bmy money\b",
        r"\bnest egg\b",
    )
)

#: Asking the system to decide, recommend, or direct.
DIRECTIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bshould i\b",
        r"\bshall i\b",
        r"\bshould we\b",
        r"\bdo you (recommend|suggest|think i)\b",
        r"\brecommend\b",
        r"\badvise\b",
        r"\badvice\b",
        r"\bis it (worth|wise|smart|safe|a good idea)\b",
        # "Is my insurance premium worth it?" puts the subject before the
        # verb, so the "is it worth" form alone would miss it.
        r"\bworth it\b",
        r"\bgood idea to\b",
        r"\bbetter (to|off)\b",
        r"\bwhich .{0,30}(should|to) (i )?(buy|pick|choose|take|get|open)\b",
        r"\bwhere should i\b",
        r"\bhow (much|do i) .{0,20}(invest|save for retirement)\b",
        r"\bworth (buying|taking|getting|opening)\b",
        r"\bhelp me (choose|pick|decide)\b",
        r"\bbest .{0,30}(fund|stock|plan|policy|scheme|deposit|account)\b",
        # Paraphrases that dodge "should I" but still ask the system to decide.
        # "Which stock would you buy?", "what would you do with my surplus?"
        r"\bwould you .{0,25}(buy|pick|choose|invest|recommend|prefer|go with|do with|put)\b",
        # "Can I afford to gamble ₹10k?" — permission for a forward-looking
        # allocation. Historical affordability names no product, so this only
        # bites in combination with a product term above.
        r"\bcan i afford\b",
        # "The smartest investment", "a wise move" — an evaluative framing of a
        # future choice rather than a factual question about recorded data.
        r"\b(smart|smartest|wise|wisest|best|right)\b.{0,20}\b(investment|move|choice|option|decision|bet|play)\b",
    )
)

#: Refused however phrased — no descriptive reading exists.
ALWAYS_PROHIBITED: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bstock tip",
        r"\bhot stock",
        r"\bwhat to invest\b",
        r"\bwhere to invest\b",
        r"\bhow to invest\b",
        r"\bwhich (stock|fund|coin|crypto)\b",
        r"\bmarket (forecast|prediction|outlook)\b",
        r"\bwill .{0,20}(go up|go down|crash|rally)\b",
        r"\bfinancial advi(c|s)e\b",
        r"\bplan my retirement\b",
        r"\bportfolio allocation\b",
        # Bare capital-allocation directives that name no product but have no
        # plausible historical reading. "Where to allocate ₹20k", "where would
        # a smart person park spare cash", "where to put my money".
        r"\bwhere (should|to|do|would|can) .{0,25}(put|park|allocate|invest|stash)\b",
        r"\ballocate\b.{0,15}(₹|rs\.?|inr|\d)",
    )
)


class GuardVerdict(str, Enum):
    PERMITTED = "PERMITTED"
    PROHIBITED = "PROHIBITED"


@dataclass(frozen=True, slots=True)
class GuardResult:
    verdict: GuardVerdict
    #: What matched, for tests and for the audit trail. Never shown to a user.
    matched: tuple[str, ...] = ()
    detail: str = ""

    @property
    def is_prohibited(self) -> bool:
        return self.verdict is GuardVerdict.PROHIBITED


def _hits(question: str, patterns: tuple[re.Pattern[str], ...]) -> list[str]:
    return sorted({match.group(0).lower() for p in patterns for match in p.finditer(question)})


def screen_question(question: str) -> GuardResult:
    """Decide whether a question may reach the rest of the pipeline.

    Returns ``PROHIBITED`` for anything that asks the system to direct future
    capital allocation, and ``PERMITTED`` for everything else — including
    questions that name a financial product while asking about recorded
    history.
    """
    text = question.strip()
    if not text:
        return GuardResult(GuardVerdict.PERMITTED)

    unconditional = _hits(text, ALWAYS_PROHIBITED)
    if unconditional:
        return GuardResult(
            GuardVerdict.PROHIBITED,
            tuple(unconditional),
            "asks for a forward-looking financial recommendation",
        )

    products = _hits(text, PRODUCT_PATTERNS)
    directives = _hits(text, DIRECTIVE_PATTERNS)

    if products and directives:
        return GuardResult(
            GuardVerdict.PROHIBITED,
            tuple(products + directives),
            "asks the system to direct capital allocation",
        )

    return GuardResult(GuardVerdict.PERMITTED)


#: The refusal a user sees. Fixed text, not generated — a refusal that went
#: through a model would be a refusal the model could soften.
REFUSAL_TEXT = (
    "I can't help with that one. This assistant describes what you have "
    "already recorded — where your money went, how your habits line up with "
    "it, what happened around a life event. It doesn't recommend financial "
    "products or advise on what to do with your money, and it isn't a "
    "licensed adviser.\n\n"
    "I can still tell you what you've spent on any of this. For example: "
    '"how much did I pay in EMIs this quarter?"'
)
