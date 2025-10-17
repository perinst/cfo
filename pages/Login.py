import streamlit as st
from auth.auth_service import AuthService
from auth.session_manager import SessionManager

st.set_page_config(
    page_title="Login - AI CFO Assistant", page_icon="🔐", layout="centered"
)

# Check if already logged in (via query params persistence)
if SessionManager.is_authenticated():
    st.success("Already signed in. Redirecting...")
    st.switch_page("app.py")

st.title("🔐 Sign in to AI CFO Assistant")

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Sign In", type="primary", use_container_width=True):
    auth = AuthService()
    prof = auth.sign_in(email, password)
    if prof:
        # Use SessionManager to persist login across page reloads
        SessionManager.set_user(prof)
        st.success("Signed in")
        st.switch_page("app.py")
    else:
        st.error("Invalid credentials or user not found")

st.caption(
    "Use your Supabase Auth credentials. Profiles and roles are mapped via public.users"
)
