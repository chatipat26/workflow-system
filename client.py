# client.py
import os
import streamlit as st
from supabase import create_client, Client

def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url:
        try:
            url = st.secrets.get("SUPABASE_URL")
        except Exception:
            url = None
    if not key:
        try:
            key = st.secrets.get("SUPABASE_KEY")
        except Exception:
            key = None
    if not url or not key:
        return None
    try:
        return create_client(url.strip(), key.strip())
    except Exception as e:
        return None

supabase = init_connection()
