"""
Documents view — manage uploaded documents.

Lists the user's documents (newest first) with metadata, the classification
badge, a text preview (fetched on demand), and a delete action.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.api_client import APIClient


def _fmt_dt(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return value


def _fmt_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} MB"


def render_documents(client: APIClient, token: str, user: dict) -> None:
    """Render the document management list."""
    st.markdown("## 📁 My Documents")
    st.caption("Manage your uploaded documents.")

    ok, documents = client.list_documents(token)
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
                category = doc.get("category")
                badge = ""
                if category:
                    conf = doc.get("category_confidence") or 0.0
                    badge = f"  ·  🏷️ **{category}** ({conf * 100:.0f}%)"
                st.markdown(f"**{doc['filename']}**  ·  `{doc['file_ext']}`{badge}")
                st.caption(
                    f"ID {doc['id']} · {_fmt_size(doc['file_size'])} · "
                    f"{doc['num_chars']:,} chars · {doc['status']} · "
                    f"{_fmt_dt(doc['created_at'])}"
                )
            with action_col:
                if st.button("🗑️ Delete", key=f"del_{doc['id']}", use_container_width=True):
                    del_ok, payload = client.delete_document(token, doc["id"])
                    if del_ok:
                        st.success(f"Deleted '{doc['filename']}'.")
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {payload}")

            with st.expander("Preview extracted text"):
                detail_ok, detail = client.get_document(token, doc["id"])
                if detail_ok:
                    text = detail.get("extracted_text", "")
                    preview = text[:2000] + ("…" if len(text) > 2000 else "")
                    st.text(preview or "(no text extracted)")
                else:
                    st.error(f"Could not load text: {detail}")
