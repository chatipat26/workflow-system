# client.py
import os
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection() -> Client:
    """สร้างการเชื่อมต่อกับ Supabase ครั้งเดียวและ Cache ไว้ใช้งาน"""
    # 1. ตรวจสอบค่าจาก Environment Variables (สำหรับ Render / Cloud Deploy)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # 2. หากไม่พบใน Env Vars ให้ดึงจาก st.secrets (สำหรับรันแบบ Local ด้วย Streamlit)
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
        st.error("⚠️ ไม่พบการตั้งค่า SUPABASE_URL หรือ SUPABASE_KEY ใน Environment Variables หรือ secrets.toml")
        st.stop()

    return create_client(url, key)

supabase = init_connection()
