"""
Unit tests — exercise individual functions in isolation (no app, no database).

These complement the API/integration tests in the other test_*.py files: they
are fast, deterministic, and pinpoint failures to a single function.
"""

from __future__ import annotations

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.genai import fallback
from app.ml.preprocess import preprocess
from app.rag import chunking
from app.services.text_cleaning import clean_text


# --- Text cleaning ---------------------------------------------------------
def test_clean_text_collapses_whitespace_and_newlines():
    raw = "Hello   world\r\n\n\n\nfoo\tbar"
    cleaned = clean_text(raw)
    assert "   " not in cleaned          # multiple spaces collapsed
    assert "\n\n\n" not in cleaned       # excess blank lines collapsed
    assert "\r" not in cleaned           # CRLF normalised


def test_clean_text_rejoins_hyphenated_linebreak():
    assert "example" in clean_text("exam-\nple")


def test_clean_text_empty():
    assert clean_text("") == ""


# --- Preprocessing ---------------------------------------------------------
def test_preprocess_lowercases_and_drops_stopwords():
    out = preprocess("The QUICK brown Fox and the dog")
    assert "the" not in out.split() and "and" not in out.split()
    assert "quick" in out and "brown" in out


# --- Security --------------------------------------------------------------
def test_password_hash_roundtrip():
    h = hash_password("S3curePass!")
    assert h != "S3curePass!"            # never stored in plaintext
    assert verify_password("S3curePass!", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    token = create_access_token(subject=7, extra_claims={"username": "ada"})
    claims = decode_access_token(token)
    assert claims["sub"] == "7" and claims["username"] == "ada"


def test_jwt_rejects_garbage():
    assert decode_access_token("not.a.jwt") is None


# --- Chunking --------------------------------------------------------------
def test_chunking_produces_overlapping_chunks():
    text = " ".join(f"word{i}" for i in range(400))  # long enough to split
    chunks = chunking.split_text(text, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


def test_chunking_empty_returns_empty():
    assert chunking.split_text("") == []


# --- GenAI fallback extractors --------------------------------------------
def test_fallback_deadlines_extraction():
    text = "The report is due by 12/05/2026. Submit feedback within 2 weeks."
    dues = [d["due"] for d in fallback.deadlines(text)]
    assert any("12/05/2026" in d for d in dues)
    assert any("within 2 weeks" in d.lower() for d in dues)


def test_fallback_action_items_detection():
    text = "Please review the draft. The team must submit the form. Nothing here."
    items = fallback.action_items(text)
    assert len(items) >= 2
