"""Demo-mode endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _enable_demo_mode():
    """Demo mode is OFF by default in V1.1 (destructive routes are opt-in).

    These endpoints only exist to be exercised, so this module turns the switch
    on and restores whatever the process default was afterwards.
    """
    original = settings.demo_mode
    settings.demo_mode = True
    yield
    settings.demo_mode = original


@pytest.fixture
def demo_disabled():
    settings.demo_mode = False
    yield
    settings.demo_mode = True


@pytest.fixture
def demo_client(anon_client: TestClient) -> TestClient:
    """A client authenticated as the **shared demo account** (§9).

    Entering the demo seeds it on first use, so the returned client is signed in
    as the demo user and its data is already loaded. This is how the demo
    dataset is reached in V1.2 — it lives in its own ``is_demo`` account, not in
    any real user's rows, so reading insights from it requires a demo session.
    """
    response = anon_client.post("/api/auth/demo")
    assert response.status_code == 200, response.text
    assert response.json()["is_demo"] is True
    return anon_client


class TestStatus:
    def test_it_reports_an_empty_database(self, client: TestClient) -> None:
        body = client.get("/api/demo/status").json()

        assert body["is_empty"] is True
        assert body["enabled"] is True

    def test_it_is_available_even_when_seeding_is_disabled(
        self, client: TestClient, demo_disabled
    ) -> None:
        """Reading what is loaded is not destructive."""
        body = client.get("/api/demo/status").json()

        assert body["enabled"] is False


class TestDesign:
    def test_it_publishes_the_planted_patterns(self, client: TestClient) -> None:
        """Exposed so a reviewer can check the associations on screen are the
        ones the generator set out to create."""
        body = client.get("/api/demo/design").json()

        pairs = {(p["habit"], p["category"]) for p in body["planted_patterns"]}
        assert ("exercise", "FOOD_DINING") in pairs

    def test_it_publishes_the_negative_controls(self, client: TestClient) -> None:
        body = client.get("/api/demo/design").json()

        assert set(body["negative_controls"]) == {"alcohol", "work_mode"}

    def test_it_publishes_the_seed(self, client: TestClient) -> None:
        assert client.get("/api/demo/design").json()["seed"] > 0


class TestSeeding:
    def test_it_loads_a_full_dataset(self, client: TestClient) -> None:
        body = client.post("/api/demo/seed").json()

        assert body["expenses"] > 300
        assert body["check_ins"] > 150
        assert body["events"] >= 3
        assert body["profile"]

    def test_the_seeded_data_produces_a_correlational_insight(
        self, demo_client: TestClient
    ) -> None:
        """⭐ End to end, this is OEQ-004 closed: a T3 insight is reachable
        through the API, which it was not before this sprint. Read from the demo
        account itself, where the demo dataset lives (§9)."""
        body = demo_client.get("/api/insights").json()
        relationships = [
            i for i in body["insights"] if i["type"] == "BEHAVIOR_RELATIONSHIP"
        ]

        assert relationships, "no T3 insight — the demo does not demonstrate the product"
        assert relationships[0]["confidence"] >= 0.9

    def test_the_seeded_data_narrates(self, demo_client: TestClient) -> None:
        body = demo_client.get("/api/narrations").json()
        types = {n["insight_type"] for n in body["narrations"]}

        assert "BEHAVIOR_RELATIONSHIP" in types

    def test_the_assistant_can_answer_from_it(self, demo_client: TestClient) -> None:
        body = demo_client.post(
            "/api/chat", json={"question": "How has my gym routine affected my spending?"}
        ).json()

        assert body["status"] == "ANSWERED"
        assert body["citations"]

    def test_seeding_twice_does_not_double_the_data(self, client: TestClient) -> None:
        first = client.post("/api/demo/seed").json()
        second = client.post("/api/demo/seed").json()

        assert first["expenses"] == second["expenses"]

    def test_a_reference_date_can_be_pinned(self, client: TestClient) -> None:
        body = client.post("/api/demo/seed", params={"reference_date": "2026-07-28"}).json()

        assert body["latest"] == "2026-07-28"


class TestClearing:
    def test_it_removes_everything(self, client: TestClient) -> None:
        client.post("/api/demo/seed")

        body = client.request("DELETE", "/api/demo").json()

        assert body["is_empty"] is True
        assert client.get("/api/expenses").json() == []


class TestGating:
    def test_seeding_is_refused_when_demo_mode_is_off(
        self, client: TestClient, demo_disabled
    ) -> None:
        response = client.post("/api/demo/seed")

        assert response.status_code == 422
        assert "Demo mode is disabled" in response.json()["detail"]

    def test_clearing_is_refused_when_demo_mode_is_off(
        self, client: TestClient, demo_disabled
    ) -> None:
        assert client.request("DELETE", "/api/demo").status_code == 422

    def test_the_refusal_names_the_cli_alternative(
        self, client: TestClient, demo_disabled
    ) -> None:
        assert "python -m app.demo seed" in client.post("/api/demo/seed").json()["detail"]


class TestDemoSeparation:
    """§9 — the demo dataset lives in its own account and never leaks into a
    real user's rows (nor the reverse)."""

    def test_entering_the_demo_yields_a_distinct_demo_account(
        self, client: TestClient
    ) -> None:
        """A real User A already exists (``client``); entering the demo returns a
        *different* account flagged ``is_demo``."""
        real_id = client.get("/api/profile").json()["id"]

        demo = TestClient(app)
        body = demo.post("/api/auth/demo").json()

        assert body["is_demo"] is True
        assert body["id"] != real_id
        assert body["email"] is None  # passwordless, unreachable via login

    def test_seeding_never_touches_a_real_account(self, client: TestClient) -> None:
        """Seeding the demo (however triggered) leaves User A's data empty — no
        expenses, and none of the demo's signature correlational insights."""
        client.post("/api/demo/seed")

        assert client.get("/api/expenses").json() == []
        insights = client.get("/api/insights").json()["insights"]
        assert not [i for i in insights if i["type"] == "BEHAVIOR_RELATIONSHIP"]

    def test_a_real_users_data_is_invisible_from_the_demo(
        self, client: TestClient, days_ago
    ) -> None:
        """User A records an expense; the demo account never sees it."""
        client.post(
            "/api/expenses",
            json={
                "expense_date": days_ago(1),
                "amount_paise": 12345,
                "category": "FOOD_DINING",
                "payment_method": "UPI",
                "merchant": "User A only",
            },
        )

        demo = TestClient(app)
        demo.post("/api/auth/demo")
        merchants = {e["merchant"] for e in demo.get("/api/expenses").json()}

        assert "User A only" not in merchants

    def test_the_demo_account_arrives_onboarded(self, demo_client: TestClient) -> None:
        """A demo visitor never sees the first-run onboarding wizard."""
        profile = demo_client.get("/api/profile").json()

        assert profile["onboarding_completed"] is True
        assert profile["tracked_habits"]

    def test_entering_the_demo_seeds_it_on_first_use(
        self, anon_client: TestClient
    ) -> None:
        """The demo account is never handed over empty."""
        anon_client.post("/api/auth/demo")

        assert anon_client.get("/api/expenses").json(), "demo entered empty"

    def test_re_entering_the_demo_does_not_double_the_data(
        self, anon_client: TestClient
    ) -> None:
        anon_client.post("/api/auth/demo")
        count_before = len(anon_client.get("/api/expenses").json())

        second = TestClient(app)  # shares the per-test database override
        second.post("/api/auth/demo")

        assert len(second.get("/api/expenses").json()) == count_before

    def test_entering_the_demo_is_refused_when_demo_mode_is_off(
        self, demo_disabled
    ) -> None:
        demo = TestClient(app)
        response = demo.post("/api/auth/demo")

        assert response.status_code == 422
        assert "Demo mode is disabled" in response.json()["detail"]
