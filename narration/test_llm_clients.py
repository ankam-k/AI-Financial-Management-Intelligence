"""The LLM adapters.

The Ollama client is tested against a stubbed transport rather than a running
server: these assert the adapter's contract — that every transport failure
becomes an ``LLMError`` and that a schema is actually sent — which is what the
renderer depends on. Whether Ollama itself works is Ollama's test suite.
"""

from __future__ import annotations

import io
import json
import socket
import urllib.error
from typing import Any

import pytest

from app.core.config import Settings
from app.llm.base import (
    LLMClient,
    LLMProtocolError,
    LLMTimeout,
    LLMUnavailable,
)
from app.llm.factory import build_llm_client
from app.llm.null import NullLLMClient
from app.llm.ollama import OllamaClient

SCHEMA: dict[str, Any] = {"type": "object", "properties": {"observation": {"type": "string"}}}


def chat_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {"message": {"role": "assistant", "content": json.dumps(payload)}}


class StubTransport:
    """Stands in for ``urllib.request.urlopen``."""

    def __init__(self, body: Any = None, *, error: Exception | None = None) -> None:
        self._body = body
        self._error = error
        self.requests: list[Any] = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        raw = json.dumps(self._body).encode() if not isinstance(self._body, bytes) else self._body
        return _Response(raw)


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


@pytest.fixture
def client() -> OllamaClient:
    return OllamaClient(model="qwen2.5:7b-instruct", timeout_seconds=5.0)


class TestNullClient:
    def test_it_satisfies_the_protocol(self) -> None:
        assert isinstance(NullLLMClient(), LLMClient)

    def test_it_refuses_immediately(self) -> None:
        with pytest.raises(LLMUnavailable, match="No LLM provider configured"):
            NullLLMClient().complete_json(system="s", user="u", schema=SCHEMA)

    def test_its_health_explains_the_consequence(self) -> None:
        health = NullLLMClient().health()

        assert health.available is False
        assert "template" in health.detail.lower()


class TestOllamaClient:
    def test_it_satisfies_the_protocol(self, client: OllamaClient) -> None:
        assert isinstance(client, LLMClient)

    def test_a_good_response_is_parsed(self, client: OllamaClient, monkeypatch) -> None:
        transport = StubTransport(chat_response({"observation": "You spent more."}))
        monkeypatch.setattr("urllib.request.urlopen", transport)

        result = client.complete_json(system="s", user="u", schema=SCHEMA)

        assert result == {"observation": "You spent more."}

    def test_the_schema_is_sent_for_constrained_decoding(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        """ADR-008 §4.4 — the model is decoded against a grammar, not asked
        politely for JSON."""
        transport = StubTransport(chat_response({"observation": "x"}))
        monkeypatch.setattr("urllib.request.urlopen", transport)

        client.complete_json(system="s", user="u", schema=SCHEMA)

        sent = json.loads(transport.requests[0].data)
        assert sent["format"] == SCHEMA
        assert sent["stream"] is False
        assert sent["model"] == "qwen2.5:7b-instruct"

    def test_it_sends_no_conversation_history(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        """Single-turn is enforced by the absence of a mechanism for anything
        else (SRS-7.7)."""
        transport = StubTransport(chat_response({"observation": "x"}))
        monkeypatch.setattr("urllib.request.urlopen", transport)

        client.complete_json(system="s", user="u", schema=SCHEMA)

        sent = json.loads(transport.requests[0].data)
        assert [m["role"] for m in sent["messages"]] == ["system", "user"]

    def test_a_timeout_becomes_llm_timeout(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen", StubTransport(error=socket.timeout("slow"))
        )

        with pytest.raises(LLMTimeout):
            client.complete_json(system="s", user="u", schema=SCHEMA)

    def test_a_timeout_wrapped_in_urlerror_is_also_caught(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        """Some platforms surface read timeouts through URLError."""
        monkeypatch.setattr(
            "urllib.request.urlopen",
            StubTransport(error=urllib.error.URLError(socket.timeout("slow"))),
        )

        with pytest.raises(LLMTimeout):
            client.complete_json(system="s", user="u", schema=SCHEMA)

    def test_a_refused_connection_becomes_llm_unavailable(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            StubTransport(error=urllib.error.URLError(ConnectionRefusedError())),
        )

        with pytest.raises(LLMUnavailable, match="Cannot reach Ollama"):
            client.complete_json(system="s", user="u", schema=SCHEMA)

    def test_an_http_error_becomes_a_protocol_error(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        error = urllib.error.HTTPError(
            url="http://x", code=404, msg="not found", hdrs=None, fp=io.BytesIO(b"no model")
        )
        monkeypatch.setattr("urllib.request.urlopen", StubTransport(error=error))

        with pytest.raises(LLMProtocolError, match="404"):
            client.complete_json(system="s", user="u", schema=SCHEMA)

    def test_non_json_content_becomes_a_protocol_error(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        """A model that ignores the grammar and writes prose."""
        transport = StubTransport({"message": {"content": "Sure! Here you go:"}})
        monkeypatch.setattr("urllib.request.urlopen", transport)

        with pytest.raises(LLMProtocolError, match="not JSON"):
            client.complete_json(system="s", user="u", schema=SCHEMA)

    def test_a_missing_message_becomes_a_protocol_error(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        monkeypatch.setattr("urllib.request.urlopen", StubTransport({"done": True}))

        with pytest.raises(LLMProtocolError):
            client.complete_json(system="s", user="u", schema=SCHEMA)

    def test_a_json_array_becomes_a_protocol_error(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        transport = StubTransport(chat_response(["not", "an", "object"]))
        monkeypatch.setattr("urllib.request.urlopen", transport)

        with pytest.raises(LLMProtocolError, match="expected an object"):
            client.complete_json(system="s", user="u", schema=SCHEMA)


class TestOllamaHealth:
    def test_health_never_raises_when_unreachable(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            StubTransport(error=urllib.error.URLError(ConnectionRefusedError())),
        )

        health = client.health()

        assert health.available is False
        assert "Cannot reach Ollama" in health.detail

    def test_an_installed_model_is_reported_ready(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            StubTransport({"models": [{"name": "qwen2.5:7b-instruct"}]}),
        )

        assert client.health().available is True

    def test_a_missing_model_says_how_to_install_it(
        self, client: OllamaClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen", StubTransport({"models": [{"name": "llama3:8b"}]})
        )

        health = client.health()

        assert health.available is False
        assert "ollama pull qwen2.5:7b-instruct" in health.detail

    def test_a_bare_model_name_matches_a_tagged_install(self, monkeypatch) -> None:
        client = OllamaClient(model="qwen2.5")
        monkeypatch.setattr(
            "urllib.request.urlopen",
            StubTransport({"models": [{"name": "qwen2.5:7b-instruct"}]}),
        )

        assert client.health().available is True


class TestFactory:
    def test_the_default_is_no_model(self) -> None:
        """A fresh clone serves template narration with nothing installed."""
        client = build_llm_client(Settings(llm_provider="none"))

        assert isinstance(client, NullLLMClient)

    def test_ollama_is_selected_by_configuration(self) -> None:
        client = build_llm_client(
            Settings(llm_provider="ollama", llm_model="qwen2.5:7b-instruct")
        )

        assert isinstance(client, OllamaClient)
        assert client.model == "qwen2.5:7b-instruct"

    def test_the_provider_name_is_case_insensitive(self) -> None:
        assert isinstance(build_llm_client(Settings(llm_provider="OLLAMA")), OllamaClient)

    def test_an_unknown_provider_degrades_rather_than_crashes(self) -> None:
        """A typo in an environment variable should cost fluency, not the
        ability to start the API."""
        assert isinstance(build_llm_client(Settings(llm_provider="gpt-9")), NullLLMClient)

    def test_configuration_flows_through(self) -> None:
        client = build_llm_client(
            Settings(
                llm_provider="ollama",
                llm_model="mistral",
                llm_base_url="http://elsewhere:1234/",
            )
        )

        assert client.model == "mistral"
        assert client._base_url == "http://elsewhere:1234"
