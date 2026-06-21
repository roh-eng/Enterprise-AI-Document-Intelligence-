"""
Streamlit frontend entrypoint.

This single controller owns authentication state and navigation:
  * If the user is not logged in -> show the auth (login/register) view.
  * If logged in -> show a sidebar with profile + navigation to the Dashboard
    and Upload views, plus a logout button.

Centralising the auth gate here (rather than using Streamlit's auto `pages/`
folder) guarantees no protected view can be reached without a valid session.

Run with:  streamlit run frontend/app.py
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient
from views.auth_view import render_auth
from views.classify_view import render_classify
from views.dashboard_view import render_dashboard
from views.genai_view import render_genai
from views.nlp_view import render_nlp
from views.upload_view import render_upload

st.set_page_config(
    page_title="AI Document Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_client() -> APIClient:
    """One shared API client per Streamlit server process."""
    return APIClient()


def _init_state() -> None:
    """Ensure expected keys exist in session state."""
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("user", None)


def _logout() -> None:
    st.session_state["token"] = None
    st.session_state["user"] = None


def main() -> None:
    _init_state()
    client = get_client()

    st.sidebar.title("🧠 AI Doc Intelligence")

    # ---- Not authenticated: show login/register only --------------------
    if not st.session_state["token"]:
        # Surface backend connectivity so a down server is obvious immediately.
        ok, _ = client.health()
        if ok:
            st.sidebar.success("Backend: connected")
        else:
            st.sidebar.error("Backend: offline")
        render_auth(client)
        return

    # ---- Authenticated experience ---------------------------------------
    user = st.session_state["user"]
    token = st.session_state["token"]

    st.sidebar.markdown(f"**Signed in as**\n\n`{user.get('username', 'user')}`")
    page = st.sidebar.radio(
        "Navigate",
        ["🏠 Dashboard", "📤 Upload", "🔮 Classify", "🧬 NLP", "✨ GenAI"],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        _logout()
        st.rerun()

    if page == "🏠 Dashboard":
        render_dashboard(client, token, user)
    elif page == "📤 Upload":
        render_upload(client, token)
    elif page == "🔮 Classify":
        render_classify(client, token)
    elif page == "🧬 NLP":
        render_nlp(client, token)
    else:
        render_genai(client, token)


if __name__ == "__main__":
    main()
