"""
Document chat view (RAG).

Pick a document, then chat with it. Each answer shows its source citations
(the retrieved chunks). Conversation history is loaded from the backend and can
be cleared.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient


def _render_message(msg: dict) -> None:
    """Render one chat message with optional source citations."""
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.markdown(msg["content"])
        sources = msg.get("sources") or []
        if sources:
            with st.expander(f"📎 {len(sources)} source passage(s)"):
                for i, s in enumerate(sources, 1):
                    st.markdown(f"**[{i}]** _(score {s['score']:.3f})_")
                    st.caption(s["text"])


def render_chat(client: APIClient, token: str) -> None:
    """Render the RAG chat page."""
    st.markdown("## 💬 Chat with your documents")
    st.caption("Ask questions; answers are grounded in retrieved passages with citations.")

    ok, docs = client.list_documents(token)
    if not ok or not docs:
        st.info("No stored documents. Upload one first on the **Upload** page.")
        return

    options = {f"#{d['id']} · {d['filename']}": d["id"] for d in docs}
    choice = st.selectbox("Select a document", list(options.keys()))
    document_id = options[choice]

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 (Re)index document", use_container_width=True):
            with st.spinner("Chunking and embedding…"):
                ok, result = client.rag_index(token, document_id)
            if ok:
                st.success(f"Indexed into {result['num_chunks']} chunks ({result['backend']}).")
            else:
                st.error(f"Indexing failed: {result}")
    with col2:
        if st.button("🗑️ Clear conversation", use_container_width=True):
            client.rag_clear_history(token, document_id)
            st.rerun()

    st.divider()

    # Render existing history.
    ok, history = client.rag_history(token, document_id)
    if ok:
        for msg in history:
            _render_message(msg)

    # Chat input.
    question = st.chat_input("Ask a question about this document…")
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving & answering…"):
                ok, result = client.rag_chat(token, document_id, question)
            if ok:
                st.markdown(result["answer"])
                badge = "🟢 Gemini" if result["source"] == "gemini" else "🟡 Offline (extractive)"
                st.caption(f"{badge} · model `{result['model_used']}`")
                if result["sources"]:
                    with st.expander(f"📎 {len(result['sources'])} source passage(s)"):
                        for i, s in enumerate(result["sources"], 1):
                            st.markdown(f"**[{i}]** _(score {s['score']:.3f})_")
                            st.caption(s["text"])
            else:
                st.error(f"Chat failed: {result}")
