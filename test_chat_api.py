"""Chat endpoint — integration, with the model absent and faked."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_llm_client
from app.main import app
from tests.narration.conftest import FakeLLMClient

DaysAgo = Callable[[int], str]


@pytest.fixture
def with_model():
    def install(client: FakeLLMClient) -> FakeLLMClient:
        app.dependency_overrides[get_llm_client] = lambda: client
        return client

    yield install
    app.dependency_overrides.pop(get_llm_client, None)


def seed(client: TestClient, days_ago: DaysAgo) -> None:
    client.patch("/api/profile", json={"monthly_budget_paise": 4_000_000})
    for offset, paise in ((3, 45000), (5, 120000), (9, 30000)):
        client.post(
            "/api/expenses",
            json={
                "expense_date": days_ago(offset),
                "amount_paise": paise,
                "category": "FOOD_DINING",
            },
        )
    client.post("/api/check-ins", json={"log_date": days_ago(1), "exercise": True})


def ask(client: TestClient, question: str, **extra) -> dict:
    response = client.post("/api/chat", json={"question": question, **extra})
    assert response.status_code == 200, response.text
    return response.json()


class TestAnsweringWithoutAModel:
    def test_it_answers_from_templates(self, client: TestClient, days_ago: DaysAgo) -> None:
        seed(client, days_ago)

        body = ask(client, "How much did I spend?")

        assert body["status"] == "ANSWERED"
        assert body["source"] == "TEMPLATE"
        assert body["intent"] == "SPENDING_SUMMARY"
        assert "You spent" in body["answer"]

    def test_it_cites_the_insights_it_used(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        seed(client, days_ago)

        body = ask(client, "Am I over budget?")

        assert body["citations"]
        assert any(c["insight_type"] == "BUDGET_UTILIZATION" for c in body["citations"])

    def test_it_reports_the_window_it_answered_over(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        body = ask(client, "How much did I spend?", days=30)

        assert body["window"]["days"] == 30

    def test_it_records_what_context_was_sent(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        seed(client, days_ago)

        body = ask(client, "Which category did I spend most on?")

        assert body["context_summary"]["intent"] == "CATEGORY_BREAKDOWN"
        assert body["context_summary"]["insight_count"] > 0


class TestRefusals:
    def test_a_prohibited_question_is_a_200_not_an_error(
        self, client: TestClient
    ) -> None:
        """Declining to recommend a fund is a correct outcome of a well-formed
        request. A client that had to catch it as an exception would treat the
        product's most important behaviour as a failure."""
        body = ask(client, "Should I invest my savings in a mutual fund?")

        assert body["status"] == "REFUSED"
        assert body["refusal_reason"] == "PROHIBITED_TOPIC"
        assert body["intent"] is None

    def test_a_prohibited_question_never_reaches_the_model(
        self, client: TestClient, with_model
    ) -> None:
        fake = with_model(FakeLLMClient({"answer": "Sure, buy an index fund."}))

        body = ask(client, "Which fund should I buy?")

        assert body["status"] == "REFUSED"
        assert fake.calls == []
        assert "index fund" not in body["answer"]

    def test_an_off_topic_question_is_refused_with_examples(
        self, client: TestClient
    ) -> None:
        body = ask(client, "What's the weather tomorrow?")

        assert body["refusal_reason"] == "NOT_ANSWERABLE_FROM_ANALYSIS"
        assert "Things I can answer" in body["answer"]

    def test_a_factual_question_about_a_loan_is_answered(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        seed(client, days_ago)

        body = ask(client, "How much did I pay in EMIs this quarter?")

        assert body["status"] == "ANSWERED"


class TestGeneratedAnswers:
    def test_a_clean_generation_is_served(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        seed(client, days_ago)
        with_model(
            FakeLLMClient({"answer": "Your spending is concentrated in a single category."})
        )

        body = ask(client, "Which category did I spend most on?")

        assert body["source"] == "LLM"
        assert body["model"] == "fake:fake-model"

    def test_an_invented_number_never_reaches_the_client(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        seed(client, days_ago)
        with_model(FakeLLMClient({"answer": "You spent ₹9,876,543 on food this month."}))

        body = ask(client, "How much did I spend?")

        assert body["source"] == "TEMPLATE"
        assert "9,876,543" not in body["answer"]
        assert body["validation_failures"][0]["validator"] == "provenance"

    def test_generation_can_be_disabled(
        self, client: TestClient, days_ago: DaysAgo, with_model
    ) -> None:
        seed(client, days_ago)
        fake = with_model(FakeLLMClient({"answer": "Something long enough to pass."}))

        body = ask(client, "How much did I spend?", generate=False)

        assert body["source"] == "TEMPLATE"
        assert fake.calls == []


class TestSingleTurn:
    def test_the_request_accepts_no_conversation_id(self, client: TestClient) -> None:
        """⭐ SRS-7.7 — single-turn is enforced by there being no field to put
        a prior turn in."""
        response = client.post(
            "/api/chat",
            json={"question": "How much did I spend?", "conversation_id": "abc"},
        )

        assert response.status_code == 422

    def test_the_request_accepts_no_history(self, client: TestClient) -> None:
        response = client.post(
            "/api/chat", json={"question": "And groceries?", "history": []}
        )

        assert response.status_code == 422

    def test_the_same_question_gives_the_same_answer(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        seed(client, days_ago)

        first = ask(client, "How much did I spend?")
        second = ask(client, "How much did I spend?")

        assert first["answer"] == second["answer"]

    def test_a_follow_up_has_no_antecedent_to_resolve(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        seed(client, days_ago)
        ask(client, "Which category did I spend most on?")

        body = ask(client, "What about it?")

        assert body["status"] == "REFUSED"


class TestValidation:
    def test_an_empty_question_is_rejected_by_the_schema(
        self, client: TestClient
    ) -> None:
        assert client.post("/api/chat", json={"question": ""}).status_code == 422

    def test_an_overlong_question_is_rejected_by_the_schema(
        self, client: TestClient
    ) -> None:
        assert client.post("/api/chat", json={"question": "a" * 600}).status_code == 422

    def test_a_malformed_date_is_a_domain_error(self, client: TestClient) -> None:
        response = client.post(
            "/api/chat", json={"question": "How much did I spend?", "start_date": "yesterday"}
        )

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"


class TestCapabilities:
    def test_it_lists_starter_questions(self, client: TestClient) -> None:
        body = client.get("/api/chat/capabilities").json()

        assert body["examples"]
        assert body["single_turn"] is True

    def test_it_lists_every_intent(self, client: TestClient) -> None:
        body = client.get("/api/chat/capabilities").json()

        assert "HABIT_RELATIONSHIP" in body["intents"]

    def test_it_says_no_history_is_kept(self, client: TestClient) -> None:
        body = client.get("/api/chat/capabilities").json()

        assert "No conversation history is kept" in body["note"]
