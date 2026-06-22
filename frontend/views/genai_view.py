"""
Generative AI view.

Pick a task (summary, FAQ, interview questions, explanation, action items,
deadlines) and an input (pasted text or a stored document), then render the
generated result. Shows whether the output came from Gemini or the offline
fallback.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient

# UI label -> backend task key.
# Plain labels: st.selectbox options render as text (not markdown), so icons
# would show literally — keep these clean.
_TASKS = {
    "Summary": "summary",
    "Explain document": "explain",
    "FAQ generation": "faq",
    "Interview questions": "interview_questions",
    "Action items": "action_items",
    "Deadlines": "deadlines",
}


def _render_result(task: str, result: dict) -> None:
    """Render the populated field of a generation response."""
    src = result["source"]
    badge = ":material/cloud: Gemini" if src == "gemini" else ":material/cloud_off: Offline fallback"
    st.caption(f"Source: {badge} · model: `{result['model_used']}` · cached: {result['cached']}")

    if task == "summary":
        st.markdown(result.get("summary") or "_No summary._")
    elif task == "explain":
        st.markdown(result.get("explanation") or "_No explanation._")
    elif task == "faq":
        for item in result.get("faq") or []:
            st.markdown(f"**Q: {item['question']}**")
            st.markdown(f"A: {item['answer']}")
    elif task == "interview_questions":
        for i, q in enumerate(result.get("interview_questions") or [], 1):
            st.markdown(f"{i}. {q}")
    elif task == "action_items":
        items = result.get("action_items") or []
        if items:
            for a in items:
                st.markdown(f"- {a}")
        else:
            st.info("No action items detected.", icon=":material/info:")
    elif task == "deadlines":
        rows = result.get("deadlines") or []
        if rows:
            st.dataframe(
                [{"Due": d["due"], "Context": d["text"]} for d in rows],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No deadlines detected.", icon=":material/info:")


def render_genai(client: APIClient, token: str) -> None:
    """Render the Generative AI page."""
    st.markdown("## :material/auto_awesome: Generative AI")
    st.caption("Summaries, FAQs, interview questions, explanations, action items & deadlines.")

    ok, status = client.genai_status(token)
    if ok:
        if status["gemini_enabled"]:
            st.success(f"Gemini live · model `{status['model']}`", icon=":material/smart_toy:")
        else:
            st.info("Gemini key not configured — using the offline fallback generator.", icon=":material/info:")

    label = st.selectbox("Task", list(_TASKS.keys()))
    task = _TASKS[label]

    text_tab, doc_tab = st.tabs([":material/article: From text", ":material/description: From a document"])

    with text_tab:
        text = st.text_area("Paste text", height=200, key="genai_text")
        if st.button("Generate", type="primary", icon=":material/auto_awesome:", key="genai_text_btn"):
            if not text.strip():
                st.warning("Please paste some text.", icon=":material/warning:")
            else:
                with st.spinner("Generating…"):
                    ok, result = client.genai_generate(token, task, text=text)
                if ok:
                    _render_result(task, result)
                else:
                    st.error(f"Generation failed: {result}", icon=":material/error:")

    with doc_tab:
        ok, docs = client.list_documents(token)
        if not ok or not docs:
            st.info("No stored documents. Upload one first.", icon=":material/info:")
        else:
            options = {f"#{d['id']} · {d['filename']}": d["id"] for d in docs}
            choice = st.selectbox("Choose a document", list(options.keys()), key="genai_doc")
            if st.button("Generate", type="primary", icon=":material/auto_awesome:", key="genai_doc_btn"):
                with st.spinner("Generating…"):
                    ok, result = client.genai_generate(token, task, document_id=options[choice])
                if ok:
                    _render_result(task, result)
                else:
                    st.error(f"Generation failed: {result}", icon=":material/error:")
