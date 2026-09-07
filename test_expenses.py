"""Expense endpoint behaviour."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def create_expense(client: TestClient, **overrides: object) -> dict:
    payload = {
        "expense_date": "2026-07-20",
        "amount_paise": 45000,
        "category": "FOOD_DINING",
        "payment_method": "UPI",
        "merchant": "Swiggy",
    }
    payload.update(overrides)
    response = client.post("/api/expenses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestCreateExpense:
    def test_records_an_expense(self, client: TestClient) -> None:
        body = create_expense(client)

        assert body["amount_paise"] == 45000
        assert body["category"] == "FOOD_DINING"
        assert body["merchant"] == "Swiggy"
        assert body["currency"] == "INR"

    def test_returns_a_formatted_amount_so_clients_never_divide_by_100(
        self, client: TestClient
    ) -> None:
        assert create_expense(client, amount_paise=45000)["amount_display"] == "450.00"
        assert create_expense(client, amount_paise=5)["amount_display"] == "0.05"

    def test_defaults_to_uncategorized(self, client: TestClient) -> None:
        response = client.post(
            "/api/expenses", json={"expense_date": "2026-07-20", "amount_paise": 100}
        )

        assert response.json()["category"] == "UNCATEGORIZED"

    @pytest.mark.parametrize("amount", [0, -1])
    def test_rejects_a_non_positive_amount(self, client: TestClient, amount: int) -> None:
        response = client.post(
            "/api/expenses", json={"expense_date": "2026-07-20", "amount_paise": amount}
        )

        assert response.status_code == 422

    def test_rejects_a_fractional_amount(self, client: TestClient) -> None:
        """₹120.50 is 12050, not 120.50. A float amount is a client bug."""
        response = client.post(
            "/api/expenses", json={"expense_date": "2026-07-20", "amount_paise": 120.50}
        )

        assert response.status_code == 422

    def test_rejects_an_unknown_category(self, client: TestClient) -> None:
        response = client.post(
            "/api/expenses",
            json={"expense_date": "2026-07-20", "amount_paise": 100, "category": "CRYPTO"},
        )

        assert response.status_code == 422

    def test_blank_merchant_is_stored_as_null(self, client: TestClient) -> None:
        assert create_expense(client, merchant="   ")["merchant"] is None


class TestListExpenses:
    def test_returns_newest_first(self, client: TestClient) -> None:
        create_expense(client, expense_date="2026-07-01")
        create_expense(client, expense_date="2026-07-25")
        create_expense(client, expense_date="2026-07-10")

        dates = [row["expense_date"] for row in client.get("/api/expenses").json()]

        assert dates == ["2026-07-25", "2026-07-10", "2026-07-01"]

    def test_filters_by_date_range_inclusively(self, client: TestClient) -> None:
        create_expense(client, expense_date="2026-07-01")
        create_expense(client, expense_date="2026-07-10")
        create_expense(client, expense_date="2026-07-20")

        response = client.get(
            "/api/expenses", params={"start_date": "2026-07-10", "end_date": "2026-07-20"}
        )

        assert [r["expense_date"] for r in response.json()] == [
            "2026-07-20",
            "2026-07-10",
        ]

    def test_filters_by_category(self, client: TestClient) -> None:
        create_expense(client, category="GROCERIES")
        create_expense(client, category="TRANSPORT")

        response = client.get("/api/expenses", params={"category": "GROCERIES"})

        assert len(response.json()) == 1
        assert response.json()[0]["category"] == "GROCERIES"

    def test_rejects_an_inverted_date_range(self, client: TestClient) -> None:
        response = client.get(
            "/api/expenses", params={"start_date": "2026-07-20", "end_date": "2026-07-01"}
        )

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"

    def test_paginates(self, client: TestClient) -> None:
        for day in range(1, 6):
            create_expense(client, expense_date=f"2026-07-0{day}")

        page = client.get("/api/expenses", params={"limit": 2, "offset": 2}).json()

        assert [r["expense_date"] for r in page] == ["2026-07-03", "2026-07-02"]


class TestReadExpense:
    def test_returns_the_expense(self, client: TestClient) -> None:
        created = create_expense(client)

        response = client.get(f"/api/expenses/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_unknown_id_is_a_404(self, client: TestClient) -> None:
        response = client.get("/api/expenses/does-not-exist")

        assert response.status_code == 404
        assert response.json()["error"] == "NotFoundError"


class TestUpdateExpense:
    def test_applies_a_partial_update(self, client: TestClient) -> None:
        created = create_expense(client)

        response = client.patch(
            f"/api/expenses/{created['id']}", json={"amount_paise": 99900}
        )

        body = response.json()
        assert body["amount_paise"] == 99900
        assert body["amount_display"] == "999.00"
        assert body["category"] == "FOOD_DINING", "omitted fields must not change"

    def test_explicit_null_clears_an_optional_field(self, client: TestClient) -> None:
        created = create_expense(client, merchant="Swiggy")

        response = client.patch(f"/api/expenses/{created['id']}", json={"merchant": None})

        assert response.json()["merchant"] is None

    def test_cannot_null_a_required_field(self, client: TestClient) -> None:
        created = create_expense(client)

        response = client.patch(f"/api/expenses/{created['id']}", json={"category": None})

        assert response.status_code == 422

    def test_unknown_id_is_a_404(self, client: TestClient) -> None:
        response = client.patch("/api/expenses/nope", json={"amount_paise": 1})

        assert response.status_code == 404


class TestDeleteExpense:
    def test_deletes(self, client: TestClient) -> None:
        created = create_expense(client)

        assert client.delete(f"/api/expenses/{created['id']}").status_code == 204
        assert client.get(f"/api/expenses/{created['id']}").status_code == 404

    def test_deleting_twice_is_a_404(self, client: TestClient) -> None:
        created = create_expense(client)
        client.delete(f"/api/expenses/{created['id']}")

        assert client.delete(f"/api/expenses/{created['id']}").status_code == 404
