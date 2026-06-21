"""
Streamlit frontend entrypoint.

This single controller owns authentication state and navigation:
  * If the user is not logged in -> show the auth (login/register) view.
  * If logged in -> show a sidebar with profile + navigation across all modules,
    plus an admin-only page and a logout button.

Centralising the auth gate here (rather than using Streamlit's auto `pages/`
folder) guarantees no protected view can be reached without a valid session.

Theming: a dark theme is configured in `.streamlit/config.toml`; users can also
switch light/dark from Streamlit's built-in settings menu. Custom CSS below adds
premium metric cards and a hero banner.

Run with:  streamlit run frontend/app.py
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient
from views.admin_view import render_admin
from views.analytics_view import render_dashboard
from views.auth_view import render_auth
from views.chat_view import render_chat
from views.classify_view import render_classify
from views.documents_view import render_documents
from views.genai_view import render_genai
from views.nlp_view import render_nlp
from views.upload_view import render_upload

st.set_page_config(
    page_title="AI Document Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium styling: gradient hero banner + elevated metric cards. Works on top of
# whichever theme (dark default) is active.
CUSTOM_CSS = """
<style>
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; }
    .hero {
        background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #2563eb 100%);
        padding: 22px 30px; border-radius: 16px; color: #fff; margin-bottom: 6px;
        box-shadow: 0 10px 28px rgba(79,70,229,0.32);
    }
    .hero h1 { margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: -0.5px; }
    .hero p  { margin: 6px 0 0 0; opacity: 0.92; }
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 14px 16px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.18);
    }
    div[data-testid="stMetricValue"] { font-weight: 700; }
</style>
"""


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
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    _init_state()
    client = get_client()

    st.sidebar.title("🧠 AI Doc Intelligence")

    # ---- Not authenticated: show login/register only --------------------
    if not st.session_state["token"]:
        ok, _ = client.health()
        st.sidebar.success("Backend: connected") if ok else st.sidebar.error("Backend: offline")
        render_auth(client)
        return

    # ---- Authenticated experience ---------------------------------------
    user = st.session_state["user"]
    token = st.session_state["token"]

    st.sidebar.markdown(f"**Signed in as**\n\n`{user.get('username', 'user')}`")
    if user.get("is_admin"):
        st.sidebar.caption("🛡️ Admin")

    pages = ["🏠 Dashboard", "📁 Documents", "📤 Upload", "🔮 Classify", "🧬 NLP", "✨ GenAI", "💬 Chat"]
    if user.get("is_admin"):
        pages.append("🛡️ Admin")

    page = st.sidebar.radio("Navigate", pages, label_visibility="collapsed")
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        _logout()
        st.rerun()

    if page == "🏠 Dashboard":
        render_dashboard(client, token, user)
    elif page == "📁 Documents":
        render_documents(client, token, user)
    elif page == "📤 Upload":
        render_upload(client, token)
    elif page == "🔮 Classify":
        render_classify(client, token)
    elif page == "🧬 NLP":
        render_nlp(client, token)
    elif page == "✨ GenAI":
        render_genai(client, token)
    elif page == "💬 Chat":
        render_chat(client, token)
    else:
        render_admin(client, token)


if __name__ == "__main__":
    main()
