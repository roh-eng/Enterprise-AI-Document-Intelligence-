"""
Analytics dashboard view (the landing page after login).

Renders KPI metric cards plus charts for upload activity, file-type mix,
classification distribution, and sentiment distribution, followed by the user's
recent search and upload history.
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


def render_dashboard(client: APIClient, token: str, user: dict) -> None:
    """Render the analytics dashboard."""
    st.markdown(
        f'<div class="hero"><h1>Analytics Dashboard</h1>'
        f'<p>Welcome back, {user.get("username", "user")} — here is your document intelligence at a glance.</p></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    ok, data = client.analytics_me(token)
    if not ok:
        st.error(f"Could not load analytics: {data}", icon=":material/error:")
        return

    # --- KPI metric cards ------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(":material/description: Documents", data["total_documents"])
    c2.metric(":material/text_fields: Characters", f"{data['total_chars']:,}")
    c3.metric(":material/dataset: Chunks indexed", data["total_chunks"])
    c4.metric(":material/search: Searches", data["total_searches"])

    if data["total_documents"] == 0:
        st.info("No documents yet — upload one to populate your dashboard.", icon=":material/info:")
        return

    st.divider()

    # --- Charts (responsive 2x2 grid) ------------------------------------
    row1 = st.columns(2)
    with row1[0]:
        st.markdown("##### :material/trending_up: Uploads over time")
        ubd = data["uploads_by_date"]
        if ubd:
            st.line_chart({d["date"]: d["count"] for d in ubd}, use_container_width=True)
        else:
            st.caption("No data.")
    with row1[1]:
        st.markdown("##### :material/folder: File types")
        st.bar_chart(data["file_type_distribution"], use_container_width=True)

    row2 = st.columns(2)
    with row2[0]:
        st.markdown("##### :material/label: Classification distribution")
        st.bar_chart(data["category_distribution"], use_container_width=True)
    with row2[1]:
        st.markdown("##### :material/mood: Sentiment distribution")
        st.bar_chart(data["sentiment_distribution"], use_container_width=True)

    st.divider()

    # --- History ---------------------------------------------------------
    h1, h2 = st.columns(2)
    with h1:
        st.markdown("##### :material/search: Recent searches")
        searches = data["recent_searches"]
        if searches:
            st.dataframe(
                [{"Question": s["question"], "Doc": s["document_id"], "When": _fmt_dt(s["created_at"])}
                 for s in searches],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("No searches yet. Try the Chat page.")
    with h2:
        st.markdown("##### :material/upload_file: Recent uploads")
        st.dataframe(
            [{"File": u["filename"], "Type": u["file_ext"], "When": _fmt_dt(u["created_at"])}
             for u in data["recent_uploads"]],
            use_container_width=True, hide_index=True,
        )
