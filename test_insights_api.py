"""Insight endpoints — the API's view of the engine.

These are integration tests: real database, real routes, frozen clock. The
analytics themselves are covered by unit tests in ``tests/analysis/``; what is
being checked here is that the wiring loads the right rows, respects window
parameters, and serialises without transformation.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

DaysAgo = Callable[[int], str]


def log_expense(client: TestClient, day: str, paise: int, category: str = "FOOD_DINING") -> None:
    response = client.post(
        "/api/expenses",
        json={"expense_date": day, "amount_paise": paise, "category": category},
    )
    assert response.status_code == 201, response.text


def log_check_in(client: TestClient, day: str, **habits: object) -> None:
    response = client.post("/api/check-ins", json={"log_date": day, **habits})
    assert response.status_code == 201, response.text


class TestRunEndpoint:
    def test_a_fresh_profile_returns_a_valid_empty_run(self, client: TestClient) -> None:
        """No data is not an error. The engine still reports the facts it has."""
        response = client.get("/api/insights")

        assert response.status_code == 200
        body = response.json()
        assert body["run"]["engine_version"]
        assert body["run"]["inputs"] == {"expenses": 0, "check_ins": 0, "events": 0}
        assert {i["type"] for i in body["insights"]} == {
            "SPENDING_TOTAL",
            "HABIT_COMPLETION",
            "HABIT_MISSED_DAYS",
        }

    def test_the_default_window_is_ninety_days(self, client: TestClient) -> None:
        body = client.get("/api/insights").json()

        assert body["run"]["window"]["days"] == 90

    def test_recorded_expenses_reach_the_engine(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(3), 45000)
        log_expense(client, days_ago(2), 15000)

        body = client.get("/api/insights").json()
        total = next(i for i in body["insights"] if i["type"] == "SPENDING_TOTAL")

        assert total["metrics"]["total_paise"] == 60000
        assert body["run"]["inputs"]["expenses"] == 2

    def test_expenses_outside_the_window_are_excluded(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(3), 45000)
        log_expense(client, days_ago(200), 99000)

        body = client.get("/api/insights", params={"days": 30}).json()
        total = next(i for i in body["insights"] if i["type"] == "SPENDING_TOTAL")

        assert total["metrics"]["total_paise"] == 45000

    def test_an_explicit_window_is_honoured(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        response = client.get(
            "/api/insights",
            params={"start_date": days_ago(30), "end_date": days_ago(0)},
        )

        assert response.status_code == 200
        assert response.json()["run"]["window"]["days"] == 31

    def test_an_inverted_window_is_rejected(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        response = client.get(
            "/api/insights",
            params={"start_date": days_ago(0), "end_date": days_ago(30)},
        )

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"

    def test_an_oversized_window_is_rejected(self, client: TestClient) -> None:
        response = client.get("/api/insights", params={"days": 1000})

        assert response.status_code == 422


class TestHabitsReachTheEngine:
    def test_an_unlogged_habit_stays_unknown_through_the_api(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        """⭐ End to end: the client omits `alcohol`, the column stores NULL,
        and the engine reports it as unknown rather than as a recorded no."""
        log_check_in(client, days_ago(1), exercise=True)

        body = client.get("/api/insights").json()
        completion = next(i for i in body["insights"] if i["type"] == "HABIT_COMPLETION")
        coverage = {
            row["habit"]: row["recorded_days"] for row in completion["metrics"]["per_habit"]
        }

        assert coverage["exercise"] == 1
        assert coverage["alcohol"] == 0

    def test_a_recorded_negative_is_counted_as_data(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_check_in(client, days_ago(1), exercise=False)

        body = client.get("/api/insights").json()
        frequency = next(
            i for i in body["insights"] if i["type"] == "HABIT_EXERCISE_FREQUENCY"
        )

        assert frequency["metrics"]["recorded_days"] == 1
        assert frequency["metrics"]["frequency_ratio"] == 0.0


class TestBudget:
    def test_budget_insights_are_absent_until_a_budget_is_set(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(1), 45000)

        body = client.get("/api/insights").json()

        assert not [i for i in body["insights"] if i["type"] == "BUDGET_UTILIZATION"]

    def test_setting_a_budget_unlocks_the_insight(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        client.patch("/api/profile", json={"monthly_budget_paise": 1_000_000})
        log_expense(client, days_ago(1), 250_000)

        body = client.get("/api/insights").json()
        budget = next(i for i in body["insights"] if i["type"] == "BUDGET_UTILIZATION")

        assert budget["metrics"]["budget_paise"] == 1_000_000
        assert budget["metrics"]["utilization_ratio"] == pytest.approx(0.25)

    def test_the_budget_can_be_cleared(self, client: TestClient) -> None:
        client.patch("/api/profile", json={"monthly_budget_paise": 1_000_000})

        response = client.patch("/api/profile", json={"monthly_budget_paise": None})

        assert response.json()["monthly_budget_paise"] is None
        body = client.get("/api/insights").json()
        assert not [i for i in body["insights"] if i["type"] == "BUDGET_UTILIZATION"]

    def test_a_non_positive_budget_is_rejected(self, client: TestClient) -> None:
        assert client.patch("/api/profile", json={"monthly_budget_paise": 0}).status_code == 422


class TestEvents:
    def test_life_events_produce_summaries(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        client.post(
            "/api/life-events",
            json={
                "event_type": "TRAVEL",
                "title": "Goa",
                "start_date": days_ago(10),
                "end_date": days_ago(7),
            },
        )
        log_expense(client, days_ago(9), 80000)

        body = client.get("/api/insights").json()
        summary = next(i for i in body["insights"] if i["type"] == "EVENT_SUMMARY")

        assert summary["metrics"]["title"] == "Goa"
        assert summary["metrics"]["total_paise"] == 80000

    def test_an_event_overlapping_the_window_start_is_loaded(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        """Overlap, not containment — an event that began before the window
        still describes days inside it."""
        client.post(
            "/api/life-events",
            json={
                "event_type": "RELOCATION",
                "title": "Moved",
                "start_date": days_ago(40),
                "end_date": days_ago(25),
            },
        )

        body = client.get("/api/insights", params={"days": 30}).json()

        assert body["run"]["inputs"]["events"] == 1


class TestFilteredViews:
    def test_types_endpoint_lists_the_closed_set(self, client: TestClient) -> None:
        types = client.get("/api/insights/types").json()

        assert "BEHAVIOR_RELATIONSHIP" in types
        assert "DATA_SUFFICIENCY" in types

    def test_filtering_by_type_returns_only_that_type(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(1), 45000)

        rows = client.get("/api/insights/SPENDING_TOTAL").json()

        assert len(rows) == 1
        assert rows[0]["type"] == "SPENDING_TOTAL"

    def test_filtering_by_an_absent_type_returns_an_empty_list(
        self, client: TestClient
    ) -> None:
        assert client.get("/api/insights/EVENT_IMPACT").json() == []

    def test_an_unknown_type_is_rejected(self, client: TestClient) -> None:
        assert client.get("/api/insights/NOT_A_TYPE").status_code == 422

    def test_sufficiency_notices_are_reachable_by_type(
        self, client: TestClient
    ) -> None:
        rows = client.get("/api/insights/DATA_SUFFICIENCY", params={"days": 14}).json()

        assert rows and rows[0]["metrics"]["failed_gate"] == "G1_HISTORY"


class TestResponseShape:
    def test_every_insight_carries_the_contract_fields(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log_expense(client, days_ago(1), 45000)

        for insight in client.get("/api/insights").json()["insights"]:
            assert set(insight) == {
                "id",
                "type",
                "tier",
                "title_key",
                "subject",
                "window",
                "metrics",
                "evidence",
                "confidence",
                "created_at",
            }
            assert insight["evidence"], "an insight always carries evidence"

    def test_insight_ids_are_stable_across_requests(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        """Deterministic ids let a client diff two runs rather than treating
        every refresh as an entirely new set of findings."""
        log_expense(client, days_ago(1), 45000)

        first = [i["id"] for i in client.get("/api/insights").json()["insights"]]
        second = [i["id"] for i in client.get("/api/insights").json()["insights"]]

        assert first == second

    def test_data_is_scoped_to_the_current_profile(self, client: TestClient) -> None:
        log_expense(client, "2026-07-20", 45000)
        client.delete("/api/profile/data")

        body = client.get("/api/insights").json()

        assert body["run"]["inputs"]["expenses"] == 0
