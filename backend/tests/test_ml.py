"""
Tests for the Week-3 ML classification module.

A session-scoped fixture trains the model once (if no artifact exists), so these
tests exercise the real train -> save -> load -> predict pipeline end-to-end.
"""

from __future__ import annotations

import pytest

from app.ml import classifier, train


@pytest.fixture(scope="session", autouse=True)
def trained_model():
    """Ensure a model artifact exists before the ML tests run."""
    if not train.MODEL_PATH.exists():
        train.train()
    classifier._load_bundle.cache_clear()  # pick up the freshly trained model
    yield


def _auth_headers(client, username="mluser", email="ml@example.com", password="S3curePass!"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/auth/login", data={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


# Representative text per category (close to the training distribution).
_SAMPLES = {
    "Invoice": "Invoice number 4471 total amount due payable within thirty days tax subtotal grand total",
    "Resume": "Experienced software engineer skilled in python with leadership and project management work experience education",
    "Legal": "This agreement between the parties plaintiff defendant governed by the laws jurisdiction clause liability",
    "Medical": "The patient presented with symptoms fever cough diagnosis prescribed medication treatment clinical examination",
    "Research": "This study investigates the proposed method experimental results methodology hypothesis benchmark datasets findings",
}


def test_model_info(client):
    headers = _auth_headers(client)
    resp = client.get("/ml/model-info", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_name"] in {"LogisticRegression", "RandomForest", "XGBoost"}
    assert set(body["categories"]) == {"Resume", "Invoice", "Legal", "Medical", "Research"}


@pytest.mark.parametrize("expected,text", list(_SAMPLES.items()))
def test_classify_text_predicts_expected_category(client, expected, text):
    headers = _auth_headers(client)
    resp = client.post("/ml/classify", headers=headers, json={"text": text})
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == expected
    assert 0.0 <= body["confidence"] <= 1.0
    # Probabilities form a distribution over all five classes.
    assert abs(sum(body["probabilities"].values()) - 1.0) < 1e-3


def test_classify_requires_auth(client):
    resp = client.post("/ml/classify", json={"text": "anything"})
    assert resp.status_code == 401


def test_classify_document_persists_category(client):
    headers = _auth_headers(client)
    up = client.post(
        "/documents/upload", headers=headers,
        files={"file": ("inv.txt", _SAMPLES["Invoice"].encode(), "text/plain")},
    )
    doc_id = up.json()["id"]

    clf = client.post(f"/documents/{doc_id}/classify", headers=headers)
    assert clf.status_code == 200
    assert clf.json()["category"] == "Invoice"

    # The category is now persisted on the document.
    detail = client.get(f"/documents/{doc_id}", headers=headers)
    assert detail.json()["category"] == "Invoice"
    assert detail.json()["category_confidence"] is not None
