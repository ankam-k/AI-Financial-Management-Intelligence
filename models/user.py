"""The user — identity and profile in one row.

Through V1.1 this was a single local *profile* with no credentials (ADR-014).
V1.2 turns it into a real authenticated account (ADR-011): the same row now
also carries ``email`` and an Argon2id ``password_hash``. Every owned row
already carried ``user_id`` with a cascading foreign key (05_Database_Design.md
§1), so multi-user isolation needed no new columns anywhere else — only a real
identity here and a login to resolve it.

Two nullable-identity cases are deliberate, so the migration onto an existing
database stays non-destructive:

* a **pre-V1.2 profile** row predates auth and has no email/hash;
* the **demo account** (``is_demo``) is entered without a password.

Both are unreachable through the login flow (which requires a verified email
and password), so nullable credentials never weaken authentication — they only
avoid rewriting history. ``email`` uniqueness is enforced by a *partial* index
over non-null emails: SQLite's ``ALTER TABLE ADD COLUMN`` cannot add a UNIQUE
column, and a partial index also lets more than one credential-less row exist.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdentifiedEntity


class User(IdentifiedEntity, Base):
    """An authenticated account and its financial profile."""

    __tablename__ = "user"

    #: Login identity. Nullable only for the pre-V1.2 profile and the demo
    #: account (see module docstring); a registered user always has one, stored
    #: already normalised (lower-cased, trimmed) by the auth service.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: Argon2id hash. **Never** the plaintext. Null for the credential-less
    #: rows above; a login can never succeed against a null hash.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: Marks the synthetic demo account. Demo data belongs exclusively to a row
    #: with ``is_demo = true`` and can never reach a real account (ADR-019,
    #: Phase 11). A real registration always creates this false.
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="Local User")

    #: IANA timezone name. Fixed to IST in V1 (ADR-003) but stored as a column
    #: rather than a constant, so a future user outside India is a data change.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")

    #: Reporting currency. A column, never hardcoded (SRS-3.14, PDR-025).
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    #: Monthly spending budget in paise. **NULL means the user has not set one**
    #: — budget insights are then suppressed entirely rather than computed
    #: against a figure the engine guessed from average spend. Added in Sprint 2
    #: because budget utilisation has nothing to measure without it.
    monthly_budget_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # ── Onboarding & personalisation (V1.2, M5) ─────────────────────────────
    # These shape the UI and nothing else. NONE of them ever reaches the
    # analysis engine, which is fed a dataset — never this row (ADR-007;
    # app/domain/preferences.py). Every column is additive and defaulted so the
    # idempotent startup migration can carry a pre-V1.2 database forward without
    # touching an existing row (app/core/migrations.py).

    #: Whether the user has finished (or skipped through) onboarding. False for
    #: pre-V1.2 rows and every fresh registration; the first-run UI reads it to
    #: decide whether to show the onboarding flow. NOT NULL DEFAULT 0, exactly
    #: like ``is_demo``, so a legacy row upgrades to "not yet onboarded".
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    #: Coarse self-description, each a closed vocabulary in
    #: ``app/domain/preferences.py``. Stored as the enum's string value; NULL
    #: means "not answered" (onboarding may be skipped). Kept as plain strings
    #: rather than a DB ``ENUM``/``CHECK`` so the migration stays a trivial
    #: ``ADD COLUMN`` — the closed set is enforced at the schema layer, where
    #: every write already passes (schemas/profile.py).
    life_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    income_pattern: Mapped[str | None] = mapped_column(String(32), nullable=True)
    work_context: Mapped[str | None] = mapped_column(String(32), nullable=True)
    household_context: Mapped[str | None] = mapped_column(String(32), nullable=True)

    #: Multi-select preferences, stored as JSON string arrays. An empty list is
    #: the natural "nothing selected yet" value, so these are NOT NULL DEFAULT
    #: '[]' — a legacy row upgrades to an empty selection, never NULL. The
    #: members are validated (and de-duplicated) at the schema layer against the
    #: real product vocabularies: ``focus_areas`` ⊆ FocusArea,
    #: ``tracked_categories`` ⊆ Category, ``tracked_habits`` ⊆ the six check-in
    #: habit fields. They drive display prominence only.
    focus_areas: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    tracked_categories: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    tracked_habits: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )

    __table_args__ = (
        CheckConstraint(
            "monthly_budget_paise IS NULL OR monthly_budget_paise > 0",
            name="ck_user_budget_positive",
        ),
        #: Email is unique among accounts that have one. Partial (``WHERE email
        #: IS NOT NULL``) so credential-less rows don't collide on NULL and so
        #: the definition matches what the ALTER-based migration can create.
        Index(
            "uq_user_email",
            "email",
            unique=True,
            sqlite_where=text("email IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id!r} display_name={self.display_name!r}>"
