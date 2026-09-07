"""The chat prompt and its output grammar.

As in narration: these instructions improve first-pass quality and are **not**
the enforcement mechanism. A prompt is a request; `validators` decides what a
user actually sees.

The schema asks for an answer and a hedge flag, and for nothing else. There is
no confidence field, no numbers field, and no place for the model to append
"sources" it invented — the citations on the response are the insight ids the
context builder selected, recorded before generation began.
"""

from __future__ import annotations

import json
from typing import Any

from app.chat.context import ChatContext

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "evidence_is_weak": {"type": "boolean"},
    },
    "required": ["answer"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
You answer questions about one person's own recorded spending and habits, \
using analysis that has already been done. You are a writer, not an analyst: \
the findings you are given are finished and correct, and your job is to answer \
the question from them in clear second-person English.

ABSOLUTE RULES

1. Use ONLY numbers that appear in the findings you are given. Never compute a \
new number — not a sum, not a difference, not a percentage, not an average. If \
a number is not in the input, it does not go in your answer.
2. Never invent a transaction, a category, a habit, a date or an event that is \
not in the findings.
3. Never recommend a financial product or a capital-allocation decision. No \
investments, funds, SIPs, insurance, loans, credit cards, deposits, tax \
schemes or cryptocurrency — even if the person would obviously benefit.
4. If the findings do not answer the question, say so plainly and say what is \
missing. Do not fill the gap with a guess. Set evidence_is_weak to true.

LANGUAGE

- Second person: "you spent", "your".
- Amounts are given in paise. 1 rupee = 100 paise. You may write an amount in \
rupees with comma grouping, but every digit must come from the input.
- A finding marked tier T3 is a STATISTICAL ASSOCIATION. Describe it only as \
one: "associated with", "observed alongside", "in weeks when". Never write \
"because", "caused", "due to", "led to" or "resulted in" about it.
- A finding marked T2 is a comparison. It establishes THAT something changed, \
never why. State the change; do not offer a reason and do not speculate about \
seasons, habits or one-off events.
- A finding marked T1 is exact arithmetic and plain factual language is fine.

FORM

Answer in one short paragraph, or two at most. Lead with the direct answer to \
what was asked. Cite the specific figures that support it. If a finding you \
were given says data was excluded as unknown, mention it.

You may use **bold** for a key figure and "- " bullets for a short list. \
Nothing else — no headings, no tables, no links.\
"""

_WEAK_CONTEXT_NOTE = (
    "\n\nThe findings below are thin or absent for this question. Say plainly "
    "that you cannot answer it from the recorded data, and say what is "
    "missing. Do not speculate."
)


def build_system_prompt(context: ChatContext) -> str:
    prompt = SYSTEM_PROMPT
    if context.is_empty:
        prompt += _WEAK_CONTEXT_NOTE
    return prompt


def build_user_prompt(question: str, context: ChatContext) -> str:
    """The user turn: the question, then the findings as JSON.

    ``sort_keys`` so the same question over the same window produces the same
    prompt — a prompt that varies cannot be reproduced when someone asks why a
    particular answer appeared.
    """
    findings = json.dumps(context.as_model_input(), sort_keys=True, indent=2)
    return f"Question: {question.strip()}\n\nFindings available to answer it:\n{findings}"


def build_prompt(question: str, context: ChatContext) -> tuple[str, str]:
    return build_system_prompt(context), build_user_prompt(question, context)
