import hashlib

import streamlit as st


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_credentials():
    try:
        return st.secrets.get("credentials", {})
    except Exception:
        return {}


def _check_login(username: str, password: str):
    creds = _get_credentials()
    user = creds.get(username.strip().lower())
    if user and _hash(password) == user.get("password_hash"):
        return dict(user)
    return None


def require_login():
    """Blocks until a valid username/password is submitted. Returns the
    logged-in user's credential dict (role, name, manager_email if any).
    """
    if "auth_user" in st.session_state:
        return st.session_state["auth_user"]

    st.title("MVH Report")
    st.subheader("Sign in")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        user = _check_login(username, password)
        if user:
            st.session_state["auth_user"] = user
            st.rerun()
        else:
            st.error("Incorrect username or password.")

    if not _get_credentials():
        st.warning(
            "No credentials are configured yet — add a `[credentials]` section to "
            "this app's secrets before anyone can sign in."
        )

    st.stop()


def logout_button():
    if st.sidebar.button("Log out"):
        st.session_state.pop("auth_user", None)
        st.rerun()
