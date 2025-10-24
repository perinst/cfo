import os
import streamlit as st


def get_config(name: str, default=None):
    v = os.getenv(name)
    if v:
        return v
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return default
