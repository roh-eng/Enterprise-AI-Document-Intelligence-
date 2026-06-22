"""
NLP dashboard view.

Three tabs:
  * Analyze text   — tokens, entities, keywords, sentiment for pasted text.
  * Analyze document — same, for a stored document.
  * Similarity     — text-vs-text and document-vs-corpus cosine similarity.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient


def _render_analysis(result: dict) -> None:
    """Render a full NLP analysis result."""
    stats = result["stats"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tokens", stats["num_tokens"])
    c2.metric("Content tokens", stats["num_content_tokens"])
    c3.metric("Unique", stats["num_unique_tokens"])
    c4.metric("Sentences", stats["num_sentences"])

    sent = result["sentiment"]
    s1, s2 = st.columns(2)
    s1.metric("Sentiment", sent["label"], delta=f"{sent['score']:+.2f}")
    s2.metric("Sentiment engine", sent["engine"])

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### :material/label: Named entities")
        entities = result["entities"]
        if entities:
            st.dataframe(
                [{"Entity": e["text"], "Type": e["label"]} for e in entities],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("No entities detected.")
    with col_b:
        st.markdown("##### :material/key: Keywords (TF-IDF)")
        keywords = result["keywords"]
        if keywords:
            st.bar_chart({k["term"]: k["score"] for k in keywords})
        else:
            st.caption("No keywords extracted.")

    with st.expander("Tokens, lemmas & active engines", icon=":material/data_object:"):
        st.write("**Engines:**", result["engines"])
        st.write("**Tokens (sample):**", ", ".join(result["tokens_sample"]))
        st.write("**Lemmas (sample):**", ", ".join(result["lemmas_sample"]))


def render_nlp(client: APIClient, token: str) -> None:
    """Render the NLP dashboard."""
    st.markdown("## :material/psychology: NLP Dashboard")
    st.caption("Tokenization · NER · Keywords · Embeddings · Similarity · Sentiment.")

    text_tab, doc_tab, sim_tab = st.tabs(
        [":material/article: Analyze text", ":material/description: Analyze document", ":material/compare_arrows: Similarity"]
    )

    # ---- Analyze text ---------------------------------------------------
    with text_tab:
        text = st.text_area("Paste text", height=180, key="nlp_text")
        if st.button("Analyze", type="primary", icon=":material/play_arrow:", key="nlp_analyze_btn"):
            if not text.strip():
                st.warning("Please paste some text.", icon=":material/warning:")
            else:
                with st.spinner("Running NLP pipeline…"):
                    ok, result = client.nlp_analyze_text(token, text)
                if ok:
                    _render_analysis(result)
                else:
                    st.error(f"Analysis failed: {result}", icon=":material/error:")

    # ---- Analyze document ----------------------------------------------
    with doc_tab:
        ok, docs = client.list_documents(token)
        if not ok or not docs:
            st.info("No stored documents. Upload one first.", icon=":material/info:")
        else:
            options = {f"#{d['id']} · {d['filename']}": d["id"] for d in docs}
            choice = st.selectbox("Choose a document", list(options.keys()), key="nlp_doc")
            if st.button("Analyze document", type="primary", icon=":material/play_arrow:", key="nlp_doc_btn"):
                with st.spinner("Running NLP pipeline…"):
                    ok, result = client.nlp_analyze_document(token, options[choice])
                if ok:
                    _render_analysis(result)
                else:
                    st.error(f"Analysis failed: {result}", icon=":material/error:")

    # ---- Similarity -----------------------------------------------------
    with sim_tab:
        st.markdown("##### :material/compare_arrows: Text-to-text similarity")
        ta = st.text_area("Text A", height=100, key="sim_a")
        tb = st.text_area("Text B", height=100, key="sim_b")
        if st.button("Compare texts", icon=":material/compare_arrows:", key="sim_btn"):
            if not (ta.strip() and tb.strip()):
                st.warning("Please fill in both texts.", icon=":material/warning:")
            else:
                ok, result = client.nlp_text_similarity(token, ta, tb)
                if ok:
                    st.metric("Cosine similarity", f"{result['similarity'] * 100:.1f}%")
                    st.caption(f"Embedding backend: {result['backend']}")
                else:
                    st.error(f"Failed: {result}", icon=":material/error:")

        st.divider()
        st.markdown("##### :material/find_in_page: Find similar documents")
        ok, docs = client.list_documents(token)
        if ok and docs:
            options = {f"#{d['id']} · {d['filename']}": d["id"] for d in docs}
            choice = st.selectbox("Target document", list(options.keys()), key="sim_doc")
            if st.button("Find similar", icon=":material/search:", key="sim_doc_btn"):
                ok, result = client.nlp_similar_documents(token, options[choice])
                if ok and result["results"]:
                    st.caption(f"Embedding backend: {result['backend']}")
                    st.dataframe(
                        [
                            {"Document": r["filename"], "Similarity": f"{r['similarity'] * 100:.1f}%"}
                            for r in result["results"]
                        ],
                        use_container_width=True, hide_index=True,
                    )
                elif ok:
                    st.info("No other documents to compare against. Upload more files.", icon=":material/info:")
                else:
                    st.error(f"Failed: {result}", icon=":material/error:")
        else:
            st.info("Upload at least two documents to compare them.", icon=":material/info:")
