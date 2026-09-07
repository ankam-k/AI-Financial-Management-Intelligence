"""Profile endpoint behaviour."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient


class TestReadProfile:
    def test_first_request_creates_the_local_profile(self, client: TestClient) -> None:
        response = client.get("/api/profile")

        assert response.status_code == 200
        body = response.json()
        assert body["display_name"] == "Local User"
        assert body["timezone"] == "Asia/Kolkata"
        assert body["currency"] == "INR"
        assert body["id"]

    def test_repeated_requests_return_the_same_profile(self, client: TestClient) -> None:
        first = client.get("/api/profile").json()
        second = client.get("/api/profile").json()

        assert first["id"] == second["id"], "the local profile must not be recreated"


class TestUpdateProfile:
    def test_updates_the_display_name(self, client: TestClient) -> None:
        response = client.patch("/api/profile", json={"display_name": "Pranay"})

        assert response.status_code == 200
        assert response.json()["display_name"] == "Pranay"
        assert client.get("/api/profile").json()["display_name"] == "Pranay"

    def test_omitted_fields_are_left_untouched(self, client: TestClient) -> None:
        client.patch("/api/profile", json={"display_name": "Pranay"})

        response = client.patch("/api/profile", json={"timezone": "Asia/Kolkata"})

        assert response.json()["display_name"] == "Pranay"

    def test_rejects_an_unknown_field(self, client: TestClient) -> None:
        response = client.patch("/api/profile", json={"emial": "typo@example.com"})

        assert response.status_code == 422, "extra='forbid' should catch typos"

    def test_rejects_a_blank_display_name(self, client: TestClient) -> None:
        assert client.patch("/api/profile", json={"display_name": ""}).status_code == 422


class TestDeleteAllData:
    def test_the_account_is_kept_and_stays_signed_in(
        self, client: TestClient
    ) -> None:
        """Phase 18: "Delete all data" empties the account but keeps it — the
        user stays signed in on the same profile, not logged out with a new id.
        """
        original_id = client.get("/api/profile").json()["id"]

        assert client.delete("/api/profile/data").status_code == 204
        assert client.get("/api/profile").json()["id"] == original_id

    def test_removes_every_record_the_profile_owned(self, client: TestClient) -> None:
        """Deletion is real and cascading — there is no soft-delete flag on
        user data (05_Database_Design.md §8, SRS-8.6)."""
        client.post(
            "/api/expenses", json={"expense_date": "2026-07-20", "amount_paise": 15000}
        )
        client.post("/api/check-ins", json={"log_date": "2026-07-20", "exercise": True})
        client.post(
            "/api/life-events",
            json={"event_type": "TRAVEL", "title": "Goa", "start_date": "2026-07-20"},
        )

        client.delete("/api/profile/data")

        assert client.get("/api/expenses").json() == []
        assert client.get("/api/check-ins").json() == []
        assert client.get("/api/life-events").json() == []


class TestOnboardingDefaults:
    def test_a_fresh_account_is_not_onboarded_and_has_no_preferences(
        self, client: TestClient
    ) -> None:
        body = client.get("/api/profile").json()

        assert body["onboarding_completed"] is False
        assert body["life_stage"] is None
        assert body["income_pattern"] is None
        assert body["work_context"] is None
        assert body["household_context"] is None
        assert body["focus_areas"] == []
        assert body["tracked_categories"] == []
        assert body["tracked_habits"] == []


class TestCompleteOnboarding:
    def test_records_answers_and_marks_onboarded(self, client: TestClient) -> None:
        response = client.post(
            "/api/profile/onboarding",
            json={
                "life_stage": "EARLY_CAREER",
                "income_pattern": "SALARIED_FIXED",
                "work_context": "HYBRID",
                "household_context": "SHARED",
                "focus_areas": ["UNDERSTAND_SPENDING", "SAVE_MORE"],
                "tracked_categories": ["FOOD_DINING", "TRANSPORT"],
                "tracked_habits": ["exercise", "sleep_minutes"],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["onboarding_completed"] is True
        assert body["life_stage"] == "EARLY_CAREER"
        assert body["work_context"] == "HYBRID"
        assert body["focus_areas"] == ["UNDERSTAND_SPENDING", "SAVE_MORE"]
        assert body["tracked_categories"] == ["FOOD_DINING", "TRANSPORT"]
        assert body["tracked_habits"] == ["exercise", "sleep_minutes"]

    def test_the_answers_persist(self, client: TestClient) -> None:
        client.post(
            "/api/profile/onboarding",
            json={"life_stage": "STUDENT", "focus_areas": ["BUILD_HEALTHY_HABITS"]},
        )

        body = client.get("/api/profile").json()
        assert body["onboarding_completed"] is True
        assert body["life_stage"] == "STUDENT"
        assert body["focus_areas"] == ["BUILD_HEALTHY_HABITS"]

    def test_an_empty_submission_still_marks_onboarded(self, client: TestClient) -> None:
        """Onboarding sets expectations, it never gates — skipping is valid."""
        response = client.post("/api/profile/onboarding", json={})

        assert response.status_code == 200
        assert response.json()["onboarding_completed"] is True

    def test_de_duplicates_a_repeated_selection(self, client: TestClient) -> None:
        body = client.post(
            "/api/profile/onboarding",
            json={"tracked_habits": ["exercise", "exercise", "alcohol"]},
        ).json()

        assert body["tracked_habits"] == ["exercise", "alcohol"]

    def test_rejects_an_unknown_life_stage(self, client: TestClient) -> None:
        response = client.post(
            "/api/profile/onboarding", json={"life_stage": "RETIRED"}
        )
        assert response.status_code == 422

    def test_rejects_an_unknown_focus_area(self, client: TestClient) -> None:
        response = client.post(
            "/api/profile/onboarding", json={"focus_areas": ["GET_RICH_QUICK"]}
        )
        assert response.status_code == 422

    def test_rejects_an_unknown_tracked_category(self, client: TestClient) -> None:
        response = client.post(
            "/api/profile/onboarding", json={"tracked_categories": ["CRYPTO"]}
        )
        assert response.status_code == 422

    def test_rejects_an_unknown_tracked_habit(self, client: TestClient) -> None:
        """``tracked_habits`` must be real check-in habit fields."""
        response = client.post(
            "/api/profile/onboarding", json={"tracked_habits": ["meditation"]}
        )
        assert response.status_code == 422


class TestUpdatePersonalisation:
    def test_patch_edits_preferences_after_onboarding(self, client: TestClient) -> None:
        client.post(
            "/api/profile/onboarding", json={"tracked_habits": ["exercise"]}
        )

        response = client.patch(
            "/api/profile", json={"tracked_habits": ["sleep_minutes", "alcohol"]}
        )

        assert response.status_code == 200
        assert response.json()["tracked_habits"] == ["sleep_minutes", "alcohol"]
        # Onboarding state is not disturbed by an ordinary settings edit.
        assert response.json()["onboarding_completed"] is True

    def test_patch_can_clear_a_preference_list(self, client: TestClient) -> None:
        client.patch("/api/profile", json={"focus_areas": ["SAVE_MORE"]})

        # A NOT NULL list column: null clears to an empty list, never NULL.
        response = client.patch("/api/profile", json={"focus_areas": None})

        assert response.status_code == 200
        assert response.json()["focus_areas"] == []

    def test_patch_can_clear_a_scalar_context(self, client: TestClient) -> None:
        client.patch("/api/profile", json={"life_stage": "FAMILY"})

        response = client.patch("/api/profile", json={"life_stage": None})

        assert response.status_code == 200
        assert response.json()["life_stage"] is None

    def test_omitted_personalisation_is_left_untouched(self, client: TestClient) -> None:
        client.patch("/api/profile", json={"life_stage": "ESTABLISHED"})

        # A budget-only edit must not disturb the personalisation fields.
        response = client.patch("/api/profile", json={"monthly_budget_paise": 5000000})

        assert response.json()["life_stage"] == "ESTABLISHED"


class TestPersonalisationNeverReachesTheEngine:
    """M5 invariant: personalisation drives the UI, never the analysis.

    The engine is fed a dataset built from expenses, check-ins and events — the
    ``User`` row and its preferences are never passed in (ADR-007). Asserted at
    the source level: no module under ``app/analysis/`` may so much as name a
    personalisation field, which would be the first sign one had leaked into a
    threshold or a gate.
    """

    PERSONALISATION_FIELDS = (
        "onboarding_completed",
        "life_stage",
        "income_pattern",
        "work_context",
        "household_context",
        "focus_areas",
        "tracked_categories",
        "tracked_habits",
    )

    def test_no_analysis_module_names_a_personalisation_field(self) -> None:
        analysis = Path(__file__).resolve().parents[1] / "backend" / "app" / "analysis"
        assert analysis.is_dir(), "analysis package not found — the check would be vacuous"

        offenders: dict[str, list[str]] = {}
        for module in sorted(analysis.rglob("*.py")):
            names = self._identifiers(module)
            hits = [f for f in self.PERSONALISATION_FIELDS if f in names]
            if hits:
                offenders[module.name] = hits

        assert offenders == {}, (
            f"analysis modules reference personalisation fields: {offenders}. "
            "Preferences drive UI prominence only and must never enter the "
            "engine (ADR-007; app/domain/preferences.py)."
        )

    @staticmethod
    def _identifiers(path: Path) -> set[str]:
        """Every attribute and name used in a module, from its AST."""
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                found.add(node.id)
            elif isinstance(node, ast.Attribute):
                found.add(node.attr)
        return found
