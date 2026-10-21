import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
from client import supabase

# --- Configuration & Theme Setup ---
st.set_page_config(
    page_title="Team Workflow & KPI Hub",
    page_icon="📋",
    layout="wide"
)

# Custom CSS for modern design and Sarabun font styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Sarabun', sans-serif;
    }
    
    .kanban-card {
        background-color: var(--background-color, #ffffff);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #3b82f6;
    }
    
    /* แจ้งเตือนสีแดง สำหรับงานเลยกำหนด */
    .kanban-card-overdue {
        border-left: 5px solid #ef4444 !important;
        background-color: #fef2f2 !important;
    }
    
    /* แจ้งเตือนสีเหลือง สำหรับงานใกล้ถึงกำหนดล่วงหน้า 3 วัน */
    .kanban-card-warning {
        border-left: 5px solid #f59e0b !important;
        background-color: #fffbeb !important;
    }
    
    /* แจ้งเตือนสีส้ม สำหรับงานที่กำลังรออนุมัติส่งต่อ */
    .kanban-card-handover {
        border-left: 5px solid #ea580c !important;
        background-color: #fff7ed !important;
    }

    .kanban-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 8px;
        margin-top: 6px;
        color: #1e293b;
    }

    .badge-project {
        background-color: #e0e7ff;
        color: #3730a3;
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-routine {
        background-color: #fef3c7;
        color: #92400e;
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-urgent {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 2px 7px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 700;
    }

    .badge-role-commander {
        background-color: #ede9fe;
        color: #5b21b6;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-role-operator {
        background-color: #ccfbf1;
        color: #115e59;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-role-admin {
        background-color: #ffe4e6;
        color: #9f1239;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    div[data-baseweb="button"] > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
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
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลผู้ใช้: {e}")
        return []

def fetch_operators():
    """ดึงรายชื่อพนักงานที่มีสิทธิ์ 'ปฏิบัติงาน' และได้รับการอนุมัติแล้ว"""
    users = fetch_all_users()
    operators = []
    for u in users:
        is_approved = u.get("is_approved", True)  # ถ้าคอลัมน์ยังไม่มี ให้ถือว่าผ่าน
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
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลงาน: {e}")
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
        pass  # หากตารางยังไม่ถูกสร้างให้ข้ามไปได้โดยไม่ error

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
    st.title("🛡️ ระบบจัดการงาน & ประเมินผล KPI (Workflow SVV)")
    st.markdown("กรุณาเข้าสู่ระบบ หรือสมัครสมาชิกรอการอนุมัติสิทธิ์เข้าใช้งาน")

    tab_login, tab_register, tab_reset = st.tabs([
        "🔒 เข้าสู่ระบบ (Login)", 
        "📝 สมัครสมาชิกใหม่ (Register)", 
        "🔑 ลืม / เปลี่ยนรหัสผ่าน (Reset Password)"
    ])

    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="kanban-card">', unsafe_allow_html=True)
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
                            # ตรวจสอบว่าได้รับการอนุมัติหรือไม่ (Admin ผ่านเสมอ)
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
            st.markdown('<div class="kanban-card">', unsafe_allow_html=True)
            st.subheader("สมัครสมาชิกพนักงานใหม่")
            st.caption("เมื่อสมัครเสร็จสิ้น บัญชีจะถูกส่งให้ Admin ตรวจสอบและให้ยศก่อนเข้าใช้")
            
            with st.form("register_form", clear_on_submit=True):
                reg_username = st.text_input("ชื่อผู้ใช้งาน (Username) *")
                reg_fullname = st.text_input("ชื่อ - นามสกุล (Full Name) *")
                reg_email = st.text_input("อีเมล (Email) *")
                reg_phone = st.text_input("เบอร์โทรศัพท์ (Phone Number) *")
                reg_pass1 = st.text_input("รหัสผ่าน (Password) *", type="password")
                reg_pass2 = st.text_input("ยืนยันรหัสผ่าน (Confirm Password) *", type="password")
                
                reg_submitted = st.form_submit_button("ส่งคำขอสมัครสมาชิก", use_container_width=True)
                
                if reg_submitted:
                    if not (reg_username and reg_fullname and reg_email and reg_phone and reg_pass1):
                        st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")
                    elif reg_pass1 != reg_pass2:
                        st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                    else:
                        # ตรวจสอบว่ามี username ซ้ำหรือไม่
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
            st.markdown('<div class="kanban-card">', unsafe_allow_html=True)
            st.subheader("แก้ไข / ตั้งรหัสผ่านใหม่")
            st.caption("กรอก Username และ Email หรือ เบอร์โทรศัพท์ ที่ลงทะเบียนไว้เพื่อยืนยันตัวตน")
            
            with st.form("reset_form"):
                rst_username = st.text_input("ชื่อผู้ใช้งาน (Username) *")
                rst_contact = st.text_input("Email หรือ เบอร์โทร ที่ลงทะเบียนไว้ *")
                rst_new_pass = st.text_input("รหัสผ่านใหม่ *", type="password")
                rst_confirm_pass = st.text_input("ยืนยันรหัสผ่านใหม่ *", type="password")
                rst_submitted = st.form_submit_button("บันทึกรหัสผ่านใหม่", use_container_width=True)
                
                if rst_submitted:
                    if not (rst_username and rst_contact and rst_new_pass):
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                    elif rst_new_pass != rst_confirm_pass:
                        st.error("รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน")
                    else:
                        # ค้นหาผู้ใช้จาก username
                        u_res = supabase.table("app_users").select("*").eq("username", rst_username.strip()).execute()
                        if not u_res.data:
                            st.error("ไม่พบบัญชีผู้ใช้นี้ในระบบ")
                        else:
                            u_data = u_res.data[0]
                            db_email = str(u_data.get("email") or "").strip().lower()
                            db_phone = str(u_data.get("phone") or "").strip()
                            input_contact = rst_contact.strip().lower()
                            
                            # ตรวจสอบ Email หรือ Phone
                            if input_contact == db_email or input_contact == db_phone:
                                supabase.table("app_users").update({
                                    "password_hash": rst_new_pass
                                }).eq("user_id", u_data["user_id"]).execute()
                                st.success("✅ แก้ไขรหัสผ่านสำเร็จแล้ว! สามารถนำรหัสใหม่ไปเข้าสู่ระบบได้ทันที")
                            else:
                                st.error("ข้อมูล Email หรือ เบอร์โทร ไม่ตรงกับในระบบ")
            st.markdown('</div>', unsafe_allow_html=True)

# --- Module 1: ระบบสั่งการและมอบหมายงาน (เฉพาะยศ 'ระดับสั่งการ') ---

def show_module1_commander_page():
    curr_user = st.session_state.user
    
    # ตรวจสอบสิทธิ์ยศระดับสั่งการ
    if not user_has_role(curr_user, "ระดับสั่งการ"):
        st.error("⛔ จำกัดสิทธิ์: โมดูลนี้อนุญาตให้เข้าใช้งานได้เฉพาะผู้มียศ **'ระดับสั่งการ'** เท่านั้น")
        st.info(f"ยศปัจจุบันของคุณ: {', '.join(parse_roles(curr_user.get('roles')))}")
        return

    st.header("🎯 โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander Hub)")
    st.caption("ระบบสำหรับผู้มียศระดับสั่งการ: มอบหมายงาน, อนุมัติการส่งต่อ, ตรวจรับประเมินผล KPI และปรับคะแนนพนักงาน")

    sub_m1, sub_m2, sub_m3, sub_m4 = st.tabs([
        "📝 มอบหมายงานใหม่", 
        "🔄 รายการรออนุมัติส่งต่องาน", 
        "⭐ ตรวจรับงาน & ประเมิน KPI", 
        "⚖️ ฟอร์มเพิ่ม/ลดคะแนน KPI"
    ])

    # 1. มอบหมายงานใหม่
    with sub_m1:
        st.subheader("สร้างและมอบหมายงานใหม่")
        operators = fetch_operators()
        op_dict = {op["display_name"]: op["username"] for op in operators}

        with st.form("create_task_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("ชื่องาน / หัวข้อโปรเจกต์ *", placeholder="เช่น ตรวจสอบสต็อกสินค้า, ทำสรุปรายรับ-รายจ่าย")
                task_type = st.selectbox("ประเภทงาน", ["Project", "Routine (งานประจำ)"])
                priority = st.selectbox("ระดับความเร่งด่วน", ["Normal", "High", "Urgent"])
            with c2:
                due_date = st.date_input("กำหนดวันส่งงาน (Due Date) *", value=datetime.today() + timedelta(days=7))
                
                # Dropdown เลือกผู้ปฏิบัติงาน (มากกว่า 1 คนได้)
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
                        st.success(f"✅ บันทึกงานเรียบร้อยแล้ว! งานถูกส่งไปแสดงบนกระดานงานโมดูลที่ 2 (สถานะ To Do)")
                    except Exception as e:
                        st.error(f"ไม่สามารถบันทึกงานได้: {e}")

    # 2. รายการรออนุมัติส่งต่องาน
    with sub_m2:
        st.subheader("อนุมัติคำขอส่งต่องานระหว่างพนักงาน")
        st.caption("เมื่อพนักงานในโมดูลที่ 2 ขอส่งงานต่อให้เพื่อนร่วมงาน ผู้สั่งการจะต้องเป็นผู้อนุมัติก่อนจึงจะมีผล")
        
        tasks_df = fetch_tasks()
        if not tasks_df.empty and "handover_status" in tasks_df.columns:
            # กรองเฉพาะงานที่ขอส่งต่อและรออนุมัติ
            pending_handovers = tasks_df[tasks_df["handover_status"] == "Pending"]
            
            # ถ้าไม่ใช่ Admin ให้เห็นเฉพาะงานที่ตัวเองสั่ง
            if curr_user.get("role") != "Admin" and "creator_username" in pending_handovers.columns:
                pending_handovers = pending_handovers[pending_handovers["creator_username"] == curr_user.get("username")]

            if pending_handovers.empty:
                st.info("ไม่มีรายการคำขอส่งต่องานที่รอการอนุมัติในขณะนี้")
            else:
                for _, row in pending_handovers.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="kanban-card kanban-card-handover">
                            <span class="badge-project">งาน: {row['title']}</span>
                            <div class="kanban-card-title">คำขอส่งต่องาน</div>
                            <p><strong>ผู้รับผิดชอบเดิม:</strong> {row.get('assignee_name') or '-'}</p>
                            <p><strong>ต้องการส่งต่อให้:</strong> <span style="color:#ea580c; font-weight:bold;">{row.get('handover_to') or '-'}</span></p>
                            <p><strong>เหตุผลในการส่งต่อ:</strong> {row.get('handover_reason') or 'ไม่ได้ระบุเหตุผล'}</p>
                            <small>📅 กำหนดส่งงาน: {row.get('due_date') or '-'}</small>
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

    # 3. ตรวจรับงาน & ประเมินความพึงพอใจ KPI
    with sub_m3:
        st.subheader("ตรวจรับงานที่ส่งมา & ประเมินความพึงพอใจสำหรับคำนวณ KPI")
        st.caption("พนักงานที่ส่งงานแล้ว สถานะจะอยู่ช่อง 'In Review' เพื่อรอการอนุมัติความสำเร็จจากผู้สั่งการ")

        tasks_df = fetch_tasks()
        if not tasks_df.empty:
            review_tasks = tasks_df[tasks_df["status"] == "In Review"]
            
            # ถ้าไม่ใช่ Admin ให้กรองเฉพาะงานที่ตัวเองสั่ง
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
                        <div class="kanban-card" style="border-left: 5px solid #8b5cf6;">
                            <div class="kanban-card-title">{row['title']}</div>
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
                                # ถ้าเป็น Routine ให้ตั้งรอบเดือนถัดไป
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
                                st.success(f"อนุมัติงาน '{row['title']}' สำเร็จแล้ว! คะแนนความพึงพอใจถูกส่งไปคำนวณ KPI ในโมดูลที่ 3")
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

    # 4. แบบฟอร์มเพิ่มหรือลดคะแนน KPI
    with sub_m4:
        st.subheader("แบบฟอร์มปรับคะแนน KPI พนักงาน (ความดีความชอบ / ความผิดพลาด)")
        st.caption("คะแนนส่วนนี้จะถูกนำไปคำนวณรวมในแดชบอร์ด KPI โมดูลที่ 3 โดยตรง")

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
                    reason = st.text_area("รายละเอียด / เหตุผลในการปรับคะแนน *", placeholder="เช่น ทำงานสำเร็จก่อนเวลาอย่างยอดเยี่ยม หรือ ส่งเอกสารผิดพลาดไม่ตรวจทาน")

                adj_submit = st.form_submit_button("⚖️ บันทึกการปรับคะแนน KPI", use_container_width=True)
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
                            st.error(f"ไม่สามารถบันทึกคะแนนได้ (กรุณาตรวจสอบว่ารันไฟล์ database_update.sql ใน Supabase หรือยัง): {e}")

# --- Module 2: กระดานงาน (Kanban Board & Task Tracking) ---

def show_module2_kanban_page():
    curr_user = st.session_state.user
    curr_username = curr_user.get("username")
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")

    st.header("📋 โมดูลที่ 2: กระดานงาน (Task Kanban Board)")
    st.caption("ทุกคนสามารถเข้าดูและอัปเดตงานได้ | การอนุมัติการแก้ไข/ส่งงาน/ส่งต่อ สงวนสิทธิ์เฉพาะผู้มียศสั่งการ")

    df = fetch_tasks()

    # --- ส่วนการแจ้งเตือนงานใหม่ & งานใกล้ครบกำหนดส่ง ---
    if not df.empty and "due_date" in df.columns:
        today_dt = datetime.today().date()
        
        # 1. แจ้งเตือนงานเข้าใหม่สำหรับผู้ใช้นี้
        if "assignee_name" in df.columns:
            my_new_tasks = df[
                (df["assignee_name"].fillna("").str.contains(curr_username)) & 
                (df["status"] == "To Do")
            ]
            if not my_new_tasks.empty:
                st.info(f"🔔 **แจ้งเตือนงานใหม่:** คุณมีงานที่รอเริ่มดำเนินการทั้งหมด **{len(my_new_tasks)} งาน** ในช่อง 'To Do'")

        # 2. แจ้งเตือนงานใกล้ครบกำหนด 3 วัน หรือ เลยกำหนด
        warning_tasks = []
        overdue_tasks = []
        for _, row in df.iterrows():
            if row.get("status") != "Done" and row.get("due_date"):
                try:
                    due_dt = pd.to_datetime(row["due_date"]).date()
                    diff = (due_dt - today_dt).days
                    if diff < 0:
                        overdue_tasks.append(f"**{row['title']}** (เกินกำหนด {abs(diff)} วัน)")
                    elif diff <= 3:
                        warning_tasks.append(f"**{row['title']}** (เหลืออีก {diff} วัน)")
                except Exception:
                    pass

        if overdue_tasks:
            st.error(f"🚨 **งานเลยกำหนดส่ง (Overdue):** {', '.join(overdue_tasks[:3])}{' และอื่นๆ...' if len(overdue_tasks) > 3 else ''}")
        if warning_tasks:
            st.warning(f"⚠️ **แจ้งเตือนใกล้ครบกำหนดส่งล่วงหน้า 3 วัน:** {', '.join(warning_tasks[:3])}{' และอื่นๆ...' if len(warning_tasks) > 3 else ''}")

    # --- Kanban Columns Display ---
    statuses = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
    cols = st.columns(len(statuses))

    for idx, status in enumerate(statuses):
        with cols[idx]:
            count = len(df[df['status'] == status]) if not df.empty and 'status' in df.columns else 0
            st.markdown(f"### {status} ({count})")
            
            if not df.empty and 'status' in df.columns:
                status_df = df[df['status'] == status]
                for _, row in status_df.iterrows():
                    badge_class = "badge-project" if row.get('task_type') == "Project" else "badge-routine"
                    urgent_badge = '<span class="badge-urgent">🔥 Urgent</span>' if row.get('priority') == 'Urgent' else ''
                    
                    # คำนวณวันกำหนดส่งและการแจ้งเตือน
                    alert_class = ""
                    alert_text = ""
                    days_diff = None
                    if status != 'Done' and row.get('due_date'):
                        try:
                            due_dt = pd.to_datetime(row['due_date']).date()
                            days_diff = (due_dt - datetime.today().date()).days
                            if days_diff < 0:
                                alert_class = "kanban-card-overdue"
                                alert_text = f'<br/><span style="color:#ef4444; font-size:0.75rem; font-weight:bold;">🚨 เกินกำหนด ({abs(days_diff)} วัน)</span>'
                            elif days_diff <= 3:
                                alert_class = "kanban-card-warning"
                                alert_text = f'<br/><span style="color:#d97706; font-size:0.75rem; font-weight:bold;">⚠️ ใกล้ครบกำหนด (เหลือ {days_diff} วัน)</span>'
                        except Exception:
                            pass
                    
                    # ตรวจสอบสถานะการส่งต่อ
                    handover_pending = row.get("handover_status") == "Pending"
                    if handover_pending:
                        alert_class = "kanban-card-handover"
                        alert_text += '<br/><span style="color:#ea580c; font-size:0.75rem; font-weight:bold;">🔄 มีคำขอส่งต่องาน (รออนุมัติ)</span>'

                    # การ์ดแสดงผล
                    creator = row.get("creator_username") or row.get("requester_name") or "-"
                    assignees = row.get("assignee_name") or row.get("assignees") or "-"
                    
                    st.markdown(f"""
                    <div class="kanban-card {alert_class}">
                        <span class="{badge_class}">{row.get('task_type', 'Task')}</span> {urgent_badge}
                        <div class="kanban-card-title">{row.get('title', 'ไม่มีชื่อ')}</div>
                        <small>👑 <strong>ผู้สั่งการ:</strong> @{creator}</small><br/>
                        <small>👥 <strong>ผู้ปฏิบัติ:</strong> {assignees}</small><br/>
                        <small>📅 <strong>กำหนดส่ง:</strong> {row.get('due_date') or '-'}</small>{alert_text}
                    </div>
                    """, unsafe_allow_html=True)

                    # เมนูจัดการภายในการ์ดงาน
                    with st.expander(f"🔍 รายละเอียด & จัดการงาน"):
                        st.markdown(f"**รายละเอียดงาน:**")
                        st.info(row.get('description') or 'ไม่มีรายละเอียด')
                        
                        if row.get('attachment_url'):
                            st.markdown(f"📎 [คลิกเปิดดูไฟล์แนบ]({row['attachment_url']})")

                        # แสดงประวัติการทำงาน (Audit Trail)
                        logs = fetch_task_logs(row['task_id'])
                        if logs:
                            st.markdown("📜 **ประวัติงานและการส่งต่อ:**")
                            for l in logs[:3]:
                                st.caption(f"• {l.get('created_at', '')[:16]} - **{l.get('action')}** โดย @{l.get('performed_by')}: {l.get('details')}")

                        st.divider()

                        # ฟังก์ชันการทำงานของพนักงาน
                        if status in ['To Do', 'Revision']:
                            if st.button("🚀 เริ่มดำเนินงาน (ย้ายไป In Progress)", key=f"start_{row['task_id']}", use_container_width=True):
                                supabase.table("tasks").update({"status": "In Progress"}).eq("task_id", row["task_id"]).execute()
                                log_task_action(row["task_id"], "เริ่มดำเนินงาน", curr_username, "เปลี่ยนสถานะเป็น In Progress")
                                st.rerun()

                        if status == 'In Progress':
                            st.markdown("##### 📤 ส่งงานเพื่อรอการอนุมัติ")
                            sub_note = st.text_input("ลิงก์งานที่ทำเสร็จ หรือ หมายเหตุการส่ง:", key=f"sub_note_{row['task_id']}")
                            if st.button("✅ ส่งงานเพื่อรออนุมัติ (Submit)", key=f"sub_btn_{row['task_id']}", use_container_width=True, type="primary"):
                                # คำนวณว่าทันกำหนดส่งหรือไม่
                                is_ontime = True
                                if row.get("due_date"):
                                    try:
                                        due_dt = pd.to_datetime(row['due_date']).date()
                                        if datetime.today().date() > due_dt:
                                            is_ontime = False
                                    except Exception:
                                        pass

                                supabase.table("tasks").update({
                                    "status": "In Review",
                                    "submission_note": sub_note,
                                    "completed_at": datetime.now().isoformat(),
                                    "is_ontime": is_ontime
                                }).eq("task_id", row["task_id"]).execute()

                                result_text = "ส่งตรงเวลา (+KPI)" if is_ontime else "ส่งล่าช้า (-KPI)"
                                log_task_action(
                                    row["task_id"], 
                                    "ส่งงานเพื่อรออนุมัติ", 
                                    curr_username, 
                                    f"พนักงานส่งงาน ({result_text}) หมายเหตุ: {sub_note}"
                                )
                                st.success("ส่งงานเรียบร้อยแล้ว งานถูกย้ายไปช่อง 'In Review' เพื่อรอผู้สั่งการอนุมัติ!")
                                st.rerun()

                        # ฟังก์ชันส่งงานต่อให้พนักงานคนอื่น
                        if status not in ['Done', 'In Review']:
                            with st.popover("🤝 ขอส่งงานต่อให้ผู้อื่น"):
                                st.markdown("ส่งงานต่อให้พนักงานคนอื่น (ต้องรอผู้สั่งการอนุมัติ)")
                                all_ops = fetch_operators()
                                target_op = st.selectbox("เลือกพนักงานปลายทาง:", [op["username"] for op in all_ops if op["username"] != curr_username], key=f"ho_to_{row['task_id']}")
                                ho_reason = st.text_area("เหตุผลในการส่งต่อ:", key=f"ho_rs_{row['task_id']}")
                                if st.button("ส่งคำขอส่งต่องาน", key=f"ho_btn_{row['task_id']}"):
                                    if not ho_reason:
                                        st.error("กรุณาระบุเหตุผล")
                                    else:
                                        supabase.table("tasks").update({
                                            "handover_to": target_op,
                                            "handover_reason": ho_reason,
                                            "handover_status": "Pending"
                                        }).eq("task_id", row["task_id"]).execute()
                                        log_task_action(
                                            row["task_id"],
                                            "ขอส่งงานต่อ",
                                            curr_username,
                                            f"ขอส่งต่อให้ @{target_op} เหตุผล: {ho_reason}"
                                        )
                                        st.success("ส่งคำขอเรียบร้อยแล้ว! กำลังรอผู้สั่งการอนุมัติในโมดูลที่ 1")
                                        st.rerun()

                        # สิทธิ์การแก้ไขโดยตรง (เฉพาะระดับสั่งการ)
                        if is_commander:
                            st.markdown("---")
                            st.caption("⚙️ สิทธิ์ระดับสั่งการ: ย้ายการ์ดโดยตรงหรือลบงาน")
                            new_stat = st.selectbox("ย้ายสถานะโดยตรง:", statuses, index=statuses.index(status), key=f"sel_{row['task_id']}")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("บันทึกสถานะ", key=f"upd_{row['task_id']}", use_container_width=True):
                                    supabase.table("tasks").update({"status": new_stat}).eq("task_id", row["task_id"]).execute()
                                    log_task_action(row["task_id"], "ย้ายสถานะโดยผู้สั่งการ", curr_username, f"ย้ายไป {new_stat}")
                                    st.rerun()
                            with c2:
                                if st.button("🗑️ ลบงาน", key=f"del_{row['task_id']}", use_container_width=True):
                                    supabase.table("tasks").delete().eq("task_id", row["task_id"]).execute()
                                    st.toast("ลบงานสำเร็จ")
                                    st.rerun()

# --- Module 3: แดชบอร์ดคะแนน KPI (KPI Dashboard) ---

def show_module3_kpi_dashboard():
    curr_user = st.session_state.user
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")

    st.header("📊 โมดูลที่ 3: แดชบอร์ดคะแนน KPI พนักงาน (KPI Dashboard)")
    st.caption("คำนวณจากปริมาณงาน, การส่งตรงเวลา/ล่าช้า, คะแนนประเมินความพึงพอใจ, และการปรับแต้มความดีความชอบ/ความผิดพลาด")

    # ดึงเฉพาะผู้ใช้งานที่มียศ 'ปฏิบัติงาน'
    all_users = fetch_all_users()
    operators = []
    for u in all_users:
        u_roles = parse_roles(u.get("roles"))
        if "ปฏิบัติงาน" in u_roles:
            operators.append(u)

    if not operators:
        st.warning("ยังไม่มีพนักงานที่มียศ 'ปฏิบัติงาน' ในระบบ")
        return

    # ดึงข้อมูลงานทั้งหมด
    tasks_df = fetch_tasks()
    adjustments = fetch_kpi_adjustments()

    # ประมวลผลคะแนน KPI ของพนักงานแต่ละคน
    kpi_records = []
    for op in operators:
        uname = op.get("username")
        fullname = op.get("fullname") or uname
        
        # ค้นหางานที่พนักงานคนนี้ได้รับมอบหมาย
        if not tasks_df.empty and "assignee_name" in tasks_df.columns:
            user_tasks = tasks_df[tasks_df["assignee_name"].fillna("").str.contains(uname)]
        else:
            user_tasks = pd.DataFrame()

        total_tasks = len(user_tasks)
        done_tasks = len(user_tasks[user_tasks["status"] == "Done"]) if not user_tasks.empty else 0
        
        # งานส่งทัน vs ส่งช้า
        ontime_count = 0
        late_count = 0
        satisfaction_scores = []

        if not user_tasks.empty:
            for _, t in user_tasks.iterrows():
                if t.get("status") == "Done":
                    if t.get("is_ontime") is True:
                        ontime_count += 1
                    elif t.get("is_ontime") is False:
                        late_count += 1
                    
                    rating = t.get("satisfaction_rating")
                    if rating and rating > 0:
                        satisfaction_scores.append(rating)

        avg_rating = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 5.0
        
        # คะแนนปรับแก้ความดีความชอบ / ความผิดพลาด
        user_adjs = [a for a in adjustments if a.get("username") == uname]
        manual_points = sum(float(a.get("points", 0)) for a in user_adjs)

        # สูตรคำนวณ KPI:
        # Base: งานสำเร็จ x 5 คะแนน
        # On-time: +10 คะแนนต่องาน
        # Late: -5 คะแนนต่องาน
        # Rating: เฉลี่ย x 4 คะแนน
        # Manual: บวกหรือลบตามที่สั่งการปรับ
        task_points = (done_tasks * 5) + (ontime_count * 10) - (late_count * 5)
        rating_points = avg_rating * 4
        total_kpi = max(0, round(task_points + rating_points + manual_points, 1))

        kpi_records.append({
            "username": uname,
            "fullname": fullname,
            "total_tasks": total_tasks,
            "done_tasks": done_tasks,
            "ontime_count": ontime_count,
            "late_count": late_count,
            "avg_rating": round(avg_rating, 1),
            "manual_points": manual_points,
            "total_kpi": total_kpi
        })

    kpi_df = pd.DataFrame(kpi_records)
    kpi_df = kpi_df.sort_values(by="total_kpi", ascending=False).reset_index(drop=True)

    # --- Top Metrics Banner ---
    m1, m2, m3, m4 = st.columns(4)
    if not kpi_df.empty:
        top_user = kpi_df.iloc[0]
        m1.metric("🏆 ผู้มีคะแนน KPI สูงสุด", f"{top_user['fullname']}", f"{top_user['total_kpi']} แต้ม")
        total_done = kpi_df["done_tasks"].sum()
        total_ontime = kpi_df["ontime_count"].sum()
        ontime_rate = round((total_ontime / total_done * 100), 1) if total_done > 0 else 100
        m2.metric("✅ งานที่เสร็จสิ้นทั้งหมด", f"{total_done} งาน")
        m3.metric("🎯 อัตราส่งตรงเวลา (On-time)", f"{ontime_rate}%")
        m4.metric("👥 พนักงานปฏิบัติงาน", f"{len(kpi_df)} คน")

    st.markdown("---")

    # --- Charts & Visualization ---
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("📈 อันดับคะแนน KPI รวม (Leaderboard)")
        fig_bar = px.bar(
            kpi_df, 
            x="fullname", 
            y="total_kpi", 
            text="total_kpi",
            labels={"fullname": "พนักงาน", "total_kpi": "คะแนน KPI รวม"},
            color="total_kpi",
            color_continuous_scale="Teal"
        )
        fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

    with c_right:
        st.subheader("⏱️ สัดส่วนงาน: ตรงเวลา vs ล่าช้า")
        fig_time = px.bar(
            kpi_df,
            x="fullname",
            y=["ontime_count", "late_count"],
            labels={"value": "จำนวนงาน", "fullname": "พนักงาน", "variable": "ประเภท"},
            barmode="group",
            color_discrete_map={"ontime_count": "#10b981", "late_count": "#ef4444"}
        )
        fig_time.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_time, use_container_width=True)

    # --- Data Table Breakdown ---
    st.subheader("📋 ตารางแจกแจงรายละเอียดคะแนน KPI รายบุคคล")
    display_df = kpi_df.rename(columns={
        "fullname": "ชื่อ-นามสกุล",
        "username": "Username",
        "total_tasks": "งานทั้งหมด",
        "done_tasks": "งานที่เสร็จ",
        "ontime_count": "ส่งทันเวลา",
        "late_count": "ส่งล่าช้า",
        "avg_rating": "ดาวเฉลี่ย ⭐",
        "manual_points": "แต้มพิเศษ/ปรับลด",
        "total_kpi": "คะแนน KPI รวม"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # --- สิทธิ์การแก้ไขคะแนน KPI (เฉพาะยศระดับสั่งการ) ---
    if is_commander:
        st.markdown("---")
        with st.expander("⚙️ เครื่องมือปรับคะแนน KPI โดยตรง (เฉพาะผู้มียศระดับสั่งการ)"):
            st.caption("ผู้มียศสั่งการสามารถเพิ่มหรือลดคะแนน KPI เพื่อแก้ไขคะแนนในระบบได้ทันที")
            with st.form("quick_adj_form"):
                eq1, eq2, eq3 = st.columns(3)
                with eq1:
                    target_emp = st.selectbox("เลือกพนักงาน:", [op.get("username") for op in operators], key="q_emp")
                with eq2:
                    adj_pts = st.number_input("คะแนนที่ต้องการเพิ่ม (+) หรือ ลด (-):", value=5.0, step=1.0, key="q_pts")
                with eq3:
                    reason_txt = st.text_input("หมายเหตุการแก้ไขคะแนน:", placeholder="เช่น ปรับเพิ่มพิเศษประจำเดือน", key="q_rs")
                
                if st.form_submit_button("บันทึกการแก้ไขคะแนน"):
                    clean_type = "ความดีความชอบ" if adj_pts >= 0 else "ความผิดพลาด"
                    try:
                        supabase.table("kpi_adjustments").insert({
                            "username": target_emp,
                            "points": adj_pts,
                            "reason_type": clean_type,
                            "description": reason_txt,
                            "created_by": curr_user.get("username")
                        }).execute()
                        st.success(f"บันทึกการปรับคะแนน {adj_pts:+} ให้ @{target_emp} สำเร็จแล้ว!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- Admin Panel: จัดการผู้ใช้งานและโครงสร้างฐานข้อมูล ---

def show_admin_panel():
    curr_user = st.session_state.user
    if curr_user.get("role") != "Admin" and curr_user.get("username") != "admin":
        st.error("⛔ หน้านี้สำหรับผู้ดูแลระบบ (Admin) เท่านั้น")
        return

    st.header("🛡️ แผงควบคุมผู้ดูแลระบบ (Admin Panel)")
    tab_pend, tab_users, tab_db = st.tabs([
        "⏳ คำขออนุมัติผู้ใช้ใหม่", 
        "👥 จัดการผู้ใช้งานทั้งหมด & ให้ยศ", 
        "🗄️ โครงสร้างฐานข้อมูล (SQL Migration)"
    ])

    all_users = fetch_all_users()

    # 1. คำขออนุมัติผู้ใช้ใหม่
    with tab_pend:
        st.subheader("คำขอสมัครสมาชิกที่รอการอนุมัติ")
        pending_users = [u for u in all_users if u.get("is_approved") is False and u.get("role") != "Admin"]
        
        if not pending_users:
            st.success("✅ ไม่มีคำขอสมัครสมาชิกค้างอยู่ ทุกคนได้รับการอนุมัติแล้ว")
        else:
            for pu in pending_users:
                with st.container():
                    st.markdown(f"""
                    <div class="kanban-card">
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
                                st.info("💡 กรุณารันคำสั่ง SQL ใน Supabase SQL Editor เพื่อสร้างคอลัมน์ roles ก่อนครับ (ดูได้จากแท็บ 'โครงสร้างฐานข้อมูล')")
                        
                        if st.button("🗑️ ปฏิเสธ / ลบ", key=f"del_user_{pu['user_id']}", use_container_width=True):
                            supabase.table("app_users").delete().eq("user_id", pu["user_id"]).execute()
                            st.warning(f"ลบคำขอของ @{pu.get('username')} แล้ว")
                            st.rerun()
                    st.divider()

    # 2. จัดการผู้ใช้งานทั้งหมด & ให้ยศ
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
                            st.info("💡 กรุณารันคำสั่ง SQL ใน Supabase SQL Editor เพื่อสร้างคอลัมน์ roles ก่อนครับ (ดูได้จากแท็บ 'โครงสร้างฐานข้อมูล')")
                with b2:
                    if u.get("username") != "admin":
                        if st.button("ลบผู้ใช้นี้ออกจากระบบ", key=f"del_emp_{u['user_id']}"):
                            supabase.table("app_users").delete().eq("user_id", u["user_id"]).execute()
                            st.warning("ลบผู้ใช้สำเร็จ")
                            st.rerun()

    # 3. โครงสร้างฐานข้อมูล
    with tab_db:
        st.subheader("คำสั่ง SQL สำหรับตั้งค่าโครงสร้างฐานข้อมูลใน Supabase")
        st.info("💡 หากระบบมีปัญหาบันทึกข้อมูลไม่สำเร็จ สามารถก๊อปปี้คำสั่ง SQL ด้านล่างไปรันใน Supabase > SQL Editor ได้ทันที")
        sql_content = """-- 1. อัปเดตตาราง app_users
ALTER TABLE app_users 
ADD COLUMN IF NOT EXISTS fullname TEXT,
ADD COLUMN IF NOT EXISTS email TEXT,
ADD COLUMN IF NOT EXISTS phone TEXT,
ADD COLUMN IF NOT EXISTS roles TEXT DEFAULT 'ปฏิบัติงาน',
ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;

UPDATE app_users 
SET is_approved = TRUE, 
    roles = 'ระดับสั่งการ, ปฏิบัติงาน',
    fullname = 'ผู้ดูแลระบบ (Admin)'
WHERE username = 'admin' OR role = 'Admin';

-- 2. อัปเดตตาราง tasks
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS creator_username TEXT,
ADD COLUMN IF NOT EXISTS assignees TEXT,
ADD COLUMN IF NOT EXISTS handover_to TEXT,
ADD COLUMN IF NOT EXISTS handover_reason TEXT,
ADD COLUMN IF NOT EXISTS handover_status TEXT DEFAULT 'None',
ADD COLUMN IF NOT EXISTS satisfaction_rating INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS is_ontime BOOLEAN,
ADD COLUMN IF NOT EXISTS submission_note TEXT;

-- 3. ตาราง kpi_adjustments
CREATE TABLE IF NOT EXISTS kpi_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    points NUMERIC NOT NULL,
    reason_type TEXT NOT NULL,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. ตาราง task_logs
CREATE TABLE IF NOT EXISTS task_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID,
    action TEXT NOT NULL,
    performed_by TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS kpi_adjustments DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_logs DISABLE ROW LEVEL SECURITY;
GRANT ALL ON TABLE app_users TO anon, authenticated, service_role;
GRANT ALL ON TABLE tasks TO anon, authenticated, service_role;
GRANT ALL ON TABLE kpi_adjustments TO anon, authenticated, service_role;
GRANT ALL ON TABLE task_logs TO anon, authenticated, service_role;
"""
        st.code(sql_content, language="sql")

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
    st.sidebar.markdown(f"### 👤 ยินดีต้อนรับ: **{curr_fullname}**")
    st.sidebar.caption(f"Username: @{curr_username}")
    
    # แสดง Badge ยศ
    badge_html = ""
    if is_admin:
        badge_html += '<span class="badge-role-admin">🛡️ ผู้ดูแลระบบ</span> '
    for r in curr_roles:
        if r == "ระดับสั่งการ":
            badge_html += '<span class="badge-role-commander">👑 ระดับสั่งการ</span> '
        elif r == "ปฏิบัติงาน":
            badge_html += '<span class="badge-role-operator">🛠️ ปฏิบัติงาน</span> '
    st.sidebar.markdown(badge_html, unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    # เมนูการใช้งาน
    menu_options = [
        "โมดูลที่ 2: กระดานงาน (Kanban Board)", 
        "โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)", 
        "โมดูลที่ 3: แดชบอร์ดคะแนน KPI"
    ]
    if is_admin:
        menu_options.append("⚙️ ผู้ดูแลระบบ (Admin Panel)")

    page = st.sidebar.radio("📌 เลือกเมนูระบบ", menu_options)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    # Routing
    if page == "โมดูลที่ 2: กระดานงาน (Kanban Board)":
        show_module2_kanban_page()
    elif page == "โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)":
        show_module1_commander_page()
    elif page == "โมดูลที่ 3: แดชบอร์ดคะแนน KPI":
        show_module3_kpi_dashboard()
    elif page == "⚙️ ผู้ดูแลระบบ (Admin Panel)":
        show_admin_panel()
