"""
Document classification view.

Lets the user (a) classify ad-hoc pasted text, or (b) classify one of their
stored documents. Shows the predicted category, a confidence metric, and the
full probability distribution as a bar chart.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient


def _show_result(result: dict) -> None:
    """Render a classification result (category, confidence, probabilities)."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted category", result["category"])
    c2.metric("Confidence", f"{result['confidence'] * 100:.1f}%")
    c3.metric("Model", result["model_name"])

    if result["confidence"] >= 0.75:
        st.success("High-confidence prediction.")
    elif result["confidence"] >= 0.5:
        st.warning("Moderate confidence — review recommended.")
    else:
        st.error("Low confidence — the document may be ambiguous or out-of-domain.")

    st.markdown("**Probability distribution**")
    probs = dict(sorted(result["probabilities"].items(), key=lambda kv: kv[1], reverse=True))
    st.bar_chart(probs)


def render_classify(client: APIClient, token: str) -> None:
    """Render the classification page."""
    st.markdown("## 🔮 Document Classifier")
    st.caption("Classify text into: Resume · Invoice · Legal · Medical · Research.")

    # Show which model is deployed.
    ok, info = client.model_info(token)
    if ok:
        st.info(
            f"Deployed model: **{info['model_name']}** · trained {info['trained_at']}",
            icon="🤖",
        )
    else:
        st.warning(f"Model unavailable: {info}")

    text_tab, doc_tab = st.tabs(["Classify text", "Classify a stored document"])

    # ---- Ad-hoc text ----------------------------------------------------
    with text_tab:
        text = st.text_area(
            "Paste document text",
            height=200,
            placeholder="Paste a resume, invoice, contract, medical note, or paper…",
        )
        if st.button("Classify text", type="primary"):
            if not text.strip():
                st.warning("Please paste some text first.")
            else:
                with st.spinner("Running the model…"):
                    ok, result = client.classify_text(token, text)
                if ok:
                    _show_result(result)
                else:
                    st.error(f"Classification failed: {result}")

    # ---- Stored document ------------------------------------------------
    with doc_tab:
        ok, documents = client.list_documents(token)
        if not ok or not documents:
            st.info("No stored documents. Upload one first on the **Upload** page.")
            return
        options = {f"#{d['id']} · {d['filename']}": d["id"] for d in documents}
        choice = st.selectbox("Choose a document", list(options.keys()))
        if st.button("Classify document", type="primary"):
            with st.spinner("Running the model…"):
                ok, result = client.classify_document(token, options[choice])
            if ok:
                _show_result(result)
                st.caption("Result saved to the document — visible on your Dashboard.")
            else:
                st.error(f"Classification failed: {result}")
