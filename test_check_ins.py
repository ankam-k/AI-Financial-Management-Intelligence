"""Check-in endpoint behaviour.

The tests in ``TestUnknownIsNotFalse`` are the reason this module exists.
Everything else here is ordinary CRUD.

Dates come from the ``days_ago`` fixture, which is anchored to the frozen
clock — the backfill-window assertions would otherwise pass all day and fail
at midnight.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

DaysAgo = Callable[[int], str]


def log(client: TestClient, log_date: str, **habits: object) -> dict:
    """Create a check-in and return the response body."""
    response = client.post("/api/check-ins", json={"log_date": log_date, **habits})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def yesterday(days_ago: DaysAgo) -> str:
    return days_ago(1)


class TestUnknownIsNotFalse:
    """⭐ SRS-5.5 — the distinction the whole analysis engine rests on."""

    def test_omitting_a_habit_records_unknown(
        self, client: TestClient, yesterday: str
    ) -> None:
        body = log(client, yesterday, exercise=True)

        assert body["alcohol"] is None, "an unmentioned habit is UNKNOWN, not False"
        assert body["work_mode"] is None
        assert body["sleep_hours"] is None

    def test_sending_false_records_an_explicit_negative(
        self, client: TestClient, yesterday: str
    ) -> None:
        body = log(client, yesterday, exercise=False)

        assert body["exercise"] is False, "an explicit 'no' must not become UNKNOWN"

    def test_zero_home_cooked_meals_is_a_recorded_value_not_unknown(
        self, client: TestClient, yesterday: str
    ) -> None:
        body = log(client, yesterday, home_cooked_meals=0)

        assert body["home_cooked_meals"] == 0
        assert body["home_cooked_meals"] is not None

    def test_a_date_with_no_row_is_404_rather_than_a_blank_record(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        """A fabricated empty row would be indistinguishable from a logged one."""
        assert client.get(f"/api/check-ins/{days_ago(3)}").status_code == 404

    def test_patching_a_habit_to_null_resets_it_to_unknown(
        self, client: TestClient, yesterday: str
    ) -> None:
        log(client, yesterday, exercise=False, stress_level=4)

        body = client.patch(
            f"/api/check-ins/{yesterday}", json={"exercise": None}
        ).json()

        assert body["exercise"] is None, "explicit null must clear the habit"
        assert body["stress_level"] == 4, "other habits must be untouched"

    def test_omitting_a_habit_in_a_patch_leaves_it_alone(
        self, client: TestClient, yesterday: str
    ) -> None:
        """The counterpart to the test above — same endpoint, opposite meaning."""
        log(client, yesterday, exercise=False, stress_level=4)

        body = client.patch(
            f"/api/check-ins/{yesterday}", json={"stress_level": 2}
        ).json()

        assert body["exercise"] is False, "omission must not clear a recorded negative"
        assert body["stress_level"] == 2


class TestCreateCheckIn:
    def test_stores_sleep_hours_without_a_float_column(
        self, client: TestClient, yesterday: str
    ) -> None:
        """Hours over the wire, integer minutes in the database, hours back."""
        assert log(client, yesterday, sleep_hours=7.5)["sleep_hours"] == 7.5

    def test_rejects_a_second_check_in_for_the_same_date(
        self, client: TestClient, yesterday: str
    ) -> None:
        log(client, yesterday, exercise=True)

        response = client.post(
            "/api/check-ins", json={"log_date": yesterday, "exercise": False}
        )

        assert response.status_code == 409
        assert response.json()["error"] == "ConflictError"

    def test_rejects_a_check_in_with_no_habits_recorded(
        self, client: TestClient, yesterday: str
    ) -> None:
        """Such a row records nothing a missing row does not, and would inflate
        the logging-coverage ratio the analysis engine gates on (SRS-6.2)."""
        response = client.post("/api/check-ins", json={"log_date": yesterday})

        assert response.status_code == 422
        assert "at least one habit" in response.json()["detail"]

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("sleep_hours", 25),
            ("sleep_hours", -1),
            ("home_cooked_meals", 4),
            ("stress_level", 0),
            ("stress_level", 6),
            ("work_mode", "HOLIDAY"),
        ],
    )
    def test_rejects_out_of_range_habits(
        self, client: TestClient, yesterday: str, field: str, value: object
    ) -> None:
        response = client.post(
            "/api/check-ins", json={"log_date": yesterday, field: value}
        )

        assert response.status_code == 422


class TestBackfillWindow:
    """SRS-5.6/5.7 — asserted against the frozen clock, so it cannot go flaky."""

    def test_today_is_allowed(self, client: TestClient, days_ago: DaysAgo) -> None:
        assert log(client, days_ago(0), exercise=True)["log_date"] == days_ago(0)

    def test_the_earliest_allowed_day_is_accepted(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        assert log(client, days_ago(30), exercise=True)["log_date"] == days_ago(30)

    def test_one_day_past_the_window_is_rejected(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        response = client.post(
            "/api/check-ins", json={"log_date": days_ago(31), "exercise": True}
        )

        assert response.status_code == 422
        assert "backfilled" in response.json()["detail"]

    def test_a_future_date_is_rejected(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        response = client.post(
            "/api/check-ins", json={"log_date": days_ago(-1), "exercise": True}
        )

        assert response.status_code == 422
        assert "future" in response.json()["detail"]


class TestListCheckIns:
    def test_returns_newest_first(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        for n in (1, 5, 3):
            log(client, days_ago(n), exercise=True)

        dates = [row["log_date"] for row in client.get("/api/check-ins").json()]

        assert dates == [days_ago(1), days_ago(3), days_ago(5)]

    def test_filters_by_date_range(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        for n in (1, 5, 10):
            log(client, days_ago(n), exercise=True)

        response = client.get(
            "/api/check-ins",
            params={"start_date": days_ago(6), "end_date": days_ago(0)},
        )

        assert [r["log_date"] for r in response.json()] == [days_ago(1), days_ago(5)]

    def test_unlogged_dates_are_absent_not_blank(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        log(client, days_ago(5), exercise=True)

        rows = client.get("/api/check-ins").json()

        assert len(rows) == 1, "the API must not fabricate rows for unlogged days"


class TestUpdateCheckIn:
    def test_unknown_date_is_a_404(
        self, client: TestClient, days_ago: DaysAgo
    ) -> None:
        response = client.patch(
            f"/api/check-ins/{days_ago(3)}", json={"exercise": True}
        )

        assert response.status_code == 404

    def test_rejects_an_update_that_would_empty_the_record(
        self, client: TestClient, yesterday: str
    ) -> None:
        log(client, yesterday, exercise=True)

        response = client.patch(f"/api/check-ins/{yesterday}", json={"exercise": None})

        assert response.status_code == 422
        assert "Delete it instead" in response.json()["detail"]

    def test_a_rejected_update_leaves_the_stored_row_unchanged(
        self, client: TestClient, yesterday: str
    ) -> None:
        log(client, yesterday, exercise=True)
        client.patch(f"/api/check-ins/{yesterday}", json={"exercise": None})

        assert client.get(f"/api/check-ins/{yesterday}").json()["exercise"] is True

    def test_rejects_an_unknown_field(
        self, client: TestClient, yesterday: str
    ) -> None:
        log(client, yesterday, exercise=True)

        response = client.patch(f"/api/check-ins/{yesterday}", json={"excercise": True})

        assert response.status_code == 422


class TestDeleteCheckIn:
    def test_deleting_returns_the_date_to_unknown(
        self, client: TestClient, yesterday: str
    ) -> None:
        log(client, yesterday, exercise=True)

        assert client.delete(f"/api/check-ins/{yesterday}").status_code == 204
        assert client.get(f"/api/check-ins/{yesterday}").status_code == 404

    def test_the_date_can_then_be_logged_again(
        self, client: TestClient, yesterday: str
    ) -> None:
        log(client, yesterday, exercise=True)
        client.delete(f"/api/check-ins/{yesterday}")

        assert log(client, yesterday, exercise=False)["exercise"] is False
