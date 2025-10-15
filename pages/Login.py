import streamlit as st
from auth.auth_service import AuthService

st.set_page_config(
    page_title="Login - AI CFO Assistant", page_icon="🔐", layout="centered"
)

st.title("🔐 Sign in to AI CFO Assistant")

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Sign In", type="primary", use_container_width=True):
    auth = AuthService()
    prof = auth.sign_in(email, password)
    if prof:
        st.session_state["auth_user"] = prof
        st.success("Signed in")
        st.switch_page("app.py")
    else:
        st.error("Invalid credentials or user not found")

st.caption(
    "Use your Supabase Auth credentials. Profiles and roles are mapped via public.users"
)
