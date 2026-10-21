import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import json
from client import supabase

# --- Configuration & Theme Setup ---
st.set_page_config(
    page_title="Team Workflow & KPI Hub",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Auspicious Red Theme & Image 1/2 Aesthetics
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Sarabun', sans-serif;
    }
    
    /* Background & Main App */
    .stApp {
        background-color: #faf8f8;
    }

    /* Auspicious Red Metric Box (Like Image 2) */
    .stat-box {
        background: #ffffff;
        border: 1px solid #fee2e2;
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(185, 28, 28, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 12px;
    }
    .stat-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 14px rgba(185, 28, 28, 0.08);
        border-color: #fca5a5;
    }
    .stat-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
    .stat-number {
        font-size: 1.85rem;
        font-weight: 700;
        color: #991b1b;
        margin: 4px 0;
        line-height: 1.2;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 600;
        display: flex;
        align-items: center;
    }
    .stat-sub {
        font-size: 0.75rem;
        color: #94a3b8;
    }

    /* The Booking / Filter Bar (Like Image 1) */
    .booking-filter-bar {
        background: #ffffff;
        border: 1px solid #fecaca;
        border-radius: 20px;
        padding: 18px 24px;
        box-shadow: 0 6px 20px rgba(185, 28, 28, 0.05);
        margin-bottom: 24px;
    }

    /* Showcase Card (Like Image 1 "Our Elite Fleet") */
    .showcase-card {
        background: #ffffff;
        border: 1px solid #fce7e7;
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 3px 10px rgba(185, 28, 28, 0.04);
        border-top: 4px solid #b91c1c;
        transition: all 0.25s ease;
    }
    .showcase-card:hover {
        box-shadow: 0 8px 22px rgba(185, 28, 28, 0.1);
        border-color: #fca5a5;
        transform: translateY(-2px);
    }
    .showcase-card-overdue {
        border-top: 4px solid #ef4444 !important;
        background-color: #fffbfb !important;
        border-color: #fecaca !important;
    }
    .showcase-card-warning {
        border-top: 4px solid #f59e0b !important;
        background-color: #fffefb !important;
    }
    .showcase-card-done {
        border-top: 4px solid #10b981 !important;
        opacity: 0.85;
    }

    .showcase-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e293b;
        margin-top: 8px;
        margin-bottom: 6px;
    }

    /* Badges & Pills */
    .badge-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 4px;
    }
    .badge-red {
        background-color: #fee2e2;
        color: #991b1b;
    }
    .badge-gold {
        background-color: #fef3c7;
        color: #92400e;
    }
    .badge-green {
        background-color: #dcfce7;
        color: #166534;
    }
    .badge-blue {
        background-color: #e0e7ff;
        color: #3730a3;
    }
    .badge-purple {
        background-color: #f3e8ff;
        color: #6b21a8;
    }

    /* Buttons Auspicious Styling */
    div[data-baseweb="button"] > button[kind="primary"] {
        background: linear-gradient(135deg, #b91c1c 0%, #dc2626 100%) !important;
        border: none !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 12px rgba(185, 28, 28, 0.22) !important;
        font-weight: 600 !important;
    }
    div[data-baseweb="button"] > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #fee2e2;
    }
    </style>
""", unsafe_allow_html=True)

# --- Supabase Connection Check ---
if supabase is None:
    st.error("⚠️ ไม่สามารถเชื่อมต่อกับฐานข้อมูล Supabase ได้")
    st.info("💡 วิธีแก้ไข: ไปที่ Render Dashboard > Environment > ตรวจสอบว่าใส่ `SUPABASE_URL` และ `SUPABASE_KEY` ถูกต้องแล้วกด Save Changes")
    st.stop()

# --- Session State Management ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

# --- Helper Functions for Roles & Database ---

def parse_roles(roles_val):
    """แปลงค่า roles ที่เก็บใน Database ให้เป็น list"""
    if not roles_val:
        return ["ปฏิบัติงาน"]
    if isinstance(roles_val, list):
        return roles_val
    return [r.strip() for r in str(roles_val).split(",") if r.strip()]

def user_has_role(user_dict, role_name):
    """ตรวจสอบว่า User มียศตามที่ระบุหรือไม่ (Admin มีสิทธิ์ทุกยศเสมอ)"""
    if not user_dict:
        return False
    if user_dict.get("role") == "Admin" or user_dict.get("username") == "admin":
        return True
    user_roles = parse_roles(user_dict.get("roles"))
    return role_name in user_roles

def fetch_all_users():
    """ดึงข้อมูลผู้ใช้งานทั้งหมด"""
    try:
        res = supabase.table("app_users").select("*").execute()
        return res.data or []
    except Exception as e:
        return []

def fetch_operators():
    """ดึงรายชื่อพนักงานที่มีสิทธิ์ 'ปฏิบัติงาน' และได้รับการอนุมัติแล้ว"""
    users = fetch_all_users()
    operators = []
    for u in users:
        is_approved = u.get("is_approved", True)
        roles = parse_roles(u.get("roles"))
        if is_approved and ("ปฏิบัติงาน" in roles or u.get("role") == "Admin"):
            display_name = u.get("fullname") or u.get("username")
            operators.append({
                "username": u.get("username"),
                "display_name": f"{display_name} (@{u.get('username')})"
            })
    return operators

def fetch_tasks():
    """ดึงข้อมูลงานทั้งหมด"""
    try:
        res = supabase.table("tasks").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def log_task_action(task_id, action, performed_by, details=""):
    """บันทึกประวัติการเปลี่ยนแปลงของงาน (Audit Log)"""
    try:
        supabase.table("task_logs").insert({
            "task_id": task_id,
            "action": action,
            "performed_by": performed_by,
            "details": details
        }).execute()
    except Exception:
        pass

def fetch_task_logs(task_id):
    """ดึงประวัติการทำงานของงานนั้นๆ"""
    try:
        res = supabase.table("task_logs").select("*").eq("task_id", task_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def fetch_kpi_adjustments(username=None):
    """ดึงคะแนนเพิ่ม/ลด KPI"""
    try:
        query = supabase.table("kpi_adjustments").select("*")
        if username:
            query = query.eq("username", username)
        res = query.order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

# --- Module: Authentication & Registration & Password Reset ---

def show_auth_page():
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem; margin-top: 1rem;">
            <h1 style="color: #991b1b; font-weight: 700; margin-bottom: 0.25rem;">✨ ระบบจัดการงาน & ประเมินผล KPI (Workflow Hub)</h1>
            <p style="color: #64748b; font-size: 1.05rem;">ระบบติดตามสถานะงาน Kanban บันทึกผลงาน และคำนวณ KPI รายบุคคล</p>
        </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register, tab_reset = st.tabs([
        "🔒 เข้าสู่ระบบ (Login)", 
        "📝 สมัครสมาชิกใหม่ (Register)", 
        "🔑 ลืม / เปลี่ยนรหัสผ่าน (Reset Password)"
    ])

    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="stat-box" style="padding: 24px;">', unsafe_allow_html=True)
            st.subheader("เข้าสู่ระบบ")
            username = st.text_input("ชื่อผู้ใช้งาน (Username)", key="login_username")
            password = st.text_input("รหัสผ่าน (Password)", type="password", key="login_password")
            
            if st.button("เข้าสู่ระบบ", use_container_width=True, type="primary"):
                if not username or not password:
                    st.warning("กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
                else:
                    try:
                        res = supabase.table("app_users").select("*").eq("username", username).eq("password_hash", password).execute()
                        if res.data and len(res.data) > 0:
                            user = res.data[0]
                            is_approved = user.get("is_approved")
                            if is_approved is False and user.get("role") != "Admin" and user.get("username") != "admin":
                                st.warning("⏳ บัญชีของคุณอยู่ระหว่างรอผู้ดูแลระบบ (Admin) อนุมัติและกำหนดยศ กรุณาติดต่อ Admin")
                            else:
                                st.session_state.logged_in = True
                                st.session_state.user = user
                                st.success("เข้าสู่ระบบสำเร็จ!")
                                st.rerun()
                        else:
                            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการตรวจสอบผู้ใช้: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_register:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="stat-box" style="padding: 24px;">', unsafe_allow_html=True)
            st.subheader("สมัครสมาชิกพนักงานใหม่")
            st.caption("เมื่อสมัครเสร็จสิ้น บัญชีจะถูกส่งให้ Admin ตรวจสอบและให้ยศก่อนเข้าใช้")
            
            with st.form("register_form", clear_on_submit=True):
                reg_username = st.text_input("ชื่อผู้ใช้งาน (Username) *")
                reg_fullname = st.text_input("ชื่อ - นามสกุล (Full Name) *")
                reg_email = st.text_input("อีเมล (Email) *")
                reg_phone = st.text_input("เบอร์โทรศัพท์ (Phone Number) *")
                reg_pass1 = st.text_input("รหัสผ่าน (Password) *", type="password")
                reg_pass2 = st.text_input("ยืนยันรหัสผ่าน (Confirm Password) *", type="password")
                
                reg_submitted = st.form_submit_button("ส่งคำขอสมัครสมาชิก", use_container_width=True, type="primary")
                
                if reg_submitted:
                    if not (reg_username and reg_fullname and reg_email and reg_phone and reg_pass1):
                        st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")
                    elif reg_pass1 != reg_pass2:
                        st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                    else:
                        check_res = supabase.table("app_users").select("username").eq("username", reg_username).execute()
                        if check_res.data and len(check_res.data) > 0:
                            st.error("ชื่อผู้ใช้งานนี้มีอยู่ในระบบแล้ว กรุณาใช้ชื่ออื่น")
                        else:
                            new_user = {
                                "username": reg_username.strip(),
                                "password_hash": reg_pass1,
                                "fullname": reg_fullname.strip(),
                                "email": reg_email.strip(),
                                "phone": reg_phone.strip(),
                                "role": "Employee",
                                "roles": "ปฏิบัติงาน",
                                "is_approved": False
                            }
                            try:
                                supabase.table("app_users").insert(new_user).execute()
                                st.success("✅ สมัครสมาชิกเรียบร้อยแล้ว! กรุณารอ Admin อนุมัติและกำหนดยศก่อนเข้าใช้งาน")
                            except Exception as e:
                                st.error(f"ไม่สามารถบันทึกข้อมูลได้: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_reset:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="stat-box" style="padding: 24px;">', unsafe_allow_html=True)
            st.subheader("แก้ไข / ตั้งรหัสผ่านใหม่")
            st.caption("กรอก Username และ Email หรือ เบอร์โทรศัพท์ ที่ลงทะเบียนไว้เพื่อยืนยันตัวตน")
            
            with st.form("reset_form"):
                rst_username = st.text_input("ชื่อผู้ใช้งาน (Username) *")
                rst_contact = st.text_input("Email หรือ เบอร์โทร ที่ลงทะเบียนไว้ *")
                rst_new_pass = st.text_input("รหัสผ่านใหม่ *", type="password")
                rst_confirm_pass = st.text_input("ยืนยันรหัสผ่านใหม่ *", type="password")
                rst_submitted = st.form_submit_button("บันทึกรหัสผ่านใหม่", use_container_width=True, type="primary")
                
                if rst_submitted:
                    if not (rst_username and rst_contact and rst_new_pass):
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                    elif rst_new_pass != rst_confirm_pass:
                        st.error("รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน")
                    else:
                        u_res = supabase.table("app_users").select("*").eq("username", rst_username.strip()).execute()
                        if not u_res.data:
                            st.error("ไม่พบบัญชีผู้ใช้นี้ในระบบ")
                        else:
                            u_data = u_res.data[0]
                            db_email = str(u_data.get("email") or "").strip().lower()
                            db_phone = str(u_data.get("phone") or "").strip()
                            input_contact = rst_contact.strip().lower()
                            
                            if input_contact == db_email or input_contact == db_phone:
                                supabase.table("app_users").update({
                                    "password_hash": rst_new_pass
                                }).eq("user_id", u_data["user_id"]).execute()
                                st.success("✅ แก้ไขรหัสผ่านสำเร็จแล้ว! สามารถนำรหัสใหม่ไปเข้าสู่ระบบได้ทันที")
                            else:
                                st.error("ข้อมูล Email หรือ เบอร์โทร ไม่ตรงกับในระบบ")
            st.markdown('</div>', unsafe_allow_html=True)

# --- Module 1: ระบบสั่งการและมอบหมายงาน (Commander Hub) ---

def show_module1_commander_page():
    curr_user = st.session_state.user
    
    if not user_has_role(curr_user, "ระดับสั่งการ"):
        st.error("⛔ จำกัดสิทธิ์: โมดูลนี้อนุญาตให้เข้าใช้งานได้เฉพาะผู้มียศ **'ระดับสั่งการ'** เท่านั้น")
        st.info(f"ยศปัจจุบันของคุณ: {', '.join(parse_roles(curr_user.get('roles')))}")
        return

    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h2 style="color: #991b1b; font-weight: 700; margin-bottom: 0.2rem;">🎯 โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander Hub)</h2>
            <p style="color: #64748b;">สำหรับผู้มียศระดับสั่งการ: มอบหมายงาน, อนุมัติการส่งต่อ, ตรวจรับประเมินผล KPI และปรับคะแนนพนักงาน</p>
        </div>
    """, unsafe_allow_html=True)

    sub_m1, sub_m2, sub_m3, sub_m4 = st.tabs([
        "📝 มอบหมายงานใหม่", 
        "🔄 รายการรออนุมัติส่งต่องาน", 
        "⭐ ตรวจรับงาน & ประเมิน KPI", 
        "⚖️ ฟอร์มเพิ่ม/ลดคะแนน KPI"
    ])

    with sub_m1:
        st.subheader("สร้างและมอบหมายงานใหม่")
        operators = fetch_operators()
        op_dict = {op["display_name"]: op["username"] for op in operators}

        with st.form("create_task_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("ชื่องาน / หัวข้อโปรเจกต์ *", placeholder="เช่น ตรวจสอบสต็อกสินค้า, สรุปยอดรายรับ")
                task_type = st.selectbox("ประเภทงาน", ["Project", "Routine (งานประจำ)"])
                priority = st.selectbox("ระดับความเร่งด่วน", ["Normal", "High", "Urgent"])
            with c2:
                due_date = st.date_input("กำหนดวันส่งงาน (Due Date) *", value=datetime.today() + timedelta(days=7))
                selected_ops = st.multiselect(
                    "ระบุตัวผู้ปฏิบัติงาน (เลือกได้มากกว่า 1 คน) *",
                    options=list(op_dict.keys()),
                    help="เลือกพนักงานที่มียศปฏิบัติงานที่ต้องการมอบหมาย"
                )
                attachment = st.text_input("ลิงก์ไฟล์แนบ / Google Drive (ถ้ามี)", placeholder="https://...")

            description = st.text_area("รายละเอียดงาน / ขอบเขตงาน (Scope of Work) *", placeholder="ระบุสิ่งที่พนักงานต้องทำอย่างละเอียด ข้อมูลนี้จะแสดงบนกระดานงานอัตโนมัติ")
            submitted = st.form_submit_button("🚀 บันทึกและส่งงานไปยังกระดาน", type="primary", use_container_width=True)

            if submitted:
                if not title or not description or not selected_ops:
                    st.error("กรุณากรอกข้อมูลที่จำเป็น (*) และเลือกผู้ปฏิบัติงานอย่างน้อย 1 คน")
                else:
                    assigned_usernames = [op_dict[op] for op in selected_ops]
                    assignees_str = ", ".join(assigned_usernames)
                    clean_task_type = "Routine" if "Routine" in task_type else "Project"
                    
                    new_task = {
                        "title": title.strip(),
                        "description": description.strip(),
                        "task_type": clean_task_type,
                        "status": "To Do",
                        "priority": priority,
                        "due_date": due_date.strftime('%Y-%m-%d'),
                        "assignee_name": assignees_str,
                        "assignees": assignees_str,
                        "creator_username": curr_user.get("username"),
                        "requester_name": curr_user.get("fullname") or curr_user.get("username"),
                        "requester_dept": "ระดับสั่งการ",
                        "attachment_url": attachment.strip() if attachment else None,
                        "handover_status": "None"
                    }
                    try:
                        res = supabase.table("tasks").insert(new_task).execute()
                        if res.data:
                            task_id = res.data[0].get("task_id")
                            log_task_action(
                                task_id=task_id,
                                action="สร้างงานใหม่",
                                performed_by=curr_user.get("username"),
                                details=f"ผู้สั่งการ @{curr_user.get('username')} มอบหมายงานให้: {assignees_str}"
                            )
                        st.success("✅ บันทึกงานเรียบร้อยแล้ว! งานถูกส่งไปแสดงบนกระดานงานโมดูลที่ 2")
                    except Exception as e:
                        st.error(f"ไม่สามารถบันทึกงานได้: {e}")

    with sub_m2:
        st.subheader("อนุมัติคำขอส่งต่องานระหว่างพนักงาน")
        tasks_df = fetch_tasks()
        if not tasks_df.empty and "handover_status" in tasks_df.columns:
            pending_handovers = tasks_df[tasks_df["handover_status"] == "Pending"]
            if curr_user.get("role") != "Admin" and "creator_username" in pending_handovers.columns:
                pending_handovers = pending_handovers[pending_handovers["creator_username"] == curr_user.get("username")]

            if pending_handovers.empty:
                st.info("ไม่มีรายการคำขอส่งต่องานที่รอการอนุมัติในขณะนี้")
            else:
                for _, row in pending_handovers.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="stat-box" style="border-left: 5px solid #ea580c;">
                            <span class="badge-pill badge-blue">งาน: {row['title']}</span>
                            <h4 style="margin: 8px 0; color: #1e293b;">คำขอส่งต่องาน</h4>
                            <p><strong>ผู้รับผิดชอบเดิม:</strong> {row.get('assignee_name') or '-'}</p>
                            <p><strong>ต้องการส่งต่อให้:</strong> <span style="color:#ea580c; font-weight:bold;">{row.get('handover_to') or '-'}</span></p>
                            <p><strong>เหตุผล:</strong> {row.get('handover_reason') or 'ไม่ได้ระบุ'}</p>
                            <small>📅 กำหนดส่ง: {row.get('due_date') or '-'}</small>
                        </div>
                        """, unsafe_allow_html=True)

                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ อนุมัติการส่งต่อ", key=f"appr_ho_{row['task_id']}", use_container_width=True, type="primary"):
                                new_assignee = row.get("handover_to")
                                supabase.table("tasks").update({
                                    "assignee_name": new_assignee,
                                    "assignees": new_assignee,
                                    "handover_status": "Approved"
                                }).eq("task_id", row["task_id"]).execute()
                                
                                log_task_action(
                                    task_id=row["task_id"],
                                    action="อนุมัติส่งต่องาน",
                                    performed_by=curr_user.get("username"),
                                    details=f"ผู้สั่งการอนุมัติให้ส่งงานต่อจาก {row.get('assignee_name')} ไปยัง {new_assignee}"
                                )
                                st.success(f"อนุมัติเปลี่ยนผู้รับผิดชอบเป็น {new_assignee} สำเร็จ!")
                                st.rerun()
                        with c2:
                            if st.button("❌ ปฏิเสธการส่งต่อ", key=f"rej_ho_{row['task_id']}", use_container_width=True):
                                supabase.table("tasks").update({
                                    "handover_status": "Rejected"
                                }).eq("task_id", row["task_id"]).execute()
                                
                                log_task_action(
                                    task_id=row["task_id"],
                                    action="ปฏิเสธส่งต่องาน",
                                    performed_by=curr_user.get("username"),
                                    details=f"ผู้สั่งการปฏิเสธคำขอส่งต่อ คงผู้รับผิดชอบเดิม {row.get('assignee_name')}"
                                )
                                st.warning("ปฏิเสธคำขอส่งต่องานแล้ว")
                                st.rerun()
                        st.divider()
        else:
            st.info("ยังไม่มีข้อมูลคำขอส่งต่องาน")

    with sub_m3:
        st.subheader("ตรวจรับงานที่ส่งมา & ประเมินความพึงพอใจสำหรับคำนวณ KPI")
        tasks_df = fetch_tasks()
        if not tasks_df.empty:
            review_tasks = tasks_df[tasks_df["status"] == "In Review"]
            if curr_user.get("role") != "Admin" and "creator_username" in review_tasks.columns:
                review_tasks = review_tasks[review_tasks["creator_username"] == curr_user.get("username")]

            if review_tasks.empty:
                st.info("ไม่มีงานที่รอการตรวจรับในขณะนี้ (สถานะ In Review ว่าง)")
            else:
                for _, row in review_tasks.iterrows():
                    with st.container():
                        is_ontime = row.get("is_ontime")
                        ontime_badge = "🟢 ส่งตรงเวลา" if is_ontime is True else ("🔴 ส่งเกินกำหนด" if is_ontime is False else "⚪ รอตรวจสอบวันส่ง")
                        
                        st.markdown(f"""
                        <div class="stat-box" style="border-left: 5px solid #8b5cf6;">
                            <h4 style="margin: 0 0 6px 0; color:#1e293b;">{row['title']}</h4>
                            <p><strong>ผู้รับผิดชอบงาน:</strong> {row.get('assignee_name') or '-'}</p>
                            <p><strong>รายละเอียดงาน:</strong> {row.get('description') or '-'}</p>
                            <p><strong>บันทึก/ลิงก์การส่งงาน:</strong> {row.get('submission_note') or row.get('attachment_url') or '-'}</p>
                            <p><strong>สถานะเวลาส่งงาน:</strong> {ontime_badge} (กำหนดส่ง: {row.get('due_date') or '-'})</p>
                        </div>
                        """, unsafe_allow_html=True)

                        col_rate, col_btn = st.columns([2, 1])
                        with col_rate:
                            rating = st.slider("⭐ ระดับความพึงพอใจในการส่งงาน (1 - 5 ดาว):", min_value=1, max_value=5, value=5, key=f"rate_{row['task_id']}")
                        
                        with col_btn:
                            st.write("")
                            if st.button("🏆 อนุมัติผ่านงาน (Done)", key=f"appr_done_{row['task_id']}", use_container_width=True, type="primary"):
                                if row.get("task_type") == "Routine":
                                    old_due = pd.to_datetime(row['due_date']) if row.get('due_date') else datetime.today()
                                    next_month_date = old_due + pd.DateOffset(months=1)
                                    next_due = next_month_date.strftime('%Y-%m-%d')
                                    
                                    supabase.table("tasks").update({
                                        "status": "To Do",
                                        "due_date": next_due,
                                        "satisfaction_rating": rating,
                                        "submission_note": None
                                    }).eq("task_id", row["task_id"]).execute()
                                    st.toast(f"🔄 งาน Routine ผ่านแล้ว และตั้งรอบถัดไปเป็นวันที่: {next_due}")
                                else:
                                    supabase.table("tasks").update({
                                        "status": "Done",
                                        "satisfaction_rating": rating
                                    }).eq("task_id", row["task_id"]).execute()
                                
                                log_task_action(
                                    task_id=row["task_id"],
                                    action="อนุมัติงานสำเร็จ",
                                    performed_by=curr_user.get("username"),
                                    details=f"ผู้สั่งการให้คะแนนความพึงพอใจ {rating}/5 ดาว และอนุมัติงานสำเร็จ"
                                )
                                st.success(f"อนุมัติงาน '{row['title']}' สำเร็จแล้ว!")
                                st.rerun()

                            if st.button("↩️ ส่งกลับไปแก้ไข (Revision)", key=f"rev_{row['task_id']}", use_container_width=True):
                                supabase.table("tasks").update({
                                    "status": "Revision"
                                }).eq("task_id", row["task_id"]).execute()
                                log_task_action(
                                    task_id=row["task_id"],
                                    action="ส่งกลับไปแก้ไข",
                                    performed_by=curr_user.get("username"),
                                    details="ผู้สั่งการแจ้งให้แก้ไขงานเพิ่มเติม"
                                )
                                st.warning("ส่งงานกลับไปสถานะ Revision เรียบร้อยแล้ว")
                                st.rerun()
                        st.divider()
        else:
            st.info("ยังไม่มีข้อมูลงานในระบบ")

    with sub_m4:
        st.subheader("แบบฟอร์มปรับคะแนน KPI พนักงาน (ความดีความชอบ / ความผิดพลาด)")
        operators = fetch_operators()
        op_list = [op["username"] for op in operators]
        
        if not op_list:
            st.warning("ไม่พบรายชื่อพนักงานที่มีสิทธิ์ปฏิบัติงานในระบบ")
        else:
            with st.form("kpi_adjust_form", clear_on_submit=True):
                ca1, ca2 = st.columns(2)
                with ca1:
                    adj_user = st.selectbox("เลือกพนักงานผู้ปฏิบัติงาน:", op_list)
                    adj_type = st.radio("ประเภทการปรับคะแนน:", ["ความดีความชอบ (เพิ่มคะแนน +)", "ความผิดพลาด (หักคะแนน -)"])
                with ca2:
                    points = st.number_input("จำนวนคะแนนที่ปรับ:", min_value=1.0, max_value=50.0, value=5.0, step=1.0)
                    reason = st.text_area("รายละเอียด / เหตุผลในการปรับคะแนน *", placeholder="เช่น มีผลงานดีเยี่ยม หรือ ปฏิบัติงานผิดพลาด")

                adj_submit = st.form_submit_button("⚖️ บันทึกการปรับคะแนน KPI", use_container_width=True, type="primary")
                if adj_submit:
                    if not reason:
                        st.error("กรุณาระบุรายละเอียดเหตุผล")
                    else:
                        calc_points = points if "ความดีความชอบ" in adj_type else -points
                        clean_type = "ความดีความชอบ" if "ความดีความชอบ" in adj_type else "ความผิดพลาด"
                        try:
                            supabase.table("kpi_adjustments").insert({
                                "username": adj_user,
                                "points": calc_points,
                                "reason_type": clean_type,
                                "description": reason.strip(),
                                "created_by": curr_user.get("username")
                            }).execute()
                            st.success(f"✅ บันทึกการปรับคะแนนให้ @{adj_user} จำนวน {calc_points:+} คะแนน เรียบร้อยแล้ว!")
                        except Exception as e:
                            st.error(f"ไม่สามารถบันทึกคะแนนได้: {e}")

# --- Module 2: กระดานงาน (Kanban & Showcase Board - Image 1 Style) ---

def show_module2_kanban_page():
    curr_user = st.session_state.user
    curr_username = curr_user.get("username")
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")

    # Header section
    st.markdown("""
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #991b1b; font-weight: 700; margin-bottom: 0.2rem;">📋 โมดูลที่ 2: กระดานงาน (Task Showcase & Kanban Board)</h2>
            <p style="color: #64748b;">ติดตามสถานะงาน คัดกรองตัวงานตามผู้รับผิดชอบและวันส่ง พร้อมส่งงานและขอส่งต่องาน</p>
        </div>
    """, unsafe_allow_html=True)

    df = fetch_tasks()

    # --- แจ้งเตือนงานใหม่ & งานใกล้ครบกำหนดส่ง ---
    if not df.empty and "due_date" in df.columns:
        today_dt = datetime.today().date()
        if "assignee_name" in df.columns:
            my_new = df[(df["assignee_name"].fillna("").str.contains(curr_username)) & (df["status"] == "To Do")]
            if not my_new.empty:
                st.info(f"🔔 **งานใหม่มอบหมายถึงคุณ:** มีงานรอเริ่มดำเนินการทั้งหมด **{len(my_new)} งาน** ในช่อง To Do")

        warning_tasks = []
        overdue_tasks = []
        for _, row in df.iterrows():
            if row.get("status") != "Done" and row.get("due_date"):
                try:
                    due_dt = pd.to_datetime(row["due_date"]).date()
                    diff = (due_dt - today_dt).days
                    if diff < 0:
                        overdue_tasks.append(f"**{row['title']}** ({abs(diff)} วัน)")
                    elif diff <= 3:
                        warning_tasks.append(f"**{row['title']}** (เหลือ {diff} วัน)")
                except Exception:
                    pass

        if overdue_tasks:
            st.error(f"🚨 **งานเกินกำหนดส่ง (Overdue):** {', '.join(overdue_tasks[:3])}")
        if warning_tasks:
            st.warning(f"⚠️ **เตือนล่วงหน้า 3 วัน:** {', '.join(warning_tasks[:3])}")

    # --- ตัวกรองสไตล์ภาพที่ 1 (The Booking / Filter Bar) ---
    st.markdown('<div class="booking-filter-bar">', unsafe_allow_html=True)
    st.markdown("<h5 style='color: #991b1b; margin-top:0; margin-bottom: 12px;'>🔍 ค้นหาและกรองตัวงาน (Filter Bar)</h5>", unsafe_allow_html=True)
    
    operators = fetch_operators()
    assignee_options = ["ทั้งหมด"] + [op["username"] for op in operators]
    status_options = ["ทั้งหมด", "To Do", "In Progress", "In Review", "Revision", "Done"]
    type_options = ["ทั้งหมด", "Project", "Routine"]

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        filter_assignee = st.selectbox("👤 ผู้รับผิดชอบ (Assignee)", assignee_options, key="f_assignee")
    with f_col2:
        filter_date = st.date_input("📅 วันที่กำหนดส่ง (จากปฏิทิน)", value=None, key="f_date")
    with f_col3:
        filter_status = st.selectbox("📌 สถานะงาน (Status)", status_options, key="f_status")
    with f_col4:
        filter_type = st.selectbox("🏷️ ประเภทงาน (Type)", type_options, key="f_type")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # กรองข้อมูล
    filtered_df = df.copy() if not df.empty else pd.DataFrame()
    if not filtered_df.empty:
        if filter_assignee != "ทั้งหมด" and "assignee_name" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["assignee_name"].fillna("").str.contains(filter_assignee)]
        if filter_date is not None and "due_date" in filtered_df.columns:
            target_str = filter_date.strftime("%Y-%m-%d")
            filtered_df = filtered_df[filtered_df["due_date"] == target_str]
        if filter_status != "ทั้งหมด" and "status" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["status"] == filter_status]
        if filter_type != "ทั้งหมด" and "task_type" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["task_type"] == filter_type]

    # สลับมุมมอง: การ์ด Showcase (ภาพที่ 1) vs กระดาน Kanban
    view_mode = st.radio("รูปแบบการแสดงผล:", ["🗂️ มุมมองการ์ดพรีเมียม (Showcase Grid)", "📊 มุมมองกระดานแบ่งช่อง (Kanban Columns)"], horizontal=True)

    if filtered_df.empty:
        st.info("ไม่พบรายการงานที่ตรงตามเงื่อนไขตัวกรอง")
        return

    # 1. มุมมองการ์ด Showcase (เหมือนภาพที่ 1 "Our Elite Fleet")
    if view_mode == "🗂️ มุมมองการ์ดพรีเมียม (Showcase Grid)":
        st.markdown(f"##### 🚗 รายการตัวงานที่แสดงผล ({len(filtered_df)} รายการ)")
        
        # จัดเรียงเป็นการ์ด Grid 3 คอลัมน์
        cols_per_row = 3
        rows = [filtered_df.iloc[i:i + cols_per_row] for i in range(0, len(filtered_df), cols_per_row)]
        
        for row_batch in rows:
            grid_cols = st.columns(cols_per_row)
            for col_idx, (_, row) in enumerate(row_batch.iterrows()):
                with grid_cols[col_idx]:
                    status = row.get("status", "To Do")
                    due_date_val = row.get("due_date")
                    
                    # คลาสเตือน
                    card_class = "showcase-card"
                    alert_badge = ""
                    if status == "Done":
                        card_class += " showcase-card-done"
                        alert_badge = '<span class="badge-pill badge-green">✅ เสร็จสิ้น</span>'
                    elif due_date_val:
                        try:
                            due_dt = pd.to_datetime(due_date_val).date()
                            diff = (due_dt - datetime.today().date()).days
                            if diff < 0:
                                card_class += " showcase-card-overdue"
                                alert_badge = f'<span class="badge-pill badge-red">🚨 เกิน {abs(diff)} วัน</span>'
                            elif diff <= 3:
                                card_class += " showcase-card-warning"
                                alert_badge = f'<span class="badge-pill badge-gold">⚠️ เหลือ {diff} วัน</span>'
                        except Exception:
                            pass

                    type_badge = f'<span class="badge-pill badge-blue">{row.get("task_type", "Task")}</span>'
                    urg_badge = f'<span class="badge-pill badge-red">🔥 {row.get("priority")}</span>' if row.get("priority") == "Urgent" else ""
                    handover_badge = '<span class="badge-pill badge-purple">🔄 ขอส่งต่อ</span>' if row.get("handover_status") == "Pending" else ""

                    st.markdown(f"""
                        <div class="{card_class}">
                            <div>
                                {type_badge} {urg_badge} {alert_badge} {handover_badge}
                                <div class="showcase-title">{row.get('title', 'ไม่มีชื่อ')}</div>
                                <p style="color:#64748b; font-size:0.85rem; margin-bottom:8px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
                                    {row.get('description') or 'ไม่มีรายละเอียดงาน'}
                                </p>
                            </div>
                            <div style="border-top: 1px solid #fee2e2; padding-top: 10px; margin-top: 10px;">
                                <small style="color: #64748b;">👑 <strong>ผู้สั่งการ:</strong> @{row.get('creator_username') or '-'}</small><br/>
                                <small style="color: #64748b;">👥 <strong>ผู้ปฏิบัติ:</strong> {row.get('assignee_name') or '-'}</small><br/>
                                <small style="color: #64748b;">📅 <strong>กำหนดส่ง:</strong> <span style="font-weight:600; color:#991b1b;">{row.get('due_date') or '-'}</span></small><br/>
                                <small style="color: #64748b;">📌 <strong>สถานะ:</strong> <b>{status}</b></small>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Popover การจัดการงาน
                    with st.popover(f"⚙️ จัดการงาน: {row.get('title')[:15]}...", use_container_width=True):
                        st.markdown(f"**ชื่องาน:** {row.get('title')}")
                        st.markdown(f"**รายละเอียด:** {row.get('description') or '-'}")
                        if row.get('attachment_url'):
                            st.markdown(f"📎 [คลิกเปิดดูไฟล์แนบ]({row['attachment_url']})")

                        # ประวัติงาน
                        logs = fetch_task_logs(row['task_id'])
                        if logs:
                            st.caption("📜 **ประวัติงานล่าสุด:**")
                            for l in logs[:2]:
                                st.caption(f"• {l.get('created_at', '')[:10]}: {l.get('action')} โดย @{l.get('performed_by')}")

                        st.divider()

                        # ส่งงาน
                        if status in ['To Do', 'Revision']:
                            if st.button("🚀 เริ่มงาน (In Progress)", key=f"sc_start_{row['task_id']}", use_container_width=True):
                                supabase.table("tasks").update({"status": "In Progress"}).eq("task_id", row["task_id"]).execute()
                                log_task_action(row["task_id"], "เริ่มดำเนินงาน", curr_username, "เปลี่ยนสถานะเป็น In Progress")
                                st.rerun()

                        if status == 'In Progress':
                            sub_note = st.text_input("ลิงก์ส่งงาน / หมายเหตุ:", key=f"sc_note_{row['task_id']}")
                            if st.button("✅ ส่งงานเพื่อรออนุมัติ", key=f"sc_sub_{row['task_id']}", use_container_width=True, type="primary"):
                                is_ontime = True
                                if row.get("due_date"):
                                    try:
                                        if datetime.today().date() > pd.to_datetime(row['due_date']).date():
                                            is_ontime = False
                                    except Exception:
                                        pass
                                supabase.table("tasks").update({
                                    "status": "In Review",
                                    "submission_note": sub_note,
                                    "completed_at": datetime.now().isoformat(),
                                    "is_ontime": is_ontime
                                }).eq("task_id", row["task_id"]).execute()
                                log_task_action(row["task_id"], "ส่งงานเพื่อรออนุมัติ", curr_username, f"ผล: {'ตรงเวลา' if is_ontime else 'ล่าช้า'}")
                                st.success("ส่งงานสำเร็จ!")
                                st.rerun()

                        # ขอส่งงานต่อ
                        if status not in ['Done', 'In Review']:
                            with st.expander("🤝 ขอส่งงานต่อให้ผู้อื่น"):
                                target_op = st.selectbox("เลือกผู้รับต่อ:", [op["username"] for op in operators if op["username"] != curr_username], key=f"sc_hoto_{row['task_id']}")
                                ho_rs = st.text_area("เหตุผล:", key=f"sc_hors_{row['task_id']}")
                                if st.button("ส่งคำขอ", key=f"sc_hobtn_{row['task_id']}"):
                                    if ho_rs:
                                        supabase.table("tasks").update({
                                            "handover_to": target_op,
                                            "handover_reason": ho_rs,
                                            "handover_status": "Pending"
                                        }).eq("task_id", row["task_id"]).execute()
                                        log_task_action(row["task_id"], "ขอส่งงานต่อ", curr_username, f"ขอส่งให้ @{target_op}")
                                        st.success("ส่งคำขอแล้ว รอผู้สั่งการอนุมัติ!")
                                        st.rerun()

                        # ผู้สั่งการย้ายโดยตรง
                        if is_commander:
                            st.divider()
                            st.caption("สิทธิ์ผู้สั่งการ: เปลี่ยนสถานะโดยตรง")
                            all_stats = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
                            new_s = st.selectbox("ย้ายไปที่:", all_stats, index=all_stats.index(status), key=f"sc_sel_{row['task_id']}")
                            if st.button("อัปเดตสถานะ", key=f"sc_upd_{row['task_id']}"):
                                supabase.table("tasks").update({"status": new_s}).eq("task_id", row["task_id"]).execute()
                                st.rerun()

    # 2. มุมมองกระดานแบ่งช่อง (Kanban Columns)
    else:
        statuses = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
        cols = st.columns(len(statuses))
        for idx, status in enumerate(statuses):
            with cols[idx]:
                col_df = filtered_df[filtered_df['status'] == status] if 'status' in filtered_df.columns else pd.DataFrame()
                st.markdown(f"#### {status} ({len(col_df)})")
                for _, row in col_df.iterrows():
                    st.markdown(f"""
                        <div class="stat-box" style="padding: 12px; margin-bottom: 8px;">
                            <span class="badge-pill badge-blue" style="font-size:0.65rem;">{row.get('task_type')}</span>
                            <div style="font-weight:700; font-size:0.95rem; margin: 4px 0;">{row.get('title')}</div>
                            <small>👤 {row.get('assignee_name') or '-'}</small><br/>
                            <small>📅 {row.get('due_date') or '-'}</small>
                        </div>
                    """, unsafe_allow_html=True)

# --- Module 3: แดชบอร์ดคะแนน KPI & รายงานผลงานย้อนหลัง (Image 2 Style) ---

def show_module3_kpi_dashboard():
    curr_user = st.session_state.user
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")

    # Header สไตล์ภาพที่ 2
    today_thai = datetime.today().strftime("%d ตุลาคม %Y")
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <div>
                <h2 style="color: #991b1b; font-weight: 700; margin: 0;">📊 แดชบอร์ด & รายงานผลงาน (KPI & Reports)</h2>
                <p style="color: #64748b; margin: 0; font-size: 0.95rem;">ข้อมูลประจำวัน: วันนี้ {today_thai} · สำนักงานใหญ่</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    all_users = fetch_all_users()
    operators = [u for u in all_users if "ปฏิบัติงาน" in parse_roles(u.get("roles"))]
    tasks_df = fetch_tasks()
    adjustments = fetch_kpi_adjustments()

    # --- แถวสรุปตัวเลขสถิติ (Stat Summary Cards แบบภาพที่ 2) ---
    total_tasks_count = len(tasks_df) if not tasks_df.empty else 0
    done_count = len(tasks_df[tasks_df["status"] == "Done"]) if not tasks_df.empty and "status" in tasks_df.columns else 0
    prog_count = len(tasks_df[tasks_df["status"] == "In Progress"]) if not tasks_df.empty and "status" in tasks_df.columns else 0
    review_count = len(tasks_df[tasks_df["status"] == "In Review"]) if not tasks_df.empty and "status" in tasks_df.columns else 0
    
    # งานที่เกินกำหนดส่ง
    overdue_count = 0
    if not tasks_df.empty and "due_date" in tasks_df.columns:
        for _, t in tasks_df.iterrows():
            if t.get("status") != "Done" and t.get("due_date"):
                try:
                    if pd.to_datetime(t["due_date"]).date() < datetime.today().date():
                        overdue_count += 1
                except Exception:
                    pass

    st1, st2, st3, st4, st5, st6 = st.columns(6)
    with st1:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="stat-dot" style="background:#b91c1c;"></span>งานทั้งหมด</div>
                <div class="stat-number">{total_tasks_count} <span style="font-size:1rem; font-weight:normal; color:#64748b;">งาน</span></div>
                <div class="stat-sub">ในระบบทั้งหมด</div>
            </div>
        """, unsafe_allow_html=True)
    with st2:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="stat-dot" style="background:#10b981;"></span>งานสำเร็จแล้ว</div>
                <div class="stat-number" style="color:#10b981;">{done_count} <span style="font-size:1rem; font-weight:normal; color:#64748b;">งาน</span></div>
                <div class="stat-sub">{'100' if total_tasks_count == 0 else round(done_count/total_tasks_count*100)}% ของงานทั้งหมด</div>
            </div>
        """, unsafe_allow_html=True)
    with st3:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="stat-dot" style="background:#3b82f6;"></span>กำลังดำเนินการ</div>
                <div class="stat-number" style="color:#3b82f6;">{prog_count} <span style="font-size:1rem; font-weight:normal; color:#64748b;">งาน</span></div>
                <div class="stat-sub">สถานะ In Progress</div>
            </div>
        """, unsafe_allow_html=True)
    with st4:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="stat-dot" style="background:#f59e0b;"></span>รอการอนุมัติ</div>
                <div class="stat-number" style="color:#f59e0b;">{review_count} <span style="font-size:1rem; font-weight:normal; color:#64748b;">งาน</span></div>
                <div class="stat-sub">สถานะ In Review</div>
            </div>
        """, unsafe_allow_html=True)
    with st5:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="stat-dot" style="background:#ef4444;"></span>งานเกินกำหนด</div>
                <div class="stat-number" style="color:#ef4444;">{overdue_count} <span style="font-size:1rem; font-weight:normal; color:#64748b;">งาน</span></div>
                <div class="stat-sub">ต้องรีบติดตาม</div>
            </div>
        """, unsafe_allow_html=True)
    with st6:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label"><span class="stat-dot" style="background:#8b5cf6;"></span>พนักงานปฏิบัติ</div>
                <div class="stat-number" style="color:#8b5cf6;">{len(operators)} <span style="font-size:1rem; font-weight:normal; color:#64748b;">คน</span></div>
                <div class="stat-sub">ผู้มีสิทธิ์คำนวณ KPI</div>
            </div>
        """, unsafe_allow_html=True)

    # --- การประมวลผลคะแนน KPI รายบุคคล ---
    kpi_records = []
    for op in operators:
        uname = op.get("username")
        fullname = op.get("fullname") or uname
        
        user_tasks = tasks_df[tasks_df["assignee_name"].fillna("").str.contains(uname)] if not tasks_df.empty and "assignee_name" in tasks_df.columns else pd.DataFrame()
        total_t = len(user_tasks)
        done_t = len(user_tasks[user_tasks["status"] == "Done"]) if not user_tasks.empty else 0
        
        ontime_c = 0
        late_c = 0
        satisfactions = []
        if not user_tasks.empty:
            for _, t in user_tasks.iterrows():
                if t.get("status") == "Done":
                    if t.get("is_ontime") is True:
                        ontime_c += 1
                    elif t.get("is_ontime") is False:
                        late_c += 1
                    rating = t.get("satisfaction_rating")
                    if rating and rating > 0:
                        satisfactions.append(rating)

        avg_sat = sum(satisfactions) / len(satisfactions) if satisfactions else 5.0
        user_adjs = [a for a in adjustments if a.get("username") == uname]
        manual_p = sum(float(a.get("points", 0)) for a in user_adjs)
        
        total_kpi = max(0, round((done_t * 5) + (ontime_c * 10) - (late_c * 5) + (avg_sat * 4) + manual_p, 1))

        kpi_records.append({
            "username": uname,
            "fullname": fullname,
            "total_tasks": total_t,
            "done_tasks": done_t,
            "ontime_count": ontime_c,
            "late_count": late_c,
            "avg_rating": round(avg_sat, 1),
            "manual_points": manual_p,
            "total_kpi": total_kpi
        })

    kpi_df = pd.DataFrame(kpi_records)
    if not kpi_df.empty:
        kpi_df = kpi_df.sort_values(by="total_kpi", ascending=False).reset_index(drop=True)

    # --- แท็บย่อย: 1. สรุปแดชบอร์ด KPI  |  2. รายงานผลงานย้อนหลัง ---
    tab_overview, tab_history = st.tabs([
        "📈 สรุปแดชบอร์ดคะแนน KPI (Dashboard Overview)", 
        "📜 รายงานผลงานเก่า & เรียกดูย้อนหลัง (Historical Work Report)"
    ])

    # 1. แดชบอร์ดภาพรวม (สไตล์ภาพที่ 2 แบบแบ่งซ้าย-ขวา)
    with tab_overview:
        c_left, c_right = st.columns([2, 1])

        with c_left:
            st.subheader("📋 ตารางคะแนน KPI และประสิทธิภาพรายบุคคล")
            if not kpi_df.empty:
                display_kpi = kpi_df.rename(columns={
                    "fullname": "ชื่อ-สกุล",
                    "username": "Username",
                    "total_tasks": "งานทั้งหมด",
                    "done_tasks": "สำเร็จ",
                    "ontime_count": "ตรงเวลา",
                    "late_count": "ส่งช้า",
                    "avg_rating": "ดาวเฉลี่ย ⭐",
                    "manual_points": "แต้มพิเศษ",
                    "total_kpi": "คะแนน KPI รวม"
                })
                st.dataframe(display_kpi, use_container_width=True, hide_index=True)

                fig_bar = px.bar(
                    kpi_df, 
                    x="fullname", 
                    y="total_kpi", 
                    text="total_kpi",
                    labels={"fullname": "พนักงาน", "total_kpi": "คะแนน KPI รวม"},
                    color="total_kpi",
                    color_continuous_scale="Reds"
                )
                fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_bar, use_container_width=True)

        with c_right:
            # Widget สรุปงานครบกำหนดเร็วๆ นี้ (คล้ายกล่อง "รถคืนวันนี้" ในภาพที่ 2)
            st.markdown("""
                <div class="stat-box" style="margin-bottom: 16px;">
                    <h4 style="margin: 0 0 10px 0; color: #991b1b;">⏱️ งานครบกำหนดส่งเร็วๆ นี้ (ใน 3 วัน)</h4>
            """, unsafe_allow_html=True)
            
            near_due_tasks = []
            if not tasks_df.empty and "due_date" in tasks_df.columns:
                for _, t in tasks_df.iterrows():
                    if t.get("status") != "Done" and t.get("due_date"):
                        try:
                            diff = (pd.to_datetime(t["due_date"]).date() - datetime.today().date()).days
                            if 0 <= diff <= 3:
                                near_due_tasks.append((t, diff))
                        except Exception:
                            pass

            if not near_due_tasks:
                st.markdown("<p style='color:#64748b; font-size:0.9rem;'>ไม่มีงานครบกำหนดส่งใน 3 วันนี้</p>", unsafe_allow_html=True)
            else:
                for t, diff in near_due_tasks[:5]:
                    st.markdown(f"""
                        <div style="border-bottom: 1px solid #fee2e2; padding: 8px 0;">
                            <strong>{t['title']}</strong><br/>
                            <small style="color:#64748b;">👤 {t.get('assignee_name') or '-'} | 📅 กำหนดส่ง: {t.get('due_date')}</small><br/>
                            <span class="badge-pill badge-gold">เหลือ {diff} วัน</span>
                        </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # เครื่องมือปรับคะแนน KPI โดยตรงสำหรับผู้มียศสั่งการ
            if is_commander:
                with st.expander("⚙️ ปรับคะแนน KPI โดยตรง"):
                    with st.form("direct_adj"):
                        t_emp = st.selectbox("เลือกพนักงาน:", [op.get("username") for op in operators])
                        t_pts = st.number_input("คะแนน (+/-):", value=5.0, step=1.0)
                        t_rs = st.text_input("เหตุผล:")
                        if st.form_submit_button("บันทึกคะแนน"):
                            clean_t = "ความดีความชอบ" if t_pts >= 0 else "ความผิดพลาด"
                            supabase.table("kpi_adjustments").insert({
                                "username": t_emp,
                                "points": t_pts,
                                "reason_type": clean_t,
                                "description": t_rs,
                                "created_by": curr_user.get("username")
                            }).execute()
                            st.success("บันทึกคะแนนแล้ว!")
                            st.rerun()

    # 2. รายงานผลงานเก่า & เรียกดูย้อนหลัง (Historical Work Report)
    with tab_history:
        st.subheader("📜 รายงานประวัติผลงานเก่าและงานที่สำเร็จย้อนหลัง")
        st.caption("สามารถเลือกดูว่าพนักงานคนไหน สำเร็จงานอะไรไปแล้วบ้าง พร้อมรายละเอียดวันส่ง คะแนนประเมิน และแต้ม KPI ที่ได้")

        # ฟิลเตอร์ค้นหาประวัติย้อนหลัง
        c_h1, c_h2, c_h3 = st.columns(3)
        with c_h1:
            hist_emp = st.selectbox("👤 เลือกพนักงานที่ต้องการดูรายงาน:", ["ทุกคน (All Employees)"] + [op["username"] for op in operators], key="hist_emp")
        with c_h2:
            hist_status = st.selectbox("📌 สถานะผลงาน:", ["เฉพาะงานที่สำเร็จแล้ว (Done)", "งานทุกสถานะ"], key="hist_status")
        with c_h3:
            hist_type = st.selectbox("🏷️ ประเภทงาน:", ["ทั้งหมด", "Project", "Routine"], key="hist_type")

        # ประมวลผลงานย้อนหลัง
        report_df = tasks_df.copy() if not tasks_df.empty else pd.DataFrame()
        if not report_df.empty:
            if hist_status == "เฉพาะงานที่สำเร็จแล้ว (Done)":
                report_df = report_df[report_df["status"] == "Done"]
            if hist_emp != "ทุกคน (All Employees)":
                report_df = report_df[report_df["assignee_name"].fillna("").str.contains(hist_emp)]
            if hist_type != "ทั้งหมด":
                report_df = report_df[report_df["task_type"] == hist_type]

        if report_df.empty:
            st.info("ไม่มีประวัติผลงานที่ตรงตามเงื่อนไขที่เลือก")
        else:
            # คำนวณแต้มและสถานะสำหรับแต่ละงาน
            history_rows = []
            for _, r in report_df.iterrows():
                is_ot = r.get("is_ontime")
                ot_text = "🟢 ตรงเวลา (+10)" if is_ot is True else ("🔴 ล่าช้า (-5)" if is_ot is False else "⚪ ปกติ")
                rating = r.get("satisfaction_rating") or 0
                rating_str = f"⭐ {rating}/5" if rating > 0 else "-"
                
                # แต้มคำนวณเฉพาะงานนี้
                base_pt = 5 if r.get("status") == "Done" else 0
                time_pt = 10 if is_ot is True else (-5 if is_ot is False else 0)
                star_pt = rating * 4
                task_kpi = base_pt + time_pt + star_pt

                history_rows.append({
                    "ชื่องาน": r.get("title"),
                    "ผู้รับผิดชอบงาน": r.get("assignee_name") or "-",
                    "ผู้สั่งการ": r.get("creator_username") or r.get("requester_name") or "-",
                    "ประเภท": r.get("task_type"),
                    "กำหนดส่ง": r.get("due_date") or "-",
                    "วันที่ส่งงานจริง": str(r.get("completed_at") or "-")[:10],
                    "ผลการส่ง": ot_text,
                    "ความพึงพอใจ": rating_str,
                    "แต้ม KPI งานนี้": f"+{task_kpi}" if task_kpi >= 0 else str(task_kpi),
                    "สถานะปัจจุบัน": r.get("status"),
                    "ลิงก์/ผลงานที่ส่ง": r.get("submission_note") or r.get("attachment_url") or "-"
                })

            history_display_df = pd.DataFrame(history_rows)
            
            # สรุปด้านบนตาราง
            st.markdown(f"**พบรายการงานในรายงานทั้งหมด:** `{len(history_display_df)} งาน`")
            st.dataframe(history_display_df, use_container_width=True, hide_index=True)

            # ปุ่มดาวน์โหลด CSV
            csv_data = history_display_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดรายงานนี้เป็นไฟล์ CSV (Excel)",
                data=csv_data,
                file_name=f"kpi_work_report_{datetime.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="primary"
            )

# --- Admin Panel: จัดการผู้ใช้งานและโครงสร้างฐานข้อมูล ---

def show_admin_panel():
    curr_user = st.session_state.user
    if curr_user.get("role") != "Admin" and curr_user.get("username") != "admin":
        st.error("⛔ หน้านี้สำหรับผู้ดูแลระบบ (Admin) เท่านั้น")
        return

    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h2 style="color: #991b1b; font-weight: 700; margin-bottom: 0.2rem;">🛡️ แผงควบคุมผู้ดูแลระบบ (Admin Panel)</h2>
            <p style="color: #64748b;">อนุมัติผู้ใช้งานใหม่, กำหนดยศพนักงาน, และตรวจสอบโครงสร้างฐานข้อมูล</p>
        </div>
    """, unsafe_allow_html=True)

    tab_pend, tab_users = st.tabs([
        "⏳ คำขออนุมัติผู้ใช้ใหม่", 
        "👥 จัดการผู้ใช้งานทั้งหมด & ให้ยศ"
    ])

    all_users = fetch_all_users()

    with tab_pend:
        st.subheader("คำขอสมัครสมาชิกที่รอการอนุมัติ")
        pending_users = [u for u in all_users if u.get("is_approved") is False and u.get("role") != "Admin"]
        
        if not pending_users:
            st.success("✅ ไม่มีคำขอสมัครสมาชิกค้างอยู่ ทุกคนได้รับการอนุมัติแล้ว")
        else:
            for pu in pending_users:
                with st.container():
                    st.markdown(f"""
                    <div class="stat-box">
                        <strong>ชื่อ-สกุล:</strong> {pu.get('fullname') or '-'}<br/>
                        <strong>Username:</strong> @{pu.get('username')}<br/>
                        <strong>Email:</strong> {pu.get('email') or '-'}<br/>
                        <strong>เบอร์โทร:</strong> {pu.get('phone') or '-'}<br/>
                        <small>วันที่สมัคร: {pu.get('created_at', '')[:10]}</small>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns([2, 1])
                    with c1:
                        new_roles = st.multiselect(
                            f"กำหนดยศให้ @{pu.get('username')}:",
                            options=["ระดับสั่งการ", "ปฏิบัติงาน"],
                            default=["ปฏิบัติงาน"],
                            key=f"roles_assign_{pu['user_id']}"
                        )
                    with c2:
                        st.write("")
                        if st.button("✅ อนุมัติและเปิดใช้งาน", key=f"appr_btn_{pu['user_id']}", use_container_width=True, type="primary"):
                            roles_str = ", ".join(new_roles) if new_roles else "ปฏิบัติงาน"
                            try:
                                supabase.table("app_users").update({
                                    "is_approved": True,
                                    "roles": roles_str
                                }).eq("user_id", pu["user_id"]).execute()
                                st.success(f"อนุมัติ @{pu.get('username')} เรียบร้อยแล้ว!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"⚠️ บันทึกไม่สำเร็จ: {e}")
                        
                        if st.button("🗑️ ปฏิเสธ / ลบ", key=f"del_user_{pu['user_id']}", use_container_width=True):
                            supabase.table("app_users").delete().eq("user_id", pu["user_id"]).execute()
                            st.warning(f"ลบคำขอของ @{pu.get('username')} แล้ว")
                            st.rerun()
                    st.divider()

    with tab_users:
        st.subheader("รายชื่อผู้ใช้งานทั้งหมดในระบบ")
        for u in all_users:
            with st.expander(f"👤 {u.get('fullname') or u.get('username')} (@{u.get('username')})"):
                st.write(f"**Email:** {u.get('email') or '-'}")
                st.write(f"**เบอร์โทร:** {u.get('phone') or '-'}")
                st.write(f"**สถานะอนุมัติ:** {'อนุมัติแล้ว' if u.get('is_approved', True) else 'รออนุมัติ'}")
                
                curr_roles = parse_roles(u.get("roles"))
                edit_roles = st.multiselect(
                    "แก้ไขยศ (1 User มีได้มากกว่า 1 ยศ):",
                    options=["ระดับสั่งการ", "ปฏิบัติงาน"],
                    default=[r for r in curr_roles if r in ["ระดับสั่งการ", "ปฏิบัติงาน"]],
                    key=f"edit_roles_{u['user_id']}"
                )
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("บันทึกการแก้ไขยศ", key=f"save_roles_{u['user_id']}"):
                        try:
                            supabase.table("app_users").update({
                                "roles": ", ".join(edit_roles)
                            }).eq("user_id", u["user_id"]).execute()
                            st.success("บันทึกยศสำเร็จ!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ บันทึกไม่สำเร็จ: {e}")
                with b2:
                    if u.get("username") != "admin":
                        if st.button("ลบผู้ใช้นี้ออกจากระบบ", key=f"del_emp_{u['user_id']}"):
                            supabase.table("app_users").delete().eq("user_id", u["user_id"]).execute()
                            st.warning("ลบผู้ใช้สำเร็จ")
                            st.rerun()

# --- Main Application Controller ---

if not st.session_state.logged_in:
    show_auth_page()
else:
    curr_user = st.session_state.user
    curr_username = curr_user.get("username")
    curr_fullname = curr_user.get("fullname") or curr_username
    curr_roles = parse_roles(curr_user.get("roles"))
    is_admin = curr_user.get("role") == "Admin" or curr_username == "admin"
    
    # Sidebar
    st.sidebar.markdown(f"""
        <div style="background:#fff5f5; border:1px solid #fee2e2; border-radius:12px; padding:14px; margin-bottom:12px;">
            <h4 style="margin:0; color:#991b1b;">👤 {curr_fullname}</h4>
            <small style="color:#64748b;">@{curr_username}</small>
        </div>
    """, unsafe_allow_html=True)
    
    badge_html = ""
    if is_admin:
        badge_html += '<span class="badge-pill badge-red">🛡️ Admin</span> '
    for r in curr_roles:
        if r == "ระดับสั่งการ":
            badge_html += '<span class="badge-pill badge-gold">👑 สั่งการ</span> '
        elif r == "ปฏิบัติงาน":
            badge_html += '<span class="badge-pill badge-green">🛠️ ปฏิบัติงาน</span> '
    st.sidebar.markdown(badge_html, unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")
    
    # ลำดับเมนูที่จัดเรียงถูกต้อง 1, 2, 3 และ Admin
    menu_options = [
        "โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)",
        "โมดูลที่ 2: กระดานงาน (Kanban Board)", 
        "โมดูลที่ 3: แดชบอร์ดคะแนน KPI"
    ]
    if is_admin:
        menu_options.append("⚙️ ผู้ดูแลระบบ (Admin Panel)")

    default_idx = 0 if is_commander else 1
    page = st.sidebar.radio("📌 เลือกเมนูระบบ", menu_options, index=default_idx)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    # Routing
    if page == "โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)":
        show_module1_commander_page()
    elif page == "โมดูลที่ 2: กระดานงาน (Kanban Board)":
        show_module2_kanban_page()
    elif page == "โมดูลที่ 3: แดชบอร์ดคะแนน KPI":
        show_module3_kpi_dashboard()
    elif page == "⚙️ ผู้ดูแลระบบ (Admin Panel)":
        show_admin_panel()
