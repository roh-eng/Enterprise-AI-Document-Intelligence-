"""
Authentication view: a centered login / registration card.

Rendered only when the user is NOT logged in. On a successful login it stores
the JWT and profile in `st.session_state` and reruns the app, which flips it
into the authenticated experience.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient


def render_auth(client: APIClient) -> None:
    """Render a horizontally-centered login / register card."""
    # Top spacing nudges the card toward the vertical middle of the page.
    for _ in range(3):
        st.write("")

    # Center the card: empty side columns squeeze a narrow middle column.
    _, center, _ = st.columns([1, 1.4, 1])

    with center:
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center'>"
                "<h2 style='margin-bottom:4px'>AI Document Intelligence</h2>"
                "<p style='color:#8b93a7;margin-top:0'>Sign in to access your workspace.</p>"
                "</div>",
                unsafe_allow_html=True,
            )

            login_tab, register_tab = st.tabs(
                [":material/login: Login", ":material/person_add: Create account"]
            )

            # ---- Login --------------------------------------------------
            with login_tab:
                with st.form("login_form", clear_on_submit=False):
                    username = st.text_input("Username", key="login_username")
                    password = st.text_input("Password", type="password", key="login_password")
                    submitted = st.form_submit_button(
                        "Login", type="primary", icon=":material/login:", use_container_width=True
                    )

                if submitted:
                    if not username or not password:
                        st.warning("Please enter both username and password.", icon=":material/warning:")
                    else:
                        ok, payload = client.login(username, password)
                        if ok:
                            token = payload["access_token"]
                            me_ok, me = client.get_me(token)
                            if me_ok:
                                st.session_state["token"] = token
                                st.session_state["user"] = me
                                st.success("Logged in. Loading your workspace…", icon=":material/check_circle:")
                                st.rerun()
                            else:
                                st.error(f"Logged in but could not load profile: {me}", icon=":material/error:")
                        else:
                            st.error(f"Login failed: {payload}", icon=":material/error:")

            # ---- Register -----------------------------------------------
            with register_tab:
                with st.form("register_form", clear_on_submit=False):
                    new_username = st.text_input("Username (min 3 chars)", key="reg_username")
                    new_email = st.text_input("Email", key="reg_email")
                    new_password = st.text_input(
                        "Password (min 8 chars)", type="password", key="reg_password"
                    )
                    submitted = st.form_submit_button(
                        "Create account", icon=":material/person_add:", use_container_width=True
                    )

                if submitted:
                    if not (new_username and new_email and new_password):
                        st.warning("All fields are required.", icon=":material/warning:")
                    elif len(new_password) < 8:
                        st.warning("Password must be at least 8 characters.", icon=":material/warning:")
                    else:
                        ok, payload = client.register(new_username, new_email, new_password)
                        if ok:
                            st.success(
                                "Account created! Switch to the **Login** tab to sign in.",
                                icon=":material/check_circle:",
                            )
                        else:
                            st.error(f"Registration failed: {payload}", icon=":material/error:")
