# auth/session_manager.py
import streamlit as st
from typing import Optional, Dict
from config.database import get_db


class SessionManager:
    """Manages persistent user sessions across page reloads"""

    @staticmethod
    def get_current_user() -> Optional[Dict]:
        """
        Get current authenticated user from session state or restore from query params.
        Returns user profile dict or None if not authenticated.
        """
        # Check if already loaded in session
        if "auth_user" in st.session_state and st.session_state["auth_user"]:
            return st.session_state["auth_user"]

        # Try to restore from query params (for page reload persistence)
        query_params = st.query_params
        user_id = query_params.get("user_id")

        if user_id:
            # Restore user profile from database
            try:
                db = get_db()
                result = (
                    db.table("users").select("*").eq("id", user_id).limit(1).execute()
                )
                if result.data:
                    user = result.data[0]
                    st.session_state["auth_user"] = user
                    return user
            except Exception as e:
                print(f"Error restoring session: {e}")
                return None

        return None

    @staticmethod
    def set_user(user: Dict):
        """
        Store user in session and add user_id to query params for persistence.
        """
        st.session_state["auth_user"] = user
        # Add user_id to query params so it persists across page reloads
        st.query_params["user_id"] = str(user["id"])

    @staticmethod
    def clear_user():
        """
        Clear user from session and remove from query params.
        """
        if "auth_user" in st.session_state:
            del st.session_state["auth_user"]
        # Clear query params
        if "user_id" in st.query_params:
            del st.query_params["user_id"]

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is currently authenticated"""
        return SessionManager.get_current_user() is not None
