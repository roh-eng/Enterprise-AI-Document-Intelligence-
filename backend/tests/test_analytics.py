"""
Tests for the Week-7 analytics dashboard endpoints.
"""

from __future__ import annotations


def _register_login(client, username, email="x@example.com", password="S3curePass!"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/auth/login", data={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_first_user_is_admin(client):
    client.post("/auth/register", json={"username": "owner", "email": "o@x.com", "password": "S3curePass!"})
    token = client.post("/auth/login", data={"username": "owner", "password": "S3curePass!"}).json()[
        "access_token"
    ]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["is_admin"] is True


def test_second_user_is_not_admin(client):
    _register_login(client, "owner", "o@x.com")  # first = admin
    headers = _register_login(client, "member", "m@x.com")  # second = not admin
    assert client.get("/auth/me", headers=headers).json()["is_admin"] is False
    assert client.get("/analytics/admin", headers=headers).status_code == 403


def test_user_analytics_aggregates(client):
    headers = _register_login(client, "owner", "o@x.com")
    client.post("/documents/upload", headers=headers,
                files={"file": ("a.txt", b"This is an excellent and wonderful report.", "text/plain")})
    client.post("/documents/upload", headers=headers,
                files={"file": ("b.txt", b"Invoice total amount due tax payment terms.", "text/plain")})

    body = client.get("/analytics/me", headers=headers).json()
    assert body["total_documents"] == 2
    assert body["total_chars"] > 0
    assert body["file_type_distribution"].get(".txt") == 2
    # No classification run yet -> both documents are "Unclassified".
    assert body["category_distribution"].get("Unclassified") == 2
    # Sentiment computed on the fly -> distribution sums to the document count.
    assert sum(body["sentiment_distribution"].values()) == 2
    assert len(body["recent_uploads"]) == 2


def test_search_history_recorded(client):
    headers = _register_login(client, "owner", "o@x.com")
    doc_id = client.post("/documents/upload", headers=headers,
                         files={"file": ("d.txt", b"Apollo landed on the Moon in 1969.", "text/plain")}).json()["id"]
    client.post(f"/documents/{doc_id}/chat", headers=headers, json={"question": "When did Apollo land?"})

    body = client.get("/analytics/me", headers=headers).json()
    assert body["total_searches"] == 1
    assert body["recent_searches"][0]["question"] == "When did Apollo land?"


def test_admin_analytics(client):
    headers = _register_login(client, "owner", "o@x.com")  # admin
    client.post("/documents/upload", headers=headers,
                files={"file": ("a.txt", b"hello world content here", "text/plain")})
    _register_login(client, "member", "m@x.com")  # a second user

    body = client.get("/analytics/admin", headers=headers).json()
    assert body["total_users"] == 2
    assert body["total_documents"] == 1
    assert any(u["username"] == "owner" for u in body["documents_per_user"])


def test_analytics_requires_auth(client):
    assert client.get("/analytics/me").status_code == 401
