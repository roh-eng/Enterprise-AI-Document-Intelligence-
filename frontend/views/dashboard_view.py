"""
User dashboard view.

Shows the authenticated user's profile and their **upload history**: every
uploaded document with metadata, a text preview (fetched on demand), and a
delete action. This is the landing page after login.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.api_client import APIClient


def _format_dt(value: str) -> str:
    """Render an ISO timestamp as a friendly string (best-effort)."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return value


def _format_size(num_bytes: int) -> str:
    """Human-readable file size."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} MB"


def render_dashboard(client: APIClient, token: str, user: dict) -> None:
    """Render profile + upload history."""
    st.markdown(f"## 👋 Welcome back, **{user.get('username', 'user')}**")
    st.caption("Your AI Document Intelligence dashboard.")

    ok, documents = client.list_documents(token)
    doc_count = len(documents) if ok and isinstance(documents, list) else 0
    total_chars = sum(d["num_chars"] for d in documents) if doc_count else 0

    # --- Summary metrics -------------------------------------------------
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents", doc_count)
    c2.metric("Total characters", f"{total_chars:,}")
    c3.metric("Account", "Active" if user.get("is_active") else "Inactive")

    with st.container(border=True):
        st.markdown("#### Profile")
        st.write(f"**Username:** {user.get('username', '—')}")
        st.write(f"**Email:** {user.get('email', '—')}")
        st.write(f"**Joined:** {_format_dt(user.get('created_at', ''))}")

    st.divider()

    # --- Upload history --------------------------------------------------
    st.markdown("#### 📄 Upload history")
    if not ok:
        st.error(f"Could not load documents: {documents}")
        return
    if not documents:
        st.info("No documents yet. Head to the **Upload** page to add your first file.")
        return

    for doc in documents:
        with st.container(border=True):
            info_col, action_col = st.columns([4, 1])
            with info_col:
                st.markdown(f"**{doc['filename']}**  ·  `{doc['file_ext']}`")
                st.caption(
                    f"ID {doc['id']} · {_format_size(doc['file_size'])} · "
                    f"{doc['num_chars']:,} chars · {doc['status']} · "
                    f"{_format_dt(doc['created_at'])}"
                )
            with action_col:
                # A two-click delete guard avoids accidental data loss.
                if st.button("🗑️ Delete", key=f"del_{doc['id']}", use_container_width=True):
                    del_ok, payload = client.delete_document(token, doc["id"])
                    if del_ok:
                        st.success(f"Deleted '{doc['filename']}'.")
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {payload}")

            # Text preview, fetched only when the expander is opened.
            with st.expander("Preview extracted text"):
                detail_ok, detail = client.get_document(token, doc["id"])
                if detail_ok:
                    text = detail.get("extracted_text", "")
                    preview = text[:2000] + ("…" if len(text) > 2000 else "")
                    st.text(preview or "(no text extracted)")
                else:
                    st.error(f"Could not load text: {detail}")
