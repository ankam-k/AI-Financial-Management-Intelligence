"""Application configuration.

Settings are read from the environment with the ``AFI_`` prefix, falling back
to values that let a fresh clone run with no setup at all — a deliberate MVP
choice, since Sprint 1 has no secrets to protect and a zero-config start is
worth more than ceremony.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

#: Repository root — this file is `<root>/backend/app/core/config.py`.
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: The default database, as an **absolute** path.
#:
#: A relative `sqlite:///./…` resolves against the working directory, so
#: running the server from the repository root and the seeder from `backend/`
#: silently creates two separate databases — the seeder reports 629 expenses
#: and the dashboard shows none. Anchoring it means every command touches the
#: same file whatever directory it was typed in.
DEFAULT_DATABASE_URL = f"sqlite:///{(_REPO_ROOT / 'financial_intelligence.db').as_posix()}"


class Settings(BaseSettings):
    """Runtime configuration for the API."""

    model_config = SettingsConfigDict(
        env_prefix="AFI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Financial Intelligence API"

    # ── Environment ─────────────────────────────────────────────────────────
    # "development" (default) or "production". This is the switch that lets the
    # auth secret fail *closed* in production while a fresh clone still runs
    # locally with zero configuration. Anything other than "production" is
    # treated as development.
    environment: str = "development"

    # ── Authentication (V1.2, ADR-011) ──────────────────────────────────────
    # The JWT signing secret. Never hardcoded, never committed. In production it
    # MUST be set (`AFI_AUTH_SECRET`) or the app refuses to start; in
    # development a clearly-marked insecure fallback is derived so a fresh clone
    # runs. Resolved through `app.core.security.resolve_auth_secret`, never read
    # raw at a call site, so the fail-closed rule lives in exactly one place.
    auth_secret: str | None = None

    # Access-token lifetime. Short-lived by design (ADR-011): there is no
    # refresh token in V1.2, so this is the whole session window before a
    # re-login. Long enough not to interrupt a working session, short enough to
    # bound the exposure of a leaked token.
    access_token_ttl_minutes: int = 720

    # Session cookie. The token is delivered as an HttpOnly cookie (ADR-011),
    # so page JavaScript can never read it — closing off token theft via XSS.
    auth_cookie_name: str = "afi_session"

    # `Secure` requires HTTPS. Defaulting it to None means "decide from the
    # environment": on in production, off in development so the cookie survives
    # plain-HTTP localhost. Set explicitly to override.
    auth_cookie_secure: bool | None = None

    @property
    def is_production(self) -> bool:
        """True when running under production rules (fail-closed secret)."""
        return self.environment.strip().lower() == "production"

    @property
    def cookie_secure(self) -> bool:
        """Whether to mark the session cookie ``Secure``."""
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure
        return self.is_production

    # SQLite for V1 (ADR-014). PostgreSQL is a URL change plus a migration
    # pass, not a rewrite — nothing below depends on SQLite specifics except
    # the foreign-key pragma in `database.py`.
    database_url: str = DEFAULT_DATABASE_URL

    # Emit SQL to stdout. Useful when demoing what the ORM actually does.
    database_echo: bool = False

    # SRS-5.6/5.7: how far back a check-in may be backfilled. Enforced in the
    # service layer against the injected clock, never as a DB constraint —
    # "today" is not a deterministic value for a CHECK.
    checkin_backfill_days: int = 30

    # CORS origins for the React client. Empty by default.
    cors_origins: list[str] = []

    # ── Narration (Sprint 3) ────────────────────────────────────────────────
    # Default "none": a fresh clone serves template narration with no model
    # installed. Set to "ollama" to enable generated prose (ADR-008).
    llm_provider: str = "none"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_base_url: str = "http://127.0.0.1:11434"

    # A 7B model on CPU can take tens of seconds for a few hundred tokens.
    # Exceeding this is not an error — it falls back to a template.
    llm_timeout_seconds: float = 60.0

    # Low but non-zero. Sampling affects prose only; every claim and every
    # number is fixed before generation begins (07_AI_Architecture §7).
    llm_temperature: float = 0.2

    # Narration is sequential and slow. A full analysis run can produce a
    # dozen insights; narrating all of them would make one request take
    # minutes, so the highest-tier ones are narrated first and the rest are
    # returned with template prose.
    llm_max_generated: int = 5

    # ── Demo mode (Sprint 6) ────────────────────────────────────────────────
    # Permits the destructive seed/clear endpoints. OFF by default: these
    # routes wipe and replace all data with no authentication, so the safe
    # production default is disabled. Turn it on explicitly for a local demo
    # with `AFI_DEMO_MODE=true` (docker-compose sets it for the demo stack).
    # See ADR-014 — the single-local-profile assumption is what makes the
    # opt-in acceptable at all.
    demo_mode: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, constructed once."""
    return Settings()


settings = get_settings()
