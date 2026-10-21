# client.py
import os
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    """สร้างการเชื่อมต่อกับ Supabase ครั้งเดียวและ Cache ไว้ใช้งาน"""
    # 1. ตรวจสอบค่าจาก Environment Variables (สำหรับ Render)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # 2. หากไม่พบ ให้ดึงจาก st.secrets (สำหรับ Local)
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
        print(f"Error initializing Supabase client: {e}")
        return None

# กำหนดตัวแปร supabase เสมอเพื่อไม่ให้เกิด ImportError
supabase = init_connection()
