"""Ollama adapter (ADR-008).

Local inference: financial data never leaves the deployment, which is the
privacy commitment the product makes rather than a deployment convenience.

Built on ``urllib`` from the standard library rather than ``httpx``. The
request is one blocking POST to a loopback address from a sync route — an
async HTTP client would add a runtime dependency and a thread-pool bridge to
buy nothing. If Sprint 4 needs concurrent generation, that is the moment to
revisit it.

**JSON-schema-constrained generation** (ADR-008 §4.4): the schema is passed as
Ollama's ``format`` field, so the model is decoded against a grammar rather
than asked politely for JSON. This bounds the surface the validators must
check — they never have to parse prose looking for a structure.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any

from app.llm.base import LLMHealth, LLMProtocolError, LLMTimeout, LLMUnavailable


class OllamaClient:
    """Talks to a local Ollama server over HTTP."""

    provider = "ollama"

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 60.0,
        temperature: float = 0.2,
    ) -> None:
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        # Low but non-zero: narration is prose, and a fully greedy decode
        # produces stilted repetition. It cannot affect claims or numbers,
        # which are fixed before generation begins (07_AI_Architecture §7).
        self._temperature = temperature

    # ── Public API ──────────────────────────────────────────────────────────

    def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "options": {"temperature": self._temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        body = self._post("/api/chat", payload, timeout=self._timeout)

        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMProtocolError(
                f"Ollama response had no message content: {body!r:.200}"
            ) from exc

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMProtocolError(
                f"Model returned text that is not JSON despite a schema: {content!r:.200}"
            ) from exc

        if not isinstance(parsed, dict):
            raise LLMProtocolError(f"Model returned {type(parsed).__name__}, expected an object")

        return parsed

    def health(self) -> LLMHealth:
        """Check reachability and whether the configured model is present."""
        try:
            body = self._post("/api/tags", None, timeout=min(5.0, self._timeout), method="GET")
        except LLMTimeout:
            return self._unhealthy("Ollama did not respond in time.")
        except LLMUnavailable as exc:
            return self._unhealthy(str(exc))
        except LLMProtocolError as exc:
            return self._unhealthy(f"Unexpected response from Ollama: {exc}")

        installed = {
            entry.get("name", "") for entry in body.get("models", []) if isinstance(entry, dict)
        }
        # Ollama reports `qwen2.5:7b-instruct`; a bare `qwen2.5` should match it.
        if any(name == self.model or name.startswith(f"{self.model}:") for name in installed):
            return LLMHealth(
                provider=self.provider,
                model=self.model,
                available=True,
                detail="Ready.",
            )

        return self._unhealthy(
            f"Ollama is running but '{self.model}' is not installed. "
            f"Run: ollama pull {self.model}"
        )

    # ── Internals ───────────────────────────────────────────────────────────

    def _unhealthy(self, detail: str) -> LLMHealth:
        return LLMHealth(
            provider=self.provider, model=self.model, available=False, detail=detail
        )

    def _post(
        self,
        path: str,
        payload: dict[str, Any] | None,
        *,
        timeout: float,
        method: str = "POST",
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except socket.timeout as exc:
            raise LLMTimeout(f"Ollama timed out after {timeout:g}s") from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            raise LLMProtocolError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            # `URLError.reason` is a socket.timeout for read timeouts on some
            # platforms, so the check has to happen here too.
            if isinstance(exc.reason, socket.timeout):
                raise LLMTimeout(f"Ollama timed out after {timeout:g}s") from exc
            raise LLMUnavailable(
                f"Cannot reach Ollama at {self._base_url}: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise LLMUnavailable(f"Cannot reach Ollama at {self._base_url}: {exc}") from exc

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMProtocolError("Ollama returned a non-JSON body") from exc

        if not isinstance(decoded, dict):
            raise LLMProtocolError(f"Ollama returned {type(decoded).__name__}, expected an object")

        return decoded
