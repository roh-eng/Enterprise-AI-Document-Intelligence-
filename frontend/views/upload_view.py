"""
Document upload view.

Lets the authenticated user upload a PDF or TXT file. The file bytes are POSTed
to the backend, which extracts the text and persists the document against the
user's account.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient


def render_upload(client: APIClient, token: str) -> None:
    """Render the file upload form and handle submission."""
    st.markdown("## 📤 Upload a document")
    st.caption("Upload a PDF, DOCX, or TXT file. We'll extract & clean its text and store it securely.")

    uploaded = st.file_uploader(
        "Choose a file", type=["pdf", "docx", "txt"], accept_multiple_files=False
    )

    if uploaded is not None:
        # Show a small preview card before the user commits to uploading.
        size_kb = uploaded.size / 1024
        with st.container(border=True):
            st.write(f"**Selected:** {uploaded.name}")
            st.write(f"**Type:** {uploaded.type or 'unknown'} · **Size:** {size_kb:,.1f} KB")

        if st.button("Upload to backend", type="primary"):
            with st.spinner("Uploading and extracting text…"):
                data = uploaded.getvalue()
                ok, payload = client.upload_document(
                    token,
                    filename=uploaded.name,
                    data=data,
                    content_type=uploaded.type or "application/octet-stream",
                )
            if ok:
                st.success(f"✅ Uploaded **{payload['filename']}** successfully!")
                c1, c2 = st.columns(2)
                c1.metric("Document ID", payload["id"])
                c2.metric("Characters extracted", payload["num_chars"])
                st.info("View it any time on your **Dashboard**.")
            else:
                st.error(f"Upload failed: {payload}")
