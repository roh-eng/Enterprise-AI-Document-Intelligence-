"""
Tests for the Week-4 NLP module: analysis (tokens/entities/keywords/sentiment),
text similarity, and document similarity.

Assertions are structural and bound-based (not exact model outputs) so the suite
passes whether the real models (spaCy/NLTK/sentence-transformers) or the offline
fallbacks are active.
"""

from __future__ import annotations


def _auth_headers(client, username="nlpuser", email="nlp@example.com", password="S3curePass!"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/auth/login", data={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


_SAMPLE = (
    "Dr. Alice Smith joined Acme Corporation in 2021. The company reported "
    "excellent revenue growth and a fantastic outlook for the next year."
)


def test_analyze_text_structure(client):
    headers = _auth_headers(client)
    resp = client.post("/nlp/analyze", headers=headers, json={"text": _SAMPLE})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stats"]["num_tokens"] > 0
    assert body["stats"]["num_sentences"] >= 2
    assert isinstance(body["entities"], list)
    assert len(body["keywords"]) > 0
    assert body["sentiment"]["label"] in {"Positive", "Negative", "Neutral"}
    assert -1.0 <= body["sentiment"]["score"] <= 1.0
    # Engine report tells us which backend served each technique.
    assert set(body["engines"]) == {"tokenizer", "lemmatizer", "ner", "sentiment"}


def test_positive_sentiment_detected(client):
    headers = _auth_headers(client)
    resp = client.post(
        "/nlp/analyze", headers=headers,
        json={"text": "This is excellent, wonderful and fantastic. I love it."},
    )
    assert resp.json()["sentiment"]["label"] == "Positive"


def test_analyze_requires_auth(client):
    assert client.post("/nlp/analyze", json={"text": "hi there"}).status_code == 401


def test_identical_text_similarity_is_high(client):
    headers = _auth_headers(client)
    resp = client.post(
        "/nlp/similarity", headers=headers,
        json={"text_a": _SAMPLE, "text_b": _SAMPLE},
    )
    assert resp.status_code == 200
    assert resp.json()["similarity"] > 0.99


def test_different_text_similarity_is_lower(client):
    headers = _auth_headers(client)
    same = client.post(
        "/nlp/similarity", headers=headers,
        json={"text_a": _SAMPLE, "text_b": _SAMPLE},
    ).json()["similarity"]
    diff = client.post(
        "/nlp/similarity", headers=headers,
        json={"text_a": "The cat sat quietly on the warm windowsill.",
              "text_b": "Quarterly invoice totals and tax payment terms are due."},
    ).json()["similarity"]
    assert diff < same


def test_document_similarity_ranks_related_doc_first(client):
    headers = _auth_headers(client)
    # Two finance-ish docs and one unrelated doc.
    client.post("/documents/upload", headers=headers,
                files={"file": ("a.txt", b"Invoice total amount due tax payment terms net thirty days.", "text/plain")})
    target = client.post("/documents/upload", headers=headers,
                         files={"file": ("b.txt", b"Invoice number payment amount due tax subtotal balance.", "text/plain")})
    client.post("/documents/upload", headers=headers,
                files={"file": ("c.txt", b"The patient presented with fever and cough symptoms.", "text/plain")})

    resp = client.get(f"/documents/{target.json()['id']}/similar", headers=headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    # The finance doc (a.txt) should rank above the medical doc (c.txt).
    assert results[0]["filename"] == "a.txt"
