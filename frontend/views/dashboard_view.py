"""
User dashboard view.

Shows the authenticated user's profile and a live list of their uploaded
documents (fetched from the backend). This is the landing page after login.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.api_client import APIClient


def _format_dt(value: str) -> str:
    """Render an ISO timestamp as a friendly local string (best-effort)."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return value


def render_dashboard(client: APIClient, token: str, user: dict) -> None:
    """Render profile + documents overview."""
    st.markdown(f"## 👋 Welcome back, **{user.get('username', 'user')}**")
    st.caption("Your AI Document Intelligence dashboard.")

    # --- Profile cards ---------------------------------------------------
    ok, documents = client.list_documents(token)
    doc_count = len(documents) if ok and isinstance(documents, list) else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Username", user.get("username", "—"))
    c2.metric("Documents", doc_count)
    c3.metric("Account status", "Active" if user.get("is_active") else "Inactive")

    with st.container(border=True):
        st.markdown("#### Profile")
        st.write(f"**Email:** {user.get('email', '—')}")
        st.write(f"**User ID:** {user.get('id', '—')}")
        st.write(f"**Joined:** {_format_dt(user.get('created_at', ''))}")

    st.divider()

    # --- Documents table -------------------------------------------------
    st.markdown("#### 📄 Your documents")
    if not ok:
        st.error(f"Could not load documents: {documents}")
        return
    if not documents:
        st.info("No documents yet. Head to the **Upload** page to add your first file.")
        return

    table_rows = [
        {
            "ID": d["id"],
            "Filename": d["filename"],
            "Type": d["content_type"],
            "Characters": d["num_chars"],
            "Uploaded": _format_dt(d["created_at"]),
        }
        for d in documents
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
