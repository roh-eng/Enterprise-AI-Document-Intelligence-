"""
Tests for the Week-2 document upload system: PDF/DOCX/TXT upload, text
extraction & cleaning, history, detail, deletion, and error handling.
"""

from __future__ import annotations

import io

import pytest


def _auth_headers(client, username="docuser", email="doc@example.com", password="S3curePass!"):
    """Register + login, returning Authorization headers."""
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/auth/login", data={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _docx_bytes(text: str) -> bytes:
    """Build a minimal in-memory DOCX containing one paragraph."""
    from docx import Document as DocxDocument

    doc = DocxDocument()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_upload_txt(client):
    headers = _auth_headers(client)
    files = {"file": ("note.txt", b"Hello   world\n\n\n\nfrom   a   test.", "text/plain")}
    resp = client.post("/documents/upload", headers=headers, files=files)
    assert resp.status_code == 201
    body = resp.json()
    assert body["file_ext"] == ".txt"
    assert body["status"] == "processed"
    # Cleaning collapsed the runs of whitespace/newlines.
    assert body["num_chars"] < len("Hello   world\n\n\n\nfrom   a   test.")


def test_upload_docx(client):
    headers = _auth_headers(client)
    files = {
        "file": (
            "report.docx",
            _docx_bytes("Quarterly report body text."),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    resp = client.post("/documents/upload", headers=headers, files=files)
    assert resp.status_code == 201
    assert resp.json()["file_ext"] == ".docx"


def test_unsupported_type_rejected(client):
    headers = _auth_headers(client)
    files = {"file": ("image.png", b"\x89PNG\r\n", "image/png")}
    resp = client.post("/documents/upload", headers=headers, files=files)
    assert resp.status_code == 415


def test_empty_file_rejected(client):
    headers = _auth_headers(client)
    files = {"file": ("empty.txt", b"", "text/plain")}
    resp = client.post("/documents/upload", headers=headers, files=files)
    assert resp.status_code == 400


def test_history_lists_newest_first(client):
    headers = _auth_headers(client)
    for i in range(2):
        client.post(
            "/documents/upload", headers=headers,
            files={"file": (f"f{i}.txt", f"content {i}".encode(), "text/plain")},
        )
    resp = client.get("/documents", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_detail_returns_cleaned_text(client):
    headers = _auth_headers(client)
    up = client.post(
        "/documents/upload", headers=headers,
        files={"file": ("d.txt", b"Detailed body text.", "text/plain")},
    )
    doc_id = up.json()["id"]
    detail = client.get(f"/documents/{doc_id}", headers=headers)
    assert detail.status_code == 200
    assert "Detailed body text." in detail.json()["extracted_text"]


def test_delete_document(client):
    headers = _auth_headers(client)
    up = client.post(
        "/documents/upload", headers=headers,
        files={"file": ("gone.txt", b"to be deleted", "text/plain")},
    )
    doc_id = up.json()["id"]

    delete = client.delete(f"/documents/{doc_id}", headers=headers)
    assert delete.status_code == 204
    # Now gone.
    assert client.get(f"/documents/{doc_id}", headers=headers).status_code == 404


def test_cannot_access_other_users_document(client):
    # User A uploads.
    headers_a = _auth_headers(client, "alice", "alice@example.com")
    doc_id = client.post(
        "/documents/upload", headers=headers_a,
        files={"file": ("a.txt", b"alice secret", "text/plain")},
    ).json()["id"]

    # User B must not see or delete it.
    headers_b = _auth_headers(client, "bob", "bob@example.com")
    assert client.get(f"/documents/{doc_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=headers_b).status_code == 404
