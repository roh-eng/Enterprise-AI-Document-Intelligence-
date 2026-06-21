"""
End-to-end tests for the authentication and document flows.

These exercise the full stack (routes -> services -> ORM) against an in-memory
database, validating the contract a frontend depends on.
"""

from __future__ import annotations


def _register(client, username="jane", email="jane@example.com", password="S3curePass!"):
    return client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )


def _login(client, username="jane", password="S3curePass!"):
    return client.post(
        "/auth/login", data={"username": username, "password": password}
    )


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_returns_user_without_password(client):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "jane"
    assert "password" not in body and "hashed_password" not in body


def test_duplicate_registration_conflicts(client):
    _register(client)
    resp = _register(client)  # same username/email again
    assert resp.status_code == 409


def test_login_and_access_protected_me(client):
    _register(client)
    login = _login(client)
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "jane@example.com"


def test_login_with_bad_password_is_unauthorized(client):
    _register(client)
    resp = _login(client, password="wrong-password")
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/documents")
    assert resp.status_code == 401


def test_upload_and_list_documents(client):
    _register(client)
    token = _login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("note.txt", b"Hello world from a test document.", "text/plain")}
    up = client.post("/documents/upload", headers=headers, files=files)
    assert up.status_code == 201
    assert up.json()["filename"] == "note.txt"
    assert up.json()["num_chars"] > 0

    listing = client.get("/documents", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
