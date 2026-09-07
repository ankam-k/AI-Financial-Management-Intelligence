"""The bounded Q&A subsystem (07_AI_Architecture.md §6).

```
question
   │
   ▼
[ProhibitedTopicGuard]  ────▶ REFUSED (PROHIBITED_TOPIC)
   │ pass                      ← never reaches the model (ADR-010)
   ▼
[Intent → capability map] ───▶ REFUSED (NOT_ANSWERABLE_FROM_ANALYSIS)
   │ matched
   ▼
[Context builder — structured outputs from the engine]
   │
   ▼
[LLM renders answer] → [validators] → answer | template fallback
```

**The guard runs first.** Prohibited content is never generated, never logged,
never cached — which is only true if nothing downstream of the guard ever sees
it. It has no model dependency and is testable on its own (SRS-7.10).

**No conversation state exists.** There is no ``conversation_id`` here, no
history parameter, no server-side turn memory. That absence *is* the
enforcement of single-turn (SRS-7.7, PDR-037🟠) — a transcript in the browser
is a display artefact the model never sees.

**Nothing here computes.** The assistant is a consumer: it selects finished
insights, hands them to a renderer, and checks what comes back. Every number
it can say was computed by ``app/analysis/`` in a previous sprint.
"""

from app.chat.context import ChatContext, build_context
from app.chat.guard import GuardVerdict, screen_question
from app.chat.intents import Intent, IntentMatch, detect_intent
from app.chat.models import (
    AnswerStatus,
    ChatAnswer,
    Citation,
    RefusalReason,
)
from app.chat.service import ChatEngine

__all__ = [
    "AnswerStatus",
    "ChatAnswer",
    "ChatContext",
    "ChatEngine",
    "Citation",
    "GuardVerdict",
    "Intent",
    "IntentMatch",
    "RefusalReason",
    "build_context",
    "detect_intent",
    "screen_question",
]
