"""Prompt construction and the output grammar.

**These instructions are not the enforcement mechanism** (07_AI_Architecture
§4.3). They improve first-pass quality and reduce how often a generation is
thrown away. Enforcement is ``validators.py`` — because a prompt is a request,
and a request is not a control.

The output is constrained by a JSON schema passed to the model as a decoding
grammar, not asked for in prose. That bounds what the validators have to
inspect: they receive four named string fields, never an essay they must parse
a structure out of.

Note what the schema does **not** contain: a confidence field. The model is
never asked for one, so it can never fabricate one.
"""

from __future__ import annotations

import json
from typing import Any

from app.analysis.models import InsightTier

#: The grammar the model is decoded against (ADR-008 §4.4).
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "observation": {"type": "string"},
        "evidence": {"type": "string"},
        "interpretation": {"type": "string"},
        "suggestion": {"type": "string"},
    },
    "required": ["observation", "evidence", "interpretation"],
    "additionalProperties": False,
}

#: Field names the renderer reads back. Kept beside the schema so the two
#: cannot drift.
GENERATED_FIELDS = ("observation", "evidence", "interpretation", "suggestion")

SYSTEM_PROMPT = """\
You explain personal-finance analytics to the person they describe. You are \
a writer, not an analyst: the analysis is already finished and correct, and \
your only job is to put it into clear second-person English.

You will receive one JSON object describing a single finished insight. Write \
four short sections about it.

ABSOLUTE RULES

1. Use ONLY numbers that appear in the JSON you are given. Never compute a \
new number — not a sum, not a difference, not a percentage, not an average, \
not a rounding you worked out yourself. If a number is not in the input, it \
does not go in your output.
2. Never state a confidence, probability, certainty or accuracy figure. \
Confidence is written separately and is not your responsibility.
3. Never recommend a financial product or a capital-allocation decision. No \
investments, stocks, mutual funds, SIPs, insurance policies, loans, credit \
cards, fixed deposits, tax-saving schemes or cryptocurrency. This holds even \
if the user would obviously benefit.
4. Never invent a cause, a motive, or a fact that is not in the input.

LANGUAGE

- Write in the second person: "your", "you spent".
- Amounts are given in paise. 1 rupee = 100 paise. You may write an amount in \
rupees, and you may format it with commas, but the digits must come from the \
input.
- For tier T3 insights, the finding is a STATISTICAL ASSOCIATION and nothing \
more. Use only correlational language: "associated with", "correlated with", \
"observed alongside", "tended to coincide with", "in weeks when". You must \
NOT write "because", "caused", "due to", "led to", "resulted in", "drove" or \
any other causal connective.
- For tier T2 insights the comparison establishes THAT something changed, \
never why. State the change. Do not offer a reason, and do not speculate \
about seasons, habits or one-off events — the input does not contain a cause, \
so any you supply is invented.
- For tier T1 insights the claim is arithmetic over recorded data and plain \
factual language is fine.

SECTIONS

observation    - one sentence stating what the data shows.
evidence       - one or two sentences citing the specific figures behind it.
interpretation - one or two sentences on what the pattern means, within the \
limits above. If the input says data was excluded as unknown, say so.
suggestion     - OPTIONAL. One hedged behavioural suggestion using "may", \
"might", "could" or "consider". Omit it entirely if nothing follows from the \
data. Never a financial product.

If the input describes insufficient data, say plainly that no reliable \
conclusion can be drawn and what is missing. Do not speculate to fill the gap.

WORKED EXAMPLES

The digits below are illustrative. Never reuse them — use only the numbers in \
the input you are given.

For a T2 period comparison, an acceptable interpretation states the shape of \
the change and stops:

  GOOD: "Only complete weeks are compared, so this is not an artefact of \
where the window starts."
  BAD:  "This increase could be due to seasonal changes or specific events." \
(invents a cause the input does not contain)

For a T3 association, an acceptable interpretation frames it as one:

  GOOD: "Higher spending was observed alongside weeks without exercise. This \
is an association and does not establish a cause."
  BAD:  "Skipping the gym led to higher food spending." (causal)\
"""

#: Extra line appended for correlational insights. Repetition is cheap and the
#: causal slip is the most common failure mode in this task.
_T3_REMINDER = (
    "\n\nThis insight is tier T3: a statistical association, not a cause. "
    "Any causal wording will cause your answer to be discarded."
)

#: Extra line for the honest empty state (PDR-030).
_SUFFICIENCY_REMINDER = (
    "\n\nThis insight reports that a requirement for analysis was not met. "
    "State plainly what is missing and what would unlock the analysis. "
    "Do not describe a pattern — none was found."
)


def build_system_prompt(tier: InsightTier, *, is_sufficiency_notice: bool = False) -> str:
    """The system prompt, with a tier-appropriate reminder appended."""
    prompt = SYSTEM_PROMPT
    if is_sufficiency_notice:
        return prompt + _SUFFICIENCY_REMINDER
    if tier is InsightTier.T3_CORRELATIONAL:
        return prompt + _T3_REMINDER
    return prompt


def build_user_prompt(payload: dict[str, Any], display_name: str | None = None) -> str:
    """The user turn: a greeting line plus the insight as JSON.

    ``sort_keys`` because two runs over the same insight must produce the same
    prompt — a prompt that varies makes a generation impossible to reproduce
    when someone asks why a particular sentence appeared.
    """
    header = "Write the four sections for this insight."
    if display_name:
        header = f"Write the four sections for {display_name}'s insight."

    return f"{header}\n\n{json.dumps(payload, sort_keys=True, indent=2)}"


def build_prompt(
    payload: dict[str, Any],
    tier: InsightTier,
    *,
    display_name: str | None = None,
    is_sufficiency_notice: bool = False,
) -> tuple[str, str]:
    """Return ``(system, user)`` for one insight."""
    return (
        build_system_prompt(tier, is_sufficiency_notice=is_sufficiency_notice),
        build_user_prompt(payload, display_name),
    )
