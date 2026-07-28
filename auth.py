import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

REMEMBER_TOKENS_PATH = Path(__file__).parent / "remember_tokens.json"
REMEMBER_TTL_DAYS = 30


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


def _load_tokens():
    if REMEMBER_TOKENS_PATH.exists():
        return json.loads(REMEMBER_TOKENS_PATH.read_text())
    return {}


def _save_tokens(tokens):
    REMEMBER_TOKENS_PATH.write_text(json.dumps(tokens))


def _create_remember_token(username: str) -> str:
    tokens = _load_tokens()
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=REMEMBER_TTL_DAYS)).isoformat()
    tokens[token] = {"username": username, "expires": expires}
    _save_tokens(tokens)
    return token


def _resolve_remember_token(token: str):
    tokens = _load_tokens()
    entry = tokens.get(token)
    if not entry:
        return None
    if datetime.fromisoformat(entry["expires"]) < datetime.now():
        tokens.pop(token, None)
        _save_tokens(tokens)
        return None
    return entry["username"]


def _invalidate_remember_token(token: str):
    tokens = _load_tokens()
    if tokens.pop(token, None) is not None:
        _save_tokens(tokens)


def require_login():
    """Blocks until a valid username/password is submitted (or a valid
    "remember me" token is found in the URL). Returns the logged-in user's
    credential dict (role, name, manager_email if any).
    """
    if "auth_user" in st.session_state:
        return st.session_state["auth_user"]

    token = st.query_params.get("rt")
    if token:
        username = _resolve_remember_token(token)
        if username:
            user = _get_credentials().get(username)
            if user:
                st.session_state["auth_user"] = dict(user)
                st.session_state["auth_username"] = username
                st.session_state["remember_token"] = token
                return st.session_state["auth_user"]
        st.query_params.pop("rt", None)

    st.title("MVH Report")
    st.subheader("Sign in")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        remember = st.checkbox("Keep me signed in")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        user = _check_login(username, password)
        if user:
            clean_username = username.strip().lower()
            st.session_state["auth_user"] = user
            st.session_state["auth_username"] = clean_username
            if remember:
                new_token = _create_remember_token(clean_username)
                st.session_state["remember_token"] = new_token
                st.query_params["rt"] = new_token
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
        token = st.session_state.get("remember_token")
        if token:
            _invalidate_remember_token(token)
        st.query_params.pop("rt", None)
        st.session_state.pop("auth_user", None)
        st.session_state.pop("auth_username", None)
        st.session_state.pop("remember_token", None)
        st.rerun()
