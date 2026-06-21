"""
Thin HTTP client wrapping the FastAPI backend.

The frontend never imports backend code directly — it talks to the API over
HTTP, exactly as a real decoupled client would. Every method returns a
`(success: bool, payload)` tuple so the UI can render errors gracefully instead
of crashing on exceptions.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Tuple

import requests

logger = logging.getLogger(__name__)

# Where the backend lives. Overridable via env so the same code works in Docker.
DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Network timeout (connect, read) in seconds.
_TIMEOUT = (5, 30)

Result = Tuple[bool, Any]


class APIClient:
    """Stateless client; the JWT is passed per-call from Streamlit session state."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    # -- internal helpers --------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _auth_header(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _handle(response: requests.Response) -> Result:
        """Convert an HTTP response into a (success, payload) tuple."""
        if response.ok:
            try:
                return True, response.json()
            except ValueError:
                return True, response.text
        # Pull FastAPI's `detail` message when present for a friendly error.
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        return False, detail

    def _safe_request(self, method: str, path: str, **kwargs) -> Result:
        """Run a request, turning connection problems into a clean error tuple."""
        try:
            response = requests.request(method, self._url(path), timeout=_TIMEOUT, **kwargs)
            return self._handle(response)
        except requests.ConnectionError:
            logger.error("Backend unreachable at %s", self.base_url)
            return False, f"Cannot reach the backend at {self.base_url}. Is it running?"
        except requests.Timeout:
            return False, "The request to the backend timed out."
        except requests.RequestException as exc:  # pragma: no cover
            logger.exception("Unexpected request error")
            return False, f"Request failed: {exc}"

    # -- health ------------------------------------------------------------
    def health(self) -> Result:
        return self._safe_request("GET", "/health")

    # -- auth --------------------------------------------------------------
    def register(self, username: str, email: str, password: str) -> Result:
        return self._safe_request(
            "POST", "/auth/register",
            json={"username": username, "email": email, "password": password},
        )

    def login(self, username: str, password: str) -> Result:
        # OAuth2 password flow expects form-encoded data, not JSON.
        return self._safe_request(
            "POST", "/auth/login",
            data={"username": username, "password": password},
        )

    def get_me(self, token: str) -> Result:
        return self._safe_request("GET", "/auth/me", headers=self._auth_header(token))

    # -- documents ---------------------------------------------------------
    def list_documents(self, token: str) -> Result:
        return self._safe_request(
            "GET", "/documents", headers=self._auth_header(token)
        )

    def get_document(self, token: str, document_id: int) -> Result:
        return self._safe_request(
            "GET", f"/documents/{document_id}", headers=self._auth_header(token)
        )

    def delete_document(self, token: str, document_id: int) -> Result:
        # 204 No Content returns an empty body; _handle still reports success.
        return self._safe_request(
            "DELETE", f"/documents/{document_id}", headers=self._auth_header(token)
        )

    def upload_document(
        self, token: str, filename: str, data: bytes, content_type: str
    ) -> Result:
        files = {"file": (filename, data, content_type)}
        return self._safe_request(
            "POST", "/documents/upload",
            headers=self._auth_header(token), files=files,
        )

    # -- machine learning --------------------------------------------------
    def classify_text(self, token: str, text: str) -> Result:
        return self._safe_request(
            "POST", "/ml/classify",
            headers=self._auth_header(token), json={"text": text},
        )

    def classify_document(self, token: str, document_id: int) -> Result:
        return self._safe_request(
            "POST", f"/documents/{document_id}/classify",
            headers=self._auth_header(token),
        )

    def model_info(self, token: str) -> Result:
        return self._safe_request(
            "GET", "/ml/model-info", headers=self._auth_header(token)
        )

    # -- nlp ---------------------------------------------------------------
    def nlp_analyze_text(self, token: str, text: str) -> Result:
        return self._safe_request(
            "POST", "/nlp/analyze", headers=self._auth_header(token), json={"text": text}
        )

    def nlp_analyze_document(self, token: str, document_id: int) -> Result:
        return self._safe_request(
            "POST", f"/documents/{document_id}/analyze", headers=self._auth_header(token)
        )

    def nlp_text_similarity(self, token: str, text_a: str, text_b: str) -> Result:
        return self._safe_request(
            "POST", "/nlp/similarity",
            headers=self._auth_header(token),
            json={"text_a": text_a, "text_b": text_b},
        )

    def nlp_similar_documents(self, token: str, document_id: int) -> Result:
        return self._safe_request(
            "GET", f"/documents/{document_id}/similar", headers=self._auth_header(token)
        )
