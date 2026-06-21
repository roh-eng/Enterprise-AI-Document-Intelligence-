"""
Tests for the Week-6 RAG system: indexing, retrieval, grounded chat with
citations, and conversation history.

With sentence-transformers + faiss installed these exercise the real FAISS path;
Gemini is not configured, so answers come from the extractive fallback (which is
still grounded and cites its source).
"""

from __future__ import annotations


def _auth_headers(client, username="raguser", email="rag@example.com", password="S3curePass!"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/auth/login", data={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


# A document with two clearly distinct topics, so retrieval can be checked.
_DOC = (
    "The Apollo program was a NASA spaceflight effort that landed humans on the "
    "Moon between 1969 and 1972. Neil Armstrong was the first person to walk on "
    "the lunar surface. "
    "Separately, the quarterly financial report showed revenue of five million "
    "dollars, driven by strong enterprise software subscriptions and renewals. "
    "Operating costs rose due to increased cloud infrastructure spending."
)


def _upload(client, headers, name="doc.txt", text=_DOC):
    return client.post("/documents/upload", headers=headers, files={"file": (name, text.encode(), "text/plain")})


def test_index_document(client):
    headers = _auth_headers(client)
    doc_id = _upload(client, headers).json()["id"]
    resp = client.post(f"/documents/{doc_id}/index", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["num_chunks"] >= 1
    assert body["backend"] in {"faiss", "brute-force"}


def test_chat_returns_grounded_answer_with_sources(client):
    headers = _auth_headers(client)
    doc_id = _upload(client, headers).json()["id"]
    resp = client.post(f"/documents/{doc_id}/chat", headers=headers,
                       json={"question": "Who was the first person to walk on the Moon?"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["sources"]) >= 1
    # The answer should be grounded in the Moon passage, not the finance one.
    assert "Armstrong" in body["answer"] or "Armstrong" in body["sources"][0]["text"]


def test_retrieval_is_relevant(client):
    headers = _auth_headers(client)
    doc_id = _upload(client, headers).json()["id"]
    resp = client.post(f"/documents/{doc_id}/chat", headers=headers,
                       json={"question": "What was the quarterly revenue?"})
    top_source = resp.json()["sources"][0]["text"].lower()
    # The most relevant chunk for a revenue question should mention money/revenue.
    assert "revenue" in top_source or "million" in top_source


def test_chat_auto_indexes(client):
    headers = _auth_headers(client)
    doc_id = _upload(client, headers).json()["id"]
    # No explicit /index call — chat should index on first use.
    resp = client.post(f"/documents/{doc_id}/chat", headers=headers, json={"question": "Apollo?"})
    assert resp.status_code == 200


def test_conversation_history(client):
    headers = _auth_headers(client)
    doc_id = _upload(client, headers).json()["id"]
    client.post(f"/documents/{doc_id}/chat", headers=headers, json={"question": "Who walked on the Moon?"})
    client.post(f"/documents/{doc_id}/chat", headers=headers, json={"question": "What was the revenue?"})

    hist = client.get(f"/documents/{doc_id}/chat/history", headers=headers).json()
    # 2 questions -> 4 messages (user + assistant each).
    assert len(hist) == 4
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"

    # Clear it.
    assert client.delete(f"/documents/{doc_id}/chat/history", headers=headers).status_code == 204
    assert client.get(f"/documents/{doc_id}/chat/history", headers=headers).json() == []


def test_chat_requires_auth(client):
    assert client.post("/documents/1/chat", json={"question": "hi"}).status_code == 401


def test_cannot_chat_other_users_document(client):
    headers_a = _auth_headers(client, "alice", "alice@example.com")
    doc_id = _upload(client, headers_a).json()["id"]
    headers_b = _auth_headers(client, "bob", "bob@example.com")
    resp = client.post(f"/documents/{doc_id}/chat", headers=headers_b, json={"question": "hi"})
    assert resp.status_code == 404
