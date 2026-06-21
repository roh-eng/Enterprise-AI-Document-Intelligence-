"""
Tests for the Week-5 Generative AI module.

No Gemini key is configured in the test environment, so these exercise the
offline fallback path (source == "fallback") and the structure of each task's
output, plus caching and document persistence.
"""

from __future__ import annotations


def _auth_headers(client, username="genaiuser", email="gen@example.com", password="S3curePass!"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/auth/login", data={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


_DOC = (
    "Project Atlas kickoff. The team must submit the final budget by 12/05/2026. "
    "Please review the vendor contract before the deadline. The quarterly report "
    "showed excellent growth in the enterprise segment. We need to schedule a "
    "follow-up meeting within 2 weeks to finalize the roadmap and approve hiring."
)


def _gen(client, headers, task, text=_DOC):
    return client.post("/genai/generate", headers=headers, json={"task": task, "text": text})


def test_status_reports_disabled_without_key(client):
    headers = _auth_headers(client)
    resp = client.get("/genai/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["gemini_enabled"] is False


def test_summary_uses_fallback(client):
    headers = _auth_headers(client)
    resp = _gen(client, headers, "summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert body["summary"] and len(body["summary"]) > 0


def test_faq_structure(client):
    headers = _auth_headers(client)
    body = _gen(client, headers, "faq").json()
    assert isinstance(body["faq"], list) and len(body["faq"]) >= 1
    assert {"question", "answer"} <= set(body["faq"][0].keys())


def test_interview_questions(client):
    headers = _auth_headers(client)
    body = _gen(client, headers, "interview_questions").json()
    assert isinstance(body["interview_questions"], list)
    assert len(body["interview_questions"]) == 6


def test_action_items_detected(client):
    headers = _auth_headers(client)
    body = _gen(client, headers, "action_items").json()
    # The doc has "must submit", "please review", "need to schedule".
    assert len(body["action_items"]) >= 2


def test_deadlines_extracted(client):
    headers = _auth_headers(client)
    body = _gen(client, headers, "deadlines").json()
    dues = [d["due"] for d in body["deadlines"]]
    assert any("12/05/2026" in d for d in dues)
    assert any("within 2 weeks" in d.lower() for d in dues)


def test_explain(client):
    headers = _auth_headers(client)
    body = _gen(client, headers, "explain").json()
    assert body["explanation"] and "words" in body["explanation"]


def test_requires_exactly_one_input(client):
    headers = _auth_headers(client)
    # Neither text nor document_id -> validation error.
    resp = client.post("/genai/generate", headers=headers, json={"task": "summary"})
    assert resp.status_code == 422


def test_requires_auth(client):
    assert client.post("/genai/generate", json={"task": "summary", "text": "x"}).status_code == 401


def test_summary_persisted_and_cached_for_document(client):
    headers = _auth_headers(client)
    up = client.post(
        "/documents/upload", headers=headers,
        files={"file": ("d.txt", _DOC.encode(), "text/plain")},
    )
    doc_id = up.json()["id"]

    first = client.post(
        "/genai/generate", headers=headers, json={"task": "summary", "document_id": doc_id}
    ).json()
    assert first["cached"] is False

    # Second identical request should hit the cache.
    second = client.post(
        "/genai/generate", headers=headers, json={"task": "summary", "document_id": doc_id}
    ).json()
    assert second["cached"] is True
