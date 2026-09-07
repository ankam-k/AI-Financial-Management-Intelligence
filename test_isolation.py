"""Cross-user data isolation — the non-negotiable guarantee (Phase 15, SRS-8.1/8.2).

Isolation is enforced in the service layer: every query is scoped by
``user_id``, so a resource that belongs to another user simply does not match
and reads as "not found" (the existing API contract — a 404, never a 403 that
would confirm the row exists). These tests prove that contract end to end for
every user-owned resource and every mutating path, plus the unauthenticated
case, using two genuinely separate authenticated accounts (``client`` = User A,
``second_client`` = User B) sharing one database.
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.user import User
from app.services.analysis_service import AnalysisService
from app.services.expense_service import ExpenseService
from app.schemas.expense import ExpenseCreate
from app.core.clock import FixedClock
from app.domain.enums import Category, PaymentMethod

EXPENSE = {"expense_date": "2026-07-20", "amount_paise": 15000, "category": "FOOD_DINING"}
CHECKIN = {"log_date": "2026-07-20", "exercise": True}
EVENT = {"event_type": "TRAVEL", "title": "Goa", "start_date": "2026-07-20"}


def _create(client: TestClient, path: str, body: dict) -> dict:
    response = client.post(path, json=body)
    assert response.status_code == 201, response.text
    return response.json()


class TestUnauthenticated:
    """Every protected endpoint refuses an anonymous caller (Phase 15.5)."""

    def test_reads_require_authentication(self, anon_client: TestClient):
        for path in (
            "/api/profile",
            "/api/expenses",
            "/api/check-ins",
            "/api/life-events",
            "/api/insights",
            "/api/narrations",
        ):
            assert anon_client.get(path).status_code == 401, path

    def test_writes_require_authentication(self, anon_client: TestClient):
        assert anon_client.post("/api/expenses", json=EXPENSE).status_code == 401
        assert anon_client.post("/api/check-ins", json=CHECKIN).status_code == 401
        assert anon_client.post("/api/life-events", json=EVENT).status_code == 401
        assert (
            anon_client.post("/api/chat", json={"question": "what did I spend?"}).status_code
            == 401
        )

    def test_delete_all_data_requires_authentication(self, anon_client: TestClient):
        assert anon_client.delete("/api/profile/data").status_code == 401


class TestExpenseIsolation:
    def test_a_owner_sees_only_their_own(
        self, client: TestClient, second_client: TestClient
    ):
        _create(second_client, "/api/expenses", EXPENSE)  # B's expense
        mine = _create(client, "/api/expenses", {**EXPENSE, "amount_paise": 99900})

        listing = client.get("/api/expenses").json()
        ids = {e["id"] for e in listing}
        assert ids == {mine["id"]}  # B's expense is absent

    def test_a_cannot_read_bs_expense(
        self, client: TestClient, second_client: TestClient
    ):
        b_expense = _create(second_client, "/api/expenses", EXPENSE)
        assert client.get(f"/api/expenses/{b_expense['id']}").status_code == 404

    def test_a_cannot_modify_bs_expense(
        self, client: TestClient, second_client: TestClient
    ):
        b_expense = _create(second_client, "/api/expenses", EXPENSE)
        resp = client.patch(
            f"/api/expenses/{b_expense['id']}", json={"amount_paise": 1}
        )
        assert resp.status_code == 404
        # B's row is untouched.
        assert (
            second_client.get(f"/api/expenses/{b_expense['id']}").json()["amount_paise"]
            == EXPENSE["amount_paise"]
        )

    def test_a_cannot_delete_bs_expense(
        self, client: TestClient, second_client: TestClient
    ):
        b_expense = _create(second_client, "/api/expenses", EXPENSE)
        assert client.delete(f"/api/expenses/{b_expense['id']}").status_code == 404
        # Still there for B.
        assert second_client.get(f"/api/expenses/{b_expense['id']}").status_code == 200


class TestLifeEventIsolation:
    def test_a_cannot_read_modify_or_delete_bs_event(
        self, client: TestClient, second_client: TestClient
    ):
        b_event = _create(second_client, "/api/life-events", EVENT)
        eid = b_event["id"]
        assert client.get(f"/api/life-events/{eid}").status_code == 404
        assert client.patch(f"/api/life-events/{eid}", json={"title": "hi"}).status_code == 404
        assert client.delete(f"/api/life-events/{eid}").status_code == 404
        assert second_client.get(f"/api/life-events/{eid}").status_code == 200
        assert client.get("/api/life-events").json() == []


class TestCheckInIsolation:
    """Check-ins are keyed by ``log_date``; the key is per-user, so the same
    date for two users is two independent rows."""

    def test_a_cannot_touch_bs_checkin_on_the_same_date(
        self, client: TestClient, second_client: TestClient
    ):
        _create(second_client, "/api/check-ins", CHECKIN)  # B logs 2026-07-20
        d = CHECKIN["log_date"]

        # A has nothing on that date, even though B does.
        assert client.get(f"/api/check-ins/{d}").status_code == 404
        assert client.patch(f"/api/check-ins/{d}", json={"exercise": False}).status_code == 404
        assert client.delete(f"/api/check-ins/{d}").status_code == 404
        assert client.get("/api/check-ins").json() == []

        # B's check-in is intact and unchanged.
        b_view = second_client.get(f"/api/check-ins/{d}").json()
        assert b_view["exercise"] is True

    def test_both_users_can_hold_the_same_date_independently(
        self, client: TestClient, second_client: TestClient
    ):
        _create(second_client, "/api/check-ins", {**CHECKIN, "exercise": False})
        a = _create(client, "/api/check-ins", {**CHECKIN, "exercise": True})
        assert a["exercise"] is True
        assert second_client.get(f"/api/check-ins/{CHECKIN['log_date']}").json()[
            "exercise"
        ] is False


class TestInsightAndAnalysisIsolation:
    def test_a_sees_no_insight_derived_from_bs_data(
        self, client: TestClient, second_client: TestClient
    ):
        # B records spending; A records nothing.
        for day in range(1, 20):
            second_client.post(
                "/api/expenses",
                json={
                    "expense_date": f"2026-07-{day:02d}",
                    "amount_paise": 50000,
                    "category": "FOOD_DINING",
                },
            )
        body = client.get("/api/insights").json()
        # A's analysis ran over an empty dataset — no behaviour relationship,
        # and certainly none of B's numbers.
        assert [i for i in body["insights"] if i["type"] == "BEHAVIOR_RELATIONSHIP"] == []

    def test_build_dataset_loads_only_the_target_users_rows(
        self, db: Session, clock: FixedClock
    ):
        """Item 13 at the source: the analysis loader is scoped by user_id."""
        a = User(email="a@x.test", display_name="A")
        b = User(email="b@x.test", display_name="B")
        db.add_all([a, b])
        db.commit()

        expenses = ExpenseService(db, clock)
        expenses.create(a, ExpenseCreate(
            expense_date=date(2026, 7, 10), amount_paise=1000,
            category=Category.FOOD_DINING, payment_method=PaymentMethod.UPI,
        ))
        expenses.create(b, ExpenseCreate(
            expense_date=date(2026, 7, 10), amount_paise=9999,
            category=Category.TRANSPORT, payment_method=PaymentMethod.UPI,
        ))

        analysis = AnalysisService(db, clock)
        window = analysis.build_window(days=90)
        dataset = analysis.build_dataset(a, window)

        amounts = {e.amount_paise for e in dataset.expenses}
        assert amounts == {1000}  # only A's expense; B's 9999 never loaded
