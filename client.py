# client.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection() -> Client:
    """สร้างการเชื่อมต่อกับ Supabase ครั้งเดียวและ Cache ไว้ใช้งาน"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()