"""
Admin dashboard view (visible only to admin users).

Shows platform-wide statistics: totals, documents per user, and category /
file-type distributions across all users.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient


def render_admin(client: APIClient, token: str) -> None:
    """Render the platform admin dashboard."""
    st.markdown(
        '<div class="hero"><h1>🛡️ Admin Dashboard</h1>'
        '<p>Platform-wide usage and content statistics.</p></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    ok, data = client.analytics_admin(token)
    if not ok:
        st.error(f"Could not load admin analytics: {data}")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Users", data["total_users"])
    c2.metric("📄 Documents", data["total_documents"])
    c3.metric("🔎 Searches", data["total_searches"])

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 👤 Documents per user")
        dpu = data["documents_per_user"]
        if dpu:
            st.bar_chart({u["username"]: u["document_count"] for u in dpu}, use_container_width=True)
        else:
            st.caption("No data.")
    with col2:
        st.markdown("##### 🏷️ Categories (all users)")
        st.bar_chart(data["category_distribution"], use_container_width=True)

    st.markdown("##### 🗂️ File types (all users)")
    st.bar_chart(data["file_type_distribution"], use_container_width=True)
