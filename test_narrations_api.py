"""Narration endpoints — integration, with the model both absent and faked."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_llm_client
from app.llm.base import LLMTimeout
from app.main import app
from tests.narration.conftest import FakeLLMClient

DaysAgo = Callable[[int], str]

GOOD = {
    "observation": "Your spending was concentrated in a few categories.",
    "evidence": "The totals group tightly across the window.",
    "interpretation": "This is a description of what you recorded.",
    "suggestion": "You may want to review the largest category.",
}


@pytest.fixture
def with_model():
    """Install a fake model client for the duration of a test."""

    def install(client: FakeLLMClient) -> FakeLLMClient:
        app.dependency_overrides[get_llm_client] = lambda: client
        return client

    yield install
    app.dependency_overrides.pop(get_llm_client, None)


def log_expense(client: TestClient, day: str, paise: int) -> None:
    response = client.post(
        "/api/expenses",
        json={"expense_date": day, "amount_paise": paise, "category": "FOOD_DINING"},
    )
    assert response.status_code == 201, response.text


class TestWithoutAModel:
    def test_narration_works_with_nothing_installed(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        """The product is fully usable with the model absent (SRS-7.6)."""
        log_expense(client, days_ago(2), 45000)

        response = client.get("/api/narrations")

        assert response.status_code == 200
        body = response.json()
        assert body["narrations"]
        assert all(item["source"] == "TEMPLATE" for item in body["narrations"])

    def test_the_response_says_which_prose_you_got(self, client: TestClient) -> None:
        body = client.get("/api/narrations").json()

        assert body["narration"]["provider"] == "none"
        assert body["narration"]["generated"] == 0
        assert body["narration"]["templated"] == body["narration"]["total"]

    def test_every_narration_has_all_five_sections(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(2), 45000)

        for item in client.get("/api/narrations").json()["narrations"]:
            assert item["observation"].strip()
            assert item["evidence"].strip()
            assert item["interpretation"].strip()
            assert item["confidence"].strip()
            assert "suggestion" in item

    def test_a_fresh_profile_is_explained_not_left_empty(
        self, client: TestClient
    ) -> None:
        """PDR-030 — the honest empty state is the response a new user most
        often sees, so it is narrated like any other."""
        body = client.get("/api/narrations", params={"days": 14}).json()

        notices = [
            item for item in body["narrations"] if item["insight_type"] == "DATA_SUFFICIENCY"
        ]
        assert notices
        assert "enough" in notices[0]["observation"].lower()

    def test_the_status_endpoint_reports_template_mode(self, client: TestClient) -> None:
        status = client.get("/api/narrations/status").json()

        assert status["provider"] == "none"
        assert status["available"] is False
        assert status["narration_mode"] == "TEMPLATE"


class TestWithAModel:
    def test_a_clean_generation_is_served(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        with_model(FakeLLMClient(GOOD))
        log_expense(client, days_ago(2), 45000)

        body = client.get("/api/narrations").json()
        generated = [i for i in body["narrations"] if i["source"] == "LLM"]

        assert generated
        assert generated[0]["observation"] == GOOD["observation"]
        assert generated[0]["model"] == "fake:fake-model"

    def test_an_invented_number_never_reaches_the_client(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        """⭐ End to end: the model fabricates, the validator catches it, the
        user sees the template."""
        with_model(FakeLLMClient({**GOOD, "evidence": "You spent ₹9,876,543."}))
        log_expense(client, days_ago(2), 45000)

        body = client.get("/api/narrations").json()

        assert all(item["source"] == "TEMPLATE" for item in body["narrations"])
        assert "9,876,543" not in response_text(body)
        assert body["narration"]["rejected_by_validation"] >= 1

    def test_prohibited_advice_never_reaches_the_client(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        with_model(FakeLLMClient({**GOOD, "suggestion": "Consider a mutual fund."}))
        log_expense(client, days_ago(2), 45000)

        body = client.get("/api/narrations").json()

        assert "mutual fund" not in response_text(body)

    def test_the_rejection_reason_is_visible(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        """A client that cannot tell generated prose from a template cannot
        show the difference to a user."""
        with_model(FakeLLMClient({**GOOD, "evidence": "You spent ₹9,876,543."}))
        log_expense(client, days_ago(2), 45000)

        item = client.get("/api/narrations").json()["narrations"][0]

        assert item["fallback_reason"]
        assert item["validation_failures"]
        assert item["validation_failures"][0]["validator"] == "provenance"

    def test_a_model_timeout_is_not_an_error_response(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        with_model(FakeLLMClient(error=LLMTimeout("timed out after 60s")))
        log_expense(client, days_ago(2), 45000)

        response = client.get("/api/narrations")

        assert response.status_code == 200
        assert all(i["source"] == "TEMPLATE" for i in response.json()["narrations"])

    def test_generation_can_be_disabled_per_request(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        fake = with_model(FakeLLMClient(GOOD))
        log_expense(client, days_ago(2), 45000)

        body = client.get("/api/narrations", params={"generate": False}).json()

        assert fake.calls == []
        assert body["narration"]["generation_attempted"] == 0

    def test_the_generation_budget_is_respected(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        fake = with_model(FakeLLMClient(GOOD))
        log_expense(client, days_ago(2), 45000)

        body = client.get("/api/narrations").json()

        assert len(fake.calls) <= 5
        assert body["narration"]["generation_attempted"] == len(fake.calls)


class TestPromptPreview:
    def test_it_returns_the_exact_prompt_for_an_insight(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(2), 45000)
        insight = client.get("/api/insights").json()["insights"][0]

        response = client.get(f"/api/narrations/prompt/{insight['id']}")

        assert response.status_code == 200
        body = response.json()
        assert body["insight_type"] == insight["type"]
        assert "ABSOLUTE RULES" in body["system_prompt"]
        assert insight["type"] in body["user_prompt"]

    def test_it_lists_the_numbers_the_model_is_held_to(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(2), 45000)
        insight = client.get("/api/insights").json()["insights"][0]

        body = client.get(f"/api/narrations/prompt/{insight['id']}").json()

        assert "45000" in body["allowed_numbers"]
        assert "450" in body["allowed_numbers"], "the rupee form is licensed too"

    def test_the_schema_asks_for_no_confidence(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(2), 45000)
        insight = client.get("/api/insights").json()["insights"][0]

        body = client.get(f"/api/narrations/prompt/{insight['id']}").json()

        assert "confidence" not in body["output_schema"]["properties"]

    def test_an_unknown_insight_is_a_404(self, client: TestClient) -> None:
        response = client.get("/api/narrations/prompt/does-not-exist")

        assert response.status_code == 404
        assert response.json()["error"] == "NotFoundError"


class TestWindowHandling:
    def test_an_explicit_window_is_honoured(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        response = client.get(
            "/api/narrations",
            params={"start_date": days_ago(30), "end_date": days_ago(0)},
        )

        assert response.json()["run"]["window"]["days"] == 31

    def test_an_inverted_window_is_rejected(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        response = client.get(
            "/api/narrations",
            params={"start_date": days_ago(0), "end_date": days_ago(30)},
        )

        assert response.status_code == 422


def response_text(body: dict) -> str:
    """Every string a user could see in this response."""
    parts: list[str] = []
    for item in body["narrations"]:
        parts.extend(
            str(item[key])
            for key in ("observation", "evidence", "interpretation", "confidence")
        )
        if item["suggestion"]:
            parts.append(item["suggestion"])
    return "\n".join(parts)
