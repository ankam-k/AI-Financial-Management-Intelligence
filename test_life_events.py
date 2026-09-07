"""Life event endpoint behaviour."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def create_event(client: TestClient, **overrides: object) -> dict:
    payload: dict[str, object] = {
        "event_type": "TRAVEL",
        "title": "Goa trip",
        "start_date": "2026-07-10",
        "end_date": "2026-07-15",
    }
    payload.update(overrides)
    response = client.post("/api/life-events", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestCreateLifeEvent:
    def test_records_a_ranged_event(self, client: TestClient) -> None:
        body = create_event(client)

        assert body["event_type"] == "TRAVEL"
        assert body["title"] == "Goa trip"
        assert body["end_date"] == "2026-07-15"
        assert body["is_point_event"] is False

    def test_omitting_end_date_creates_a_point_event(self, client: TestClient) -> None:
        body = create_event(client, end_date=None, title="Diwali")

        assert body["end_date"] is None
        assert body["is_point_event"] is True

    def test_rejects_an_end_date_before_the_start(self, client: TestClient) -> None:
        response = client.post(
            "/api/life-events",
            json={
                "event_type": "TRAVEL",
                "title": "Backwards",
                "start_date": "2026-07-15",
                "end_date": "2026-07-10",
            },
        )

        assert response.status_code == 422

    def test_a_single_day_range_is_allowed(self, client: TestClient) -> None:
        body = create_event(client, start_date="2026-07-10", end_date="2026-07-10")

        assert body["end_date"] == "2026-07-10"

    def test_rejects_an_unknown_event_type(self, client: TestClient) -> None:
        response = client.post(
            "/api/life-events",
            json={"event_type": "PROMOTION", "title": "x", "start_date": "2026-07-10"},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("title", ["", "   "])
    def test_rejects_a_blank_title(self, client: TestClient, title: str) -> None:
        response = client.post(
            "/api/life-events",
            json={"event_type": "OTHER", "title": title, "start_date": "2026-07-10"},
        )

        assert response.status_code == 422


class TestListLifeEvents:
    def test_returns_most_recent_first(self, client: TestClient) -> None:
        create_event(client, start_date="2026-06-01", end_date=None)
        create_event(client, start_date="2026-07-20", end_date=None)
        create_event(client, start_date="2026-07-01", end_date=None)

        starts = [row["start_date"] for row in client.get("/api/life-events").json()]

        assert starts == ["2026-07-20", "2026-07-01", "2026-06-01"]

    def test_includes_an_event_that_began_before_the_window_and_overlaps_it(
        self, client: TestClient
    ) -> None:
        """The case containment-filtering would wrongly hide.

        A relocation that started in June and ended in July still explains
        July spending.
        """
        create_event(client, title="Relocation", start_date="2026-06-25", end_date="2026-07-05")

        response = client.get(
            "/api/life-events",
            params={"start_date": "2026-07-01", "end_date": "2026-07-31"},
        )

        assert [r["title"] for r in response.json()] == ["Relocation"]

    def test_excludes_an_event_that_ended_before_the_window(
        self, client: TestClient
    ) -> None:
        create_event(client, start_date="2026-05-01", end_date="2026-05-10")

        response = client.get(
            "/api/life-events",
            params={"start_date": "2026-07-01", "end_date": "2026-07-31"},
        )

        assert response.json() == []

    def test_excludes_an_event_that_begins_after_the_window(
        self, client: TestClient
    ) -> None:
        create_event(client, start_date="2026-09-01", end_date=None)

        response = client.get(
            "/api/life-events",
            params={"start_date": "2026-07-01", "end_date": "2026-07-31"},
        )

        assert response.json() == []

    def test_includes_a_point_event_inside_the_window(self, client: TestClient) -> None:
        create_event(client, title="Diwali", start_date="2026-07-15", end_date=None)

        response = client.get(
            "/api/life-events",
            params={"start_date": "2026-07-01", "end_date": "2026-07-31"},
        )

        assert [r["title"] for r in response.json()] == ["Diwali"]

    def test_filters_by_event_type(self, client: TestClient) -> None:
        create_event(client, event_type="TRAVEL")
        create_event(client, event_type="ILLNESS")

        response = client.get("/api/life-events", params={"event_type": "ILLNESS"})

        assert [r["event_type"] for r in response.json()] == ["ILLNESS"]


class TestReadLifeEvent:
    def test_returns_the_event(self, client: TestClient) -> None:
        created = create_event(client)

        assert client.get(f"/api/life-events/{created['id']}").json()["id"] == created["id"]

    def test_unknown_id_is_a_404(self, client: TestClient) -> None:
        assert client.get("/api/life-events/nope").status_code == 404


class TestUpdateLifeEvent:
    def test_applies_a_partial_update(self, client: TestClient) -> None:
        created = create_event(client)

        body = client.patch(
            f"/api/life-events/{created['id']}", json={"title": "Goa trip (extended)"}
        ).json()

        assert body["title"] == "Goa trip (extended)"
        assert body["start_date"] == "2026-07-10", "omitted fields must not change"

    def test_null_end_date_turns_a_range_into_a_point_event(
        self, client: TestClient
    ) -> None:
        created = create_event(client)

        body = client.patch(
            f"/api/life-events/{created['id']}", json={"end_date": None}
        ).json()

        assert body["end_date"] is None
        assert body["is_point_event"] is True

    def test_rejects_an_end_date_before_the_stored_start_date(
        self, client: TestClient
    ) -> None:
        """The check the schema alone cannot make: only ``end_date`` is sent,
        so validity depends on the row already in the database."""
        created = create_event(client, start_date="2026-07-10", end_date="2026-07-15")

        response = client.patch(
            f"/api/life-events/{created['id']}", json={"end_date": "2026-07-01"}
        )

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"

    def test_rejects_a_start_date_after_the_stored_end_date(
        self, client: TestClient
    ) -> None:
        created = create_event(client, start_date="2026-07-10", end_date="2026-07-15")

        response = client.patch(
            f"/api/life-events/{created['id']}", json={"start_date": "2026-07-20"}
        )

        assert response.status_code == 422

    def test_moving_both_dates_together_is_allowed(self, client: TestClient) -> None:
        created = create_event(client)

        body = client.patch(
            f"/api/life-events/{created['id']}",
            json={"start_date": "2026-08-01", "end_date": "2026-08-05"},
        ).json()

        assert body["start_date"] == "2026-08-01"
        assert body["end_date"] == "2026-08-05"

    def test_cannot_null_a_required_field(self, client: TestClient) -> None:
        created = create_event(client)

        response = client.patch(f"/api/life-events/{created['id']}", json={"title": None})

        assert response.status_code == 422

    def test_rejects_a_whitespace_only_title(self, client: TestClient) -> None:
        created = create_event(client)

        response = client.patch(f"/api/life-events/{created['id']}", json={"title": "   "})

        assert response.status_code == 422


class TestDeleteLifeEvent:
    def test_deletes(self, client: TestClient) -> None:
        created = create_event(client)

        assert client.delete(f"/api/life-events/{created['id']}").status_code == 204
        assert client.get(f"/api/life-events/{created['id']}").status_code == 404
