"""Authentication: registration, login, sessions, and token handling.

These cover Phase 15's auth cases (valid/invalid login, missing/expired token,
logout, current-user resolution). Cross-user *data* isolation lives in
``test_isolation.py`` (M4), which builds on the register/login helpers here.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    resolve_auth_secret,
    verify_password,
)
from app.models.user import User
from tests.conftest import FROZEN_NOW

COOKIE = settings.auth_cookie_name


@pytest.fixture
def client(anon_client: TestClient) -> TestClient:
    """Auth tests drive registration/login themselves, so they need a client
    that is NOT already signed in — unlike the shared authenticated ``client``.
    """
    return anon_client


def register(client: TestClient, email: str, password: str = "correct horse", **kw):
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password, **kw},
    )


class TestRegistration:
    def test_register_creates_account_and_starts_a_session(self, client: TestClient):
        response = register(client, "ada@example.com", display_name="Ada")

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "ada@example.com"
        assert body["display_name"] == "Ada"
        assert body["is_demo"] is False
        # The session cookie is set, and it is HttpOnly.
        assert COOKIE in response.cookies
        set_cookie = response.headers["set-cookie"].lower()
        assert "httponly" in set_cookie
        # No secret ever leaves the server.
        assert "password" not in body
        assert "password_hash" not in body

    def test_a_new_account_can_immediately_reach_its_own_data(self, client: TestClient):
        register(client, "ada@example.com")
        # The cookie from registration authenticates the follow-up call.
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == "ada@example.com"

    def test_email_is_normalised(self, client: TestClient):
        assert register(client, "  ADA@Example.COM ").status_code == 201
        # A differently-cased duplicate is the same account.
        assert register(client, "ada@example.com").status_code == 409

    def test_duplicate_email_is_a_409(self, client: TestClient):
        register(client, "ada@example.com")
        dup = register(client, "ada@example.com")
        assert dup.status_code == 409
        assert "already exists" in dup.json()["detail"]

    @pytest.mark.parametrize("email", ["not-an-email", "a@b", "@x.com", "a b@x.com"])
    def test_invalid_email_is_rejected(self, client: TestClient, email: str):
        assert register(client, email).status_code == 422

    def test_short_password_is_rejected(self, client: TestClient):
        assert register(client, "ada@example.com", password="short").status_code == 422

    def test_display_name_defaults_to_the_email_local_part(self, client: TestClient):
        body = register(client, "ada@example.com").json()
        assert body["display_name"] == "ada"


class TestLogin:
    def test_valid_login_starts_a_session(self, client: TestClient):
        register(client, "ada@example.com", password="a good password")
        client.cookies.clear()  # forget the registration session

        response = client.post(
            "/api/auth/login",
            json={"email": "ada@example.com", "password": "a good password"},
        )
        assert response.status_code == 200
        assert COOKIE in response.cookies
        assert client.get("/api/auth/me").json()["email"] == "ada@example.com"

    def test_wrong_password_is_a_generic_401(self, client: TestClient):
        register(client, "ada@example.com", password="a good password")
        client.cookies.clear()

        response = client.post(
            "/api/auth/login",
            json={"email": "ada@example.com", "password": "wrong password"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."

    def test_unknown_email_gives_the_identical_401(self, client: TestClient):
        # No account registered. The message must match the wrong-password case
        # exactly, so the response never reveals whether the email exists.
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "whatever now"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."


class TestSession:
    def test_me_without_a_token_is_401(self, client: TestClient):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_accepts_a_bearer_token(self, client: TestClient):
        token = register(client, "ada@example.com").cookies[COOKIE]
        client.cookies.clear()
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "ada@example.com"

    def test_a_garbage_token_is_401(self, client: TestClient):
        response = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
        )
        assert response.status_code == 401

    def test_an_expired_token_is_401(self, client: TestClient):
        me = register(client, "ada@example.com").json()
        # Mint a token that expired before the frozen "now", signed with the
        # same secret the app verifies against.
        secret = resolve_auth_secret(settings)
        stale = create_access_token(
            subject=me["id"],
            secret=secret,
            issued_at=FROZEN_NOW - timedelta(minutes=settings.access_token_ttl_minutes + 10),
            ttl_minutes=settings.access_token_ttl_minutes,
        )
        client.cookies.clear()
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {stale}"}
        )
        assert response.status_code == 401

    def test_a_token_for_a_deleted_account_is_401(
        self, client: TestClient, db: Session
    ):
        me = register(client, "ada@example.com").json()
        token = client.cookies[COOKIE]
        # "Delete all data" keeps the account (Phase 18), so to test a token
        # whose subject is truly gone we remove the user row directly.
        db.delete(db.get(User, me["id"]))
        db.commit()
        client.cookies.clear()
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_logout_clears_the_session(self, client: TestClient):
        register(client, "ada@example.com")
        assert client.get("/api/auth/me").status_code == 200

        logout = client.post("/api/auth/logout")
        assert logout.status_code == 204
        client.cookies.clear()  # the browser would drop the expired cookie
        assert client.get("/api/auth/me").status_code == 401


class TestPasswordHashing:
    def test_hash_is_not_the_plaintext_and_verifies(self):
        digest = hash_password("correct horse battery staple")
        assert digest != "correct horse battery staple"
        assert digest.startswith("$argon2id$")  # Argon2id, per ADR-011
        assert verify_password("correct horse battery staple", digest) is True
        assert verify_password("wrong", digest) is False

    def test_verify_against_a_null_hash_is_false(self):
        # The demo/legacy rows have no password; nothing authenticates them.
        assert verify_password("anything", None) is False
