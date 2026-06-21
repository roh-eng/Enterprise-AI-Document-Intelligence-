"""
Authentication view: login and registration forms.

Rendered only when the user is NOT logged in. On a successful login it stores
the JWT and profile in `st.session_state` and reruns the app, which flips it
into the authenticated experience.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import APIClient


def render_auth(client: APIClient) -> None:
    """Render the login / register tabs."""
    st.markdown("## 🔐 Welcome")
    st.caption("Sign in to access your AI Document Intelligence workspace.")

    login_tab, register_tab = st.tabs(["Login", "Create account"])

    # ---- Login ----------------------------------------------------------
    with login_tab:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submitted:
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                ok, payload = client.login(username, password)
                if ok:
                    token = payload["access_token"]
                    me_ok, me = client.get_me(token)
                    if me_ok:
                        st.session_state["token"] = token
                        st.session_state["user"] = me
                        st.success("Logged in successfully. Loading your workspace…")
                        st.rerun()
                    else:
                        st.error(f"Logged in but could not load profile: {me}")
                else:
                    st.error(f"Login failed: {payload}")

    # ---- Register -------------------------------------------------------
    with register_tab:
        with st.form("register_form", clear_on_submit=False):
            new_username = st.text_input("Username (min 3 chars)", key="reg_username")
            new_email = st.text_input("Email", key="reg_email")
            new_password = st.text_input(
                "Password (min 8 chars)", type="password", key="reg_password"
            )
            submitted = st.form_submit_button("Create account", use_container_width=True)

        if submitted:
            if not (new_username and new_email and new_password):
                st.warning("All fields are required.")
            elif len(new_password) < 8:
                st.warning("Password must be at least 8 characters.")
            else:
                ok, payload = client.register(new_username, new_email, new_password)
                if ok:
                    st.success("Account created! Switch to the **Login** tab to sign in.")
                else:
                    st.error(f"Registration failed: {payload}")
