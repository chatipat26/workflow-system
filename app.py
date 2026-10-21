import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from client import supabase

# --- Configuration & Theme Setup ---
st.set_page_config(
    page_title="Team Workflow Hub",
    page_icon="📋",
    layout="wide"
)

# Custom CSS (ชุดสีและ UI เดิม: Pastel Blue, Soft Rose Gold, Beige)
st.markdown("""
    <style>
    font-family: 'Sarabun', sans-serif;
    
    .kanban-card {
        background-color: var(--background-color, #ffffff);
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #b4c6e7;
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

    /* แจ้งเตือนสีส้ม สำหรับงานที่ขอส่งต่อ */
    .kanban-card-handover {
        border-left: 5px solid #fb923c !important;
        background-color: #fff7ed !important;
    }
    
    .kanban-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 8px;
        margin-top: 6px;
    }

    .badge-project {
        background-color: #e0b8b8;
        color: #ffffff;
        padding: 3px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-routine {
        background-color: #f5e6b3;
        color: #5d4037;
        padding: 3px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-urgent {
        background-color: #ff8a80;
        color: #ffffff;
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 0.7rem;
    }

    .badge-role-commander {
        background-color: #e0e7ff;
        color: #3730a3;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-role-operator {
        background-color: #d1fae5;
        color: #065f46;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-role-admin {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    div[data-baseweb="button"] > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Supabase Connection Check ---
if supabase is None:
    st.error("⚠️ ไม่สามารถเชื่อมต่อกับฐานข้อมูล Supabase ได้")
    st.info("💡 วิธีแก้ไข: ไปที่ Render Dashboard > Environment > ตรวจสอบว่าใส่ SUPABASE_URL และ SUPABASE_KEY ถูกต้องแล้วกด Save Changes")
    st.stop()

# --- Session State Management ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

# --- Helper Functions ---

def parse_roles(roles_val):
    if not roles_val:
        return ["ปฏิบัติงาน"]
    if isinstance(roles_val, list):
        return roles_val
    return [r.strip() for r in str(roles_val).split(",") if r.strip()]

def user_has_role(user_dict, role_name):
    if not user_dict:
        return False
    if user_dict.get("role") == "Admin" or user_dict.get("username") == "admin":
        return True
    user_roles = parse_roles(user_dict.get("roles"))
    return role_name in user_roles

def fetch_all_users():
    try:
        res = supabase.table("app_users").select("*").execute()
        return res.data or []
    except Exception:
        return []

def fetch_operators():
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
    try:
        res = supabase.table("tasks").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def log_task_action(task_id, action, performed_by, details=""):
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
    try:
        res = supabase.table("task_logs").select("*").eq("task_id", task_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def fetch_kpi_adjustments(username=None):
    try:
        query = supabase.table("kpi_adjustments").select("*")
        if username:
            query = query.eq("username", username)
        res = query.order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

# --- Authentication & Registration Page ---

def show_auth_page():
    st.title("🔒 เข้าสู่ระบบ (System Login)")
    
    tab_login, tab_register, tab_reset = st.tabs([
        "เข้าสู่ระบบ", 
        "สมัครสมาชิกใหม่", 
        "ลืม / เปลี่ยนรหัสผ่าน"
    ])

    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="kanban-card">', unsafe_allow_html=True)
            username = st.text_input("ชื่อผู้ใช้งาน (Username)", key="l_user")
            password = st.text_input("รหัสผ่าน (Password)", type="password", key="l_pass")
            
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
                                st.warning("⏳ บัญชีของคุณอยู่ระหว่างรอ Admin อนุมัติและกำหนดยศ กรุณาติดต่อ Admin")
                            else:
                                st.session_state.logged_in = True
                                st.session_state.user = user
                                st.rerun()
                        else:
                            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_register:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="kanban-card">', unsafe_allow_html=True)
            st.subheader("ลงทะเบียนพนักงานใหม่")
            with st.form("reg_form", clear_on_submit=True):
                r_user = st.text_input("Username *")
                r_name = st.text_input("ชื่อ - สกุล *")
                r_email = st.text_input("Email *")
                r_phone = st.text_input("เบอร์โทรศัพท์ *")
                r_p1 = st.text_input("รหัสผ่าน *", type="password")
                r_p2 = st.text_input("ยืนยันรหัสผ่าน *", type="password")
                
                if st.form_submit_button("ส่งคำขอสมัครสมาชิก", use_container_width=True):
                    if not (r_user and r_name and r_email and r_phone and r_p1):
                        st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")
                    elif r_p1 != r_p2:
                        st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                    else:
                        check = supabase.table("app_users").select("username").eq("username", r_user).execute()
                        if check.data:
                            st.error("Username นี้มีอยู่ในระบบแล้ว")
                        else:
                            new_u = {
                                "username": r_user.strip(),
                                "password_hash": r_p1,
                                "fullname": r_name.strip(),
                                "email": r_email.strip(),
                                "phone": r_phone.strip(),
                                "role": "Employee",
                                "roles": "ปฏิบัติงาน",
                                "is_approved": False
                            }
                            supabase.table("app_users").insert(new_u).execute()
                            st.success("✅ สมัครสำเร็จ! กรุณารอ Admin อนุมัติสิทธิ์เข้าใช้งาน")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_reset:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="kanban-card">', unsafe_allow_html=True)
            st.subheader("ตั้งรหัสผ่านใหม่")
            with st.form("reset_form"):
                rs_user = st.text_input("Username *")
                rs_contact = st.text_input("Email หรือ เบอร์โทรที่ลงทะเบียนไว้ *")
                rs_p1 = st.text_input("รหัสผ่านใหม่ *", type="password")
                rs_p2 = st.text_input("ยืนยันรหัสผ่านใหม่ *", type="password")
                
                if st.form_submit_button("บันทึกรหัสผ่านใหม่", use_container_width=True):
                    if not (rs_user and rs_contact and rs_p1):
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                    elif rs_p1 != rs_p2:
                        st.error("รหัสผ่านไม่ตรงกัน")
                    else:
                        u_res = supabase.table("app_users").select("*").eq("username", rs_user.strip()).execute()
                        if not u_res.data:
                            st.error("ไม่พบบัญชีผู้ใช้นี้")
                        else:
                            ud = u_res.data[0]
                            if rs_contact.strip().lower() in [str(ud.get("email")).strip().lower(), str(ud.get("phone")).strip()]:
                                supabase.table("app_users").update({"password_hash": rs_p1}).eq("user_id", ud["user_id"]).execute()
                                st.success("✅ แก้ไขรหัสผ่านสำเร็จแล้ว! สามารถเข้าสู่ระบบด้วยรหัสใหม่ได้ทันที")
                            else:
                                st.error("Email หรือ เบอร์โทรไม่ตรงกับข้อมูลในระบบ")
            st.markdown('</div>', unsafe_allow_html=True)

# --- Module 1: ระบบสั่งการและมอบหมายงาน (เฉพาะยศ 'ระดับสั่งการ') ---

def show_module1_commander_page():
    curr_user = st.session_state.user
    if not user_has_role(curr_user, "ระดับสั่งการ"):
        st.error("⛔ จำกัดสิทธิ์: โมดูลนี้อนุญาตเฉพาะผู้มียศ **'ระดับสั่งการ'** เท่านั้น")
        return

    st.header("🎯 โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander Hub)")
    
    sub1, sub2, sub3, sub4 = st.tabs([
        "📝 มอบหมายงานใหม่", 
        "🔄 รายการรออนุมัติส่งต่องาน", 
        "⭐ ตรวจรับงาน & ประเมินความพึงพอใจ", 
        "⚖️ ฟอร์มเพิ่ม/ลดคะแนน KPI"
    ])

    with sub1:
        st.subheader("สร้างและมอบหมายงานใหม่")
        operators = fetch_operators()
        op_dict = {op["display_name"]: op["username"] for op in operators}

        with st.form("create_task_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("ชื่องาน / หัวข้อโปรเจกต์ *")
                task_type = st.selectbox("ประเภทงาน", ["Project", "Routine"])
                priority = st.selectbox("ระดับความเร่งด่วน", ["Normal", "High", "Urgent"])
            with col2:
                due_date = st.date_input("กำหนดวันส่งงาน (Due Date) *")
                selected_ops = st.multiselect("ระบุผู้ปฏิบัติงาน (เลือกได้มากกว่า 1 คน) *", options=list(op_dict.keys()))
                attachment = st.text_input("ลิงก์ไฟล์แนบ (Google Drive / Cloud Link)")

            description = st.text_area("รายละเอียดขอบเขตงาน (Scope of Work) *")
            submitted = st.form_submit_button("บันทึกและส่งงานไปยังกระดาน", use_container_width=True)

            if submitted:
                if not title or not description or not selected_ops:
                    st.error("กรุณากรอกข้อมูลที่จำเป็น (*) และเลือกผู้ปฏิบัติงาน")
                else:
                    assigned_str = ", ".join([op_dict[op] for op in selected_ops])
                    new_task = {
                        "title": title.strip(),
                        "description": description.strip(),
                        "task_type": task_type,
                        "status": "To Do",
                        "priority": priority,
                        "due_date": due_date.strftime('%Y-%m-%d'),
                        "assignee_name": assigned_str,
                        "assignees": assigned_str,
                        "creator_username": curr_user.get("username"),
                        "requester_name": curr_user.get("fullname") or curr_user.get("username"),
                        "requester_dept": "ระดับสั่งการ",
                        "attachment_url": attachment.strip() if attachment else None,
                        "handover_status": "None"
                    }
                    try:
                        res = supabase.table("tasks").insert(new_task).execute()
                        if res.data:
                            log_task_action(res.data[0].get("task_id"), "สร้างงานใหม่", curr_user.get("username"), f"มอบหมายให้: {assigned_str}")
                        st.success("✅ บันทึกงานสำเร็จและส่งขึ้นกระดานงานโมดูลที่ 2 แล้ว!")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

    with sub2:
        st.subheader("อนุมัติคำขอส่งต่องานระหว่างพนักงาน")
        tasks_df = fetch_tasks()
        if not tasks_df.empty and "handover_status" in tasks_df.columns:
            handovers = tasks_df[tasks_df["handover_status"] == "Pending"]
            if curr_user.get("role") != "Admin" and "creator_username" in handovers.columns:
                handovers = handovers[handovers["creator_username"] == curr_user.get("username")]

            if handovers.empty:
                st.info("ไม่มีรายการคำขอส่งต่องานค้างอยู่")
            else:
                for _, row in handovers.iterrows():
                    st.markdown(f"""
                        <div class="kanban-card kanban-card-handover">
                            <span class="badge-project">งาน: {row['title']}</span>
                            <div class="kanban-card-title">คำขอส่งต่องาน</div>
                            <p><strong>ผู้รับผิดชอบเดิม:</strong> {row.get('assignee_name') or '-'}</p>
                            <p><strong>ต้องการส่งต่อให้:</strong> <span style="color:#ea580c; font-weight:bold;">{row.get('handover_to') or '-'}</span></p>
                            <p><strong>เหตุผล:</strong> {row.get('handover_reason') or 'ไม่ได้ระบุ'}</p>
                            <small>📅 กำหนดส่ง: {row.get('due_date') or '-'}</small>
                        </div>
                    """, unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ อนุมัติการส่งต่อ", key=f"ap_ho_{row['task_id']}", use_container_width=True):
                            new_assignee = row.get("handover_to")
                            supabase.table("tasks").update({
                                "assignee_name": new_assignee,
                                "assignees": new_assignee,
                                "handover_status": "Approved"
                            }).eq("task_id", row["task_id"]).execute()
                            log_task_action(row["task_id"], "อนุมัติส่งต่องาน", curr_user.get("username"), f"ส่งต่อให้ {new_assignee}")
                            st.success(f"อนุมัติเปลี่ยนผู้รับผิดชอบเป็น {new_assignee} สำเร็จ!")
                            st.rerun()
                    with c2:
                        if st.button("❌ ปฏิเสธการส่งต่อ", key=f"rj_ho_{row['task_id']}", use_container_width=True):
                            supabase.table("tasks").update({"handover_status": "Rejected"}).eq("task_id", row["task_id"]).execute()
                            log_task_action(row["task_id"], "ปฏิเสธส่งต่องาน", curr_user.get("username"), "ปฏิเสธคำขอ")
                            st.warning("ปฏิเสธคำขอแล้ว")
                            st.rerun()
                    st.divider()
        else:
            st.info("ยังไม่มีข้อมูลคำขอส่งต่องาน")

    with sub3:
        st.subheader("ตรวจรับงาน & ประเมินความพึงพอใจสำหรับคำนวณ KPI")
        tasks_df = fetch_tasks()
        if not tasks_df.empty:
            reviews = tasks_df[tasks_df["status"] == "In Review"]
            if curr_user.get("role") != "Admin" and "creator_username" in reviews.columns:
                reviews = reviews[reviews["creator_username"] == curr_user.get("username")]

            if reviews.empty:
                st.info("ไม่มีงานที่รอการตรวจรับในขณะนี้ (ช่อง In Review ว่าง)")
            else:
                for _, row in reviews.iterrows():
                    ot_badge = "🟢 ส่งตรงเวลา" if row.get("is_ontime") is True else ("🔴 ส่งเกินกำหนด" if row.get("is_ontime") is False else "⚪ รอตรวจสอบวันส่ง")
                    st.markdown(f"""
                        <div class="kanban-card">
                            <div class="kanban-card-title">{row['title']}</div>
                            <p><strong>ผู้รับผิดชอบ:</strong> {row.get('assignee_name') or '-'}</p>
                            <p><strong>รายละเอียด:</strong> {row.get('description') or '-'}</p>
                            <p><strong>ผลงาน/ลิงก์ที่ส่ง:</strong> {row.get('submission_note') or row.get('attachment_url') or '-'}</p>
                            <p><strong>สถานะเวลาส่ง:</strong> {ot_badge} (กำหนดส่ง: {row.get('due_date') or '-'})</p>
                        </div>
                    """, unsafe_allow_html=True)

                    c_rt, c_bt = st.columns([2, 1])
                    with c_rt:
                        rating = st.slider("⭐ ระดับความพึงพอใจ (1-5 ดาว):", 1, 5, 5, key=f"rt_{row['task_id']}")
                    with c_bt:
                        st.write("")
                        if st.button("🏆 อนุมัติผ่านงาน (Done)", key=f"dn_{row['task_id']}", use_container_width=True):
                            if row.get("task_type") == "Routine":
                                old_due = pd.to_datetime(row['due_date']) if row.get('due_date') else datetime.today()
                                next_due = (old_due + pd.DateOffset(months=1)).strftime('%Y-%m-%d')
                                supabase.table("tasks").update({
                                    "status": "To Do",
                                    "due_date": next_due,
                                    "satisfaction_rating": rating,
                                    "submission_note": None
                                }).eq("task_id", row["task_id"]).execute()
                                st.toast(f"🔄 งาน Routine ผ่านแล้ว รอบถัดไปคือ: {next_due}")
                            else:
                                supabase.table("tasks").update({"status": "Done", "satisfaction_rating": rating}).eq("task_id", row["task_id"]).execute()

                            log_task_action(row["task_id"], "อนุมัติงานสำเร็จ", curr_user.get("username"), f"ให้ {rating} ดาว")
                            st.success(f"อนุมัติงาน '{row['title']}' สำเร็จแล้ว!")
                            st.rerun()

                        if st.button("↩️ ส่งกลับไปแก้ไข (Revision)", key=f"rv_{row['task_id']}", use_container_width=True):
                            supabase.table("tasks").update({"status": "Revision"}).eq("task_id", row["task_id"]).execute()
                            log_task_action(row["task_id"], "ส่งกลับไปแก้ไข", curr_user.get("username"), "สั่งแก้ไขงาน")
                            st.warning("ส่งกลับไปสถานะ Revision แล้ว")
                            st.rerun()
                    st.divider()
        else:
            st.info("ยังไม่มีข้อมูลงานในระบบ")

    with sub4:
        st.subheader("แบบฟอร์มเพิ่มหรือลดคะแนน KPI (ความดีความชอบ / ความผิดพลาด)")
        operators = fetch_operators()
        op_list = [op["username"] for op in operators]
        if not op_list:
            st.warning("ไม่พบรายชื่อพนักงานปฏิบัติงานในระบบ")
        else:
            with st.form("kpi_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    adj_user = st.selectbox("เลือกพนักงาน:", op_list)
                    adj_type = st.radio("ประเภท:", ["ความดีความชอบ (เพิ่มแต้ม +)", "ความผิดพลาด (หักแต้ม -)"])
                with c2:
                    points = st.number_input("คะแนน:", min_value=1.0, max_value=50.0, value=5.0, step=1.0)
                    reason = st.text_area("เหตุผลในการปรับคะแนน *")

                if st.form_submit_button("บันทึกการปรับคะแนน", use_container_width=True):
                    if not reason:
                        st.error("กรุณาระบุเหตุผล")
                    else:
                        calc_p = points if "ความดีความชอบ" in adj_type else -points
                        clean_t = "ความดีความชอบ" if "ความดีความชอบ" in adj_type else "ความผิดพลาด"
                        supabase.table("kpi_adjustments").insert({
                            "username": adj_user,
                            "points": calc_p,
                            "reason_type": clean_t,
                            "description": reason.strip(),
                            "created_by": curr_user.get("username")
                        }).execute()
                        st.success(f"✅ บันทึกคะแนน {calc_p:+} ให้ @{adj_user} เรียบร้อยแล้ว!")

# --- Module 2: กระดานงาน (Kanban Board พร้อมตัวกรองผู้รับผิดชอบ & วันส่ง) ---

def show_module2_kanban_page():
    curr_user = st.session_state.user
    curr_username = curr_user.get("username")
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")

    st.header("📋 โมดูลที่ 2: กระดานงาน (Kanban Board)")
    
    df = fetch_tasks()

    # --- ส่วนตัวกรองผู้รับผิดชอบ & วันที่ส่งจากปฏิทิน ---
    st.markdown("##### 🔍 ตัวกรองค้นหาตัวงาน")
    operators = fetch_operators()
    assignee_options = ["ทั้งหมด"] + [op["username"] for op in operators]
    
    f1, f2, f3 = st.columns(3)
    with f1:
        selected_assignee = st.selectbox("เลือกผู้รับผิดชอบงาน:", assignee_options, key="kb_filter_assignee")
    with f2:
        selected_due_date = st.date_input("เลือกวันที่กำหนดส่งจากปฏิทิน:", value=None, key="kb_filter_date")
    with f3:
        selected_type = st.selectbox("เลือกประเภทงาน:", ["ทั้งหมด", "Project", "Routine"], key="kb_filter_type")

    # กรองข้อมูลตามที่เลือก
    filtered_df = df.copy() if not df.empty else pd.DataFrame()
    if not filtered_df.empty:
        if selected_assignee != "ทั้งหมด" and "assignee_name" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["assignee_name"].fillna("").str.contains(selected_assignee)]
        if selected_due_date is not None and "due_date" in filtered_df.columns:
            target_date_str = selected_due_date.strftime("%Y-%m-%d")
            filtered_df = filtered_df[filtered_df["due_date"] == target_date_str]
        if selected_type != "ทั้งหมด" and "task_type" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["task_type"] == selected_type]

    st.divider()

    # แสดงผลคอลัมน์สถานะ 5 ช่องแบบเดิม
    statuses = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
    cols = st.columns(len(statuses))

    for idx, status in enumerate(statuses):
        with cols[idx]:
            count = len(filtered_df[filtered_df['status'] == status]) if not filtered_df.empty and 'status' in filtered_df.columns else 0
            st.markdown(f"#### {status} ({count})")
            
            if not filtered_df.empty and 'status' in filtered_df.columns:
                status_df = filtered_df[filtered_df['status'] == status]
                for _, row in status_df.iterrows():
                    badge_class = "badge-project" if row.get('task_type') == "Project" else "badge-routine"
                    urgent_badge = '<span class="badge-urgent">🔥 Urgent</span>' if row.get('priority') == 'Urgent' else ''
                    
                    # คำนวณการแจ้งเตือนวันกำหนดส่ง (ล่วงหน้า 3 วัน & เกินกำหนด)
                    alert_class = ""
                    alert_text = ""
                    if status != 'Done' and row.get('due_date'):
                        try:
                            due_dt = pd.to_datetime(row['due_date']).date()
                            days_diff = (due_dt - datetime.today().date()).days
                            if days_diff < 0:
                                alert_class = "kanban-card-overdue"
                                alert_text = f'<br/><span style="color:#ef4444; font-size:0.75rem; font-weight:bold;">🚨 เกินกำหนด ({abs(days_diff)} วัน)</span>'
                            elif days_diff <= 3:
                                alert_class = "kanban-card-warning"
                                alert_text = f'<br/><span style="color:#f59e0b; font-size:0.75rem; font-weight:bold;">⚠️ ใกล้กำหนดส่ง (เหลือ {days_diff} วัน)</span>'
                        except Exception:
                            pass

                    # การ์ดแสดงผล
                    creator = row.get("creator_username") or row.get("requester_name") or "-"
                    assignees = row.get("assignee_name") or "-"
                    
                    if status == 'Done':
                        st.markdown(f"""
                        <div class="kanban-card" style="padding: 12px; border-left: 5px solid #a7f3d0; opacity: 0.85; margin-bottom: 8px;">
                            <span class="{badge_class}" style="font-size: 0.65rem; padding: 2px 6px;">{row.get('task_type')}</span>
                            <div class="kanban-card-title" style="font-size: 0.95rem; margin: 6px 0; text-decoration: line-through; color: #6b7280;">{row['title']}</div>
                            <small style="font-size: 0.75rem; color: #6b7280;">👤 {assignees} | 📅 {row.get('due_date') or '-'}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="kanban-card {alert_class}">
                            <span class="{badge_class}">{row.get('task_type', 'Task')}</span> {urgent_badge}
                            <div class="kanban-card-title">{row['title']}</div>
                            <small>👑 <strong>ผู้สั่งการ:</strong> @{creator}</small><br/>
                            <small>👤 <strong>ผู้ปฏิบัติ:</strong> {assignees}</small><br/>
                            <small>📅 <strong>กำหนดส่ง:</strong> {row.get('due_date') or '-'}</small>{alert_text}
                        </div>
                        """, unsafe_allow_html=True)

                    # เมนูจัดการภายในการ์ดงาน
                    with st.expander("⚙️ ดูรายละเอียด & ดำเนินการ"):
                        st.markdown(f"**รายละเอียดงาน:**")
                        st.info(row.get('description') or 'ไม่มีรายละเอียด')
                        if row.get('attachment_url'):
                            st.markdown(f"[📎 คลิกเปิดดูไฟล์แนบ]({row['attachment_url']})")

                        logs = fetch_task_logs(row['task_id'])
                        if logs:
                            st.caption("📜 ประวัติงานล่าสุด:")
                            for l in logs[:2]:
                                st.caption(f"• {l.get('action')} โดย @{l.get('performed_by')}: {l.get('details')}")

                        st.divider()

                        if status in ['To Do', 'Revision']:
                            if st.button("🚀 เริ่มดำเนินงาน", key=f"st_{row['task_id']}", use_container_width=True):
                                supabase.table("tasks").update({"status": "In Progress"}).eq("task_id", row["task_id"]).execute()
                                log_task_action(row["task_id"], "เริ่มดำเนินงาน", curr_username, "เปลี่ยนสถานะเป็น In Progress")
                                st.rerun()

                        if status == 'In Progress':
                            s_note = st.text_input("ลิงก์งานที่ทำเสร็จ / หมายเหตุ:", key=f"sn_{row['task_id']}")
                            if st.button("✅ ส่งงานเพื่อรออนุมัติ", key=f"sb_{row['task_id']}", use_container_width=True):
                                is_ot = True
                                if row.get("due_date"):
                                    try:
                                        if datetime.today().date() > pd.to_datetime(row['due_date']).date():
                                            is_ot = False
                                    except Exception:
                                        pass
                                supabase.table("tasks").update({
                                    "status": "In Review",
                                    "submission_note": s_note,
                                    "completed_at": datetime.now().isoformat(),
                                    "is_ontime": is_ot
                                }).eq("task_id", row["task_id"]).execute()
                                log_task_action(row["task_id"], "ส่งงานเพื่อรออนุมัติ", curr_username, f"ผล: {'ตรงเวลา' if is_ot else 'ล่าช้า'}")
                                st.success("ส่งงานเรียบร้อยแล้ว!")
                                st.rerun()

                        if status not in ['Done', 'In Review']:
                            with st.popover("🤝 ขอส่งงานต่อให้ผู้อื่น"):
                                target_op = st.selectbox("เลือกผู้รับต่อ:", [op["username"] for op in operators if op["username"] != curr_username], key=f"ho_{row['task_id']}")
                                ho_rs = st.text_area("เหตุผล:", key=f"rs_{row['task_id']}")
                                if st.button("ส่งคำขอส่งต่อ", key=f"hbtn_{row['task_id']}"):
                                    if ho_rs:
                                        supabase.table("tasks").update({
                                            "handover_to": target_op,
                                            "handover_reason": ho_rs,
                                            "handover_status": "Pending"
                                        }).eq("task_id", row["task_id"]).execute()
                                        log_task_action(row["task_id"], "ขอส่งงานต่อ", curr_username, f"ขอส่งให้ @{target_op}")
                                        st.success("ส่งคำขอส่งต่อแล้ว!")
                                        st.rerun()

                        if is_commander:
                            st.divider()
                            st.caption("สิทธิ์ผู้สั่งการ: ย้ายสถานะโดยตรงหรือลบงาน")
                            new_stat = st.selectbox("ย้ายการ์ดไปที่:", statuses, index=statuses.index(status), key=f"sel_{row['task_id']}")
                            b1, b2 = st.columns(2)
                            with b1:
                                if st.button("อัปเดต", key=f"btn_{row['task_id']}", use_container_width=True):
                                    supabase.table("tasks").update({"status": new_stat}).eq("task_id", row["task_id"]).execute()
                                    st.rerun()
                            with b2:
                                if st.button("🗑️", key=f"del_{row['task_id']}", use_container_width=True):
                                    supabase.table("tasks").delete().eq("task_id", row["task_id"]).execute()
                                    st.rerun()

# --- Module 3: แดชบอร์ดคะแนน KPI & รายงานผลงานเก่าเรียกดูย้อนหลัง ---

def show_module3_kpi_dashboard():
    curr_user = st.session_state.user
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")

    st.header("📊 โมดูลที่ 3: แดชบอร์ดคะแนน KPI & รายงานผลงาน")
    
    tasks_df = fetch_tasks()
    all_users = fetch_all_users()
    operators = [u for u in all_users if "ปฏิบัติงาน" in parse_roles(u.get("roles"))]
    adjustments = fetch_kpi_adjustments()

    # การ์ดสรุปเมตริกเดิม 4 ตัว
    m1, m2, m3, m4 = st.columns(4)
    total_t = len(tasks_df) if not tasks_df.empty else 0
    in_prog = len(tasks_df[tasks_df['status'] == 'In Progress']) if not tasks_df.empty and 'status' in tasks_df.columns else 0
    in_rev = len(tasks_df[tasks_df['status'].isin(['In Review', 'Revision'])]) if not tasks_df.empty and 'status' in tasks_df.columns else 0
    done_c = len(tasks_df[tasks_df['status'] == 'Done']) if not tasks_df.empty and 'status' in tasks_df.columns else 0

    m1.metric("📌 งานทั้งหมด", total_t)
    m2.metric("⏳ กำลังดำเนินการ", in_prog)
    m3.metric("🔍 อยู่ระหว่างตรวจ/แก้ไข", in_rev)
    m4.metric("✅ เสร็จสิ้น", done_c)

    st.markdown("---")

    # แท็บ: 1. คะแนน KPI ปัจจุบัน  |  2. รายงานผลงานเก่าเรียกดูย้อนหลัง
    tab_kpi, tab_history = st.tabs([
        "📈 คะแนน KPI พนักงาน (Leaderboard)", 
        "📜 รายงานผลงานเก่า & เรียกดูย้อนหลัง (Historical Work Report)"
    ])

    # 1. แดชบอร์ดคะแนน KPI
    with tab_kpi:
        kpi_records = []
        for op in operators:
            uname = op.get("username")
            fullname = op.get("fullname") or uname
            
            user_tasks = tasks_df[tasks_df["assignee_name"].fillna("").str.contains(uname)] if not tasks_df.empty and "assignee_name" in tasks_df.columns else pd.DataFrame()
            tot = len(user_tasks)
            d_count = len(user_tasks[user_tasks["status"] == "Done"]) if not user_tasks.empty else 0
            
            ontime_c = 0
            late_c = 0
            ratings = []
            if not user_tasks.empty:
                for _, t in user_tasks.iterrows():
                    if t.get("status") == "Done":
                        if t.get("is_ontime") is True:
                            ontime_c += 1
                        elif t.get("is_ontime") is False:
                            late_c += 1
                        r = t.get("satisfaction_rating")
                        if r and r > 0:
                            ratings.append(r)

            avg_r = sum(ratings) / len(ratings) if ratings else 5.0
            user_adjs = [a for a in adjustments if a.get("username") == uname]
            man_pts = sum(float(a.get("points", 0)) for a in user_adjs)
            
            tot_kpi = max(0, round((d_count * 5) + (ontime_c * 10) - (late_c * 5) + (avg_r * 4) + man_pts, 1))

            kpi_records.append({
                "username": uname,
                "fullname": fullname,
                "total_tasks": tot,
                "done_tasks": d_count,
                "ontime_count": ontime_c,
                "late_count": late_c,
                "avg_rating": round(avg_r, 1),
                "manual_points": man_pts,
                "total_kpi": tot_kpi
            })

        kpi_df = pd.DataFrame(kpi_records)
        if not kpi_df.empty:
            kpi_df = kpi_df.sort_values(by="total_kpi", ascending=False).reset_index(drop=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📈 อันดับคะแนน KPI รวม")
            if not kpi_df.empty:
                fig1 = px.bar(
                    kpi_df, 
                    x="fullname", 
                    y="total_kpi", 
                    labels={"fullname": "พนักงาน", "total_kpi": "คะแนน KPI รวม"},
                    color_discrete_sequence=['#b4c6e7']
                )
                fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig1, use_container_width=True)

        with c2:
            st.markdown("##### ⏱️ สัดส่วนงาน: ตรงเวลา vs ล่าช้า")
            if not kpi_df.empty:
                fig2 = px.bar(
                    kpi_df,
                    x="fullname",
                    y=["ontime_count", "late_count"],
                    labels={"value": "จำนวนงาน", "fullname": "พนักงาน", "variable": "ประเภท"},
                    barmode="group",
                    color_discrete_map={"ontime_count": "#a7f3d0", "late_count": "#fecaca"}
                )
                fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### 📋 ตารางแจกแจงรายละเอียดคะแนน KPI รายบุคคล")
        if not kpi_df.empty:
            st.dataframe(kpi_df.rename(columns={
                "fullname": "ชื่อ-นามสกุล",
                "username": "Username",
                "total_tasks": "งานทั้งหมด",
                "done_tasks": "งานที่เสร็จ",
                "ontime_count": "ส่งทันเวลา",
                "late_count": "ส่งล่าช้า",
                "avg_rating": "ดาวเฉลี่ย ⭐",
                "manual_points": "แต้มพิเศษ/ปรับลด",
                "total_kpi": "คะแนน KPI รวม"
            }), use_container_width=True, hide_index=True)

        if is_commander:
            st.markdown("---")
            with st.expander("⚙️ เครื่องมือปรับคะแนน KPI โดยตรง (เฉพาะผู้มียศสั่งการ)"):
                with st.form("adj_direct"):
                    ea1, ea2, ea3 = st.columns(3)
                    with ea1:
                        target_e = st.selectbox("เลือกพนักงาน:", [op.get("username") for op in operators])
                    with ea2:
                        points_e = st.number_input("คะแนนที่ปรับ (+/-):", value=5.0, step=1.0)
                    with ea3:
                        reason_e = st.text_input("หมายเหตุ:")
                    if st.form_submit_button("บันทึกการปรับคะแนน"):
                        clean_tp = "ความดีความชอบ" if points_e >= 0 else "ความผิดพลาด"
                        supabase.table("kpi_adjustments").insert({
                            "username": target_e,
                            "points": points_e,
                            "reason_type": clean_tp,
                            "description": reason_e,
                            "created_by": curr_user.get("username")
                        }).execute()
                        st.success("บันทึกคะแนนเรียบร้อยแล้ว!")
                        st.rerun()

    # 2. รายงานผลงานเก่า & เรียกดูย้อนหลัง
    with tab_history:
        st.subheader("📜 รายงานผลงานเก่า & เรียกดูย้อนหลัง")
        st.caption("ตรวจสอบว่าพนักงานคนไหน ทำงานอะไรสำเร็จไปแล้วบ้าง พร้อมรายละเอียดคะแนนความพึงพอใจและแต้ม KPI")

        ch1, ch2 = st.columns(2)
        with ch1:
            filter_emp = st.selectbox("เลือกพนักงานที่ต้องการดูรีพอร์ต:", ["ทุกคน"] + [op["username"] for op in operators], key="hist_emp_sel")
        with ch2:
            filter_stat = st.selectbox("สถานะงาน:", ["เฉพาะงานที่สำเร็จแล้ว (Done)", "งานทุกสถานะ"], key="hist_stat_sel")

        rep_df = tasks_df.copy() if not tasks_df.empty else pd.DataFrame()
        if not rep_df.empty:
            if filter_stat == "เฉพาะงานที่สำเร็จแล้ว (Done)":
                rep_df = rep_df[rep_df["status"] == "Done"]
            if filter_emp != "ทุกคน":
                rep_df = rep_df[rep_df["assignee_name"].fillna("").str.contains(filter_emp)]

        if rep_df.empty:
            st.info("ไม่มีประวัติผลงานตามเงื่อนไขที่เลือก")
        else:
            rep_list = []
            for _, r in rep_df.iterrows():
                is_ot = r.get("is_ontime")
                ot_str = "🟢 ตรงเวลา (+10)" if is_ot is True else ("🔴 ล่าช้า (-5)" if is_ot is False else "⚪ ปกติ")
                rating = r.get("satisfaction_rating") or 0
                
                base_pt = 5 if r.get("status") == "Done" else 0
                time_pt = 10 if is_ot is True else (-5 if is_ot is False else 0)
                star_pt = rating * 4
                task_kpi = base_pt + time_pt + star_pt

                rep_list.append({
                    "ชื่องาน": r.get("title"),
                    "ผู้รับผิดชอบงาน": r.get("assignee_name") or "-",
                    "ผู้สั่งการ": r.get("creator_username") or r.get("requester_name") or "-",
                    "ประเภท": r.get("task_type"),
                    "กำหนดส่ง": r.get("due_date") or "-",
                    "วันที่ส่งงานจริง": str(r.get("completed_at") or "-")[:10],
                    "ผลการส่ง": ot_str,
                    "คะแนนประเมิน (ดาว)": f"⭐ {rating}/5" if rating > 0 else "-",
                    "แต้ม KPI ที่ได้จากงานนี้": f"+{task_kpi}" if task_kpi >= 0 else str(task_kpi),
                    "สถานะงาน": r.get("status"),
                    "ลิงก์/ผลงานที่ส่ง": r.get("submission_note") or r.get("attachment_url") or "-"
                })

            history_table = pd.DataFrame(rep_list)
            st.markdown(f"**พบรายการงานทั้งหมด:** `{len(history_table)} งาน`")
            st.dataframe(history_table, use_container_width=True, hide_index=True)

            csv = history_table.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดรายงานนี้เป็นไฟล์ Excel (CSV)",
                data=csv,
                file_name=f"work_history_report_{datetime.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# --- Admin Panel: จัดการผู้ใช้งานและโครงสร้างฐานข้อมูล ---

def show_admin_panel():
    curr_user = st.session_state.user
    if curr_user.get("role") != "Admin" and curr_user.get("username") != "admin":
        st.error("⛔ หน้านี้สำหรับ Admin เท่านั้น")
        return

    st.header("🛡️ แผงควบคุมผู้ดูแลระบบ (Admin Panel)")
    tab_p, tab_u = st.tabs(["คำขออนุมัติผู้ใช้ใหม่", "จัดการผู้ใช้งานทั้งหมด & ให้ยศ"])
    
    all_users = fetch_all_users()

    with tab_p:
        st.subheader("คำขอสมัครสมาชิกที่รออนุมัติ")
        pending = [u for u in all_users if u.get("is_approved") is False and u.get("role") != "Admin"]
        if not pending:
            st.success("ไม่มีคำขอค้างอยู่ ทุกคนได้รับการอนุมัติแล้ว")
        else:
            for pu in pending:
                st.markdown(f"""
                <div class="kanban-card">
                    <strong>ชื่อ-สกุล:</strong> {pu.get('fullname') or '-'}<br/>
                    <strong>Username:</strong> @{pu.get('username')}<br/>
                    <strong>Email:</strong> {pu.get('email') or '-'}<br/>
                    <strong>เบอร์โทร:</strong> {pu.get('phone') or '-'}<br/>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns([2, 1])
                with c1:
                    new_r = st.multiselect(f"กำหนดยศให้ @{pu.get('username')}:", ["ระดับสั่งการ", "ปฏิบัติงาน"], default=["ปฏิบัติงาน"], key=f"r_{pu['user_id']}")
                with c2:
                    if st.button("อนุมัติและเปิดใช้งาน", key=f"ap_{pu['user_id']}", use_container_width=True):
                        supabase.table("app_users").update({
                            "is_approved": True,
                            "roles": ", ".join(new_r) if new_r else "ปฏิบัติงาน"
                        }).eq("user_id", pu["user_id"]).execute()
                        st.success(f"อนุมัติ @{pu.get('username')} เรียบร้อยแล้ว!")
                        st.rerun()
                    if st.button("ลบคำขอ", key=f"dl_{pu['user_id']}", use_container_width=True):
                        supabase.table("app_users").delete().eq("user_id", pu["user_id"]).execute()
                        st.rerun()
                st.divider()

    with tab_u:
        st.subheader("รายชื่อผู้ใช้งานทั้งหมด")
        for u in all_users:
            with st.expander(f"👤 {u.get('fullname') or u.get('username')} (@{u.get('username')})"):
                st.write(f"**Email:** {u.get('email') or '-'}")
                st.write(f"**เบอร์โทร:** {u.get('phone') or '-'}")
                curr_r = parse_roles(u.get("roles"))
                edit_r = st.multiselect(
                    "แก้ไขยศ (1 User มีได้มากกว่า 1 ยศ):",
                    ["ระดับสั่งการ", "ปฏิบัติงาน"],
                    default=[r for r in curr_r if r in ["ระดับสั่งการ", "ปฏิบัติงาน"]],
                    key=f"ed_r_{u['user_id']}"
                )
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("บันทึกการแก้ไขยศ", key=f"sv_{u['user_id']}"):
                        supabase.table("app_users").update({"roles": ", ".join(edit_r)}).eq("user_id", u["user_id"]).execute()
                        st.success("บันทึกยศสำเร็จ!")
                        st.rerun()
                with b2:
                    if u.get("username") != "admin":
                        if st.button("ลบผู้ใช้", key=f"dl_u_{u['user_id']}"):
                            supabase.table("app_users").delete().eq("user_id", u["user_id"]).execute()
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
    st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: **{curr_fullname}**")
    st.sidebar.caption(f"Username: @{curr_username}")
    
    badge_html = ""
    if is_admin:
        badge_html += '<span class="badge-role-admin">🛡️ Admin</span> '
    for r in curr_roles:
        if r == "ระดับสั่งการ":
            badge_html += '<span class="badge-role-commander">👑 สั่งการ</span> '
        elif r == "ปฏิบัติงาน":
            badge_html += '<span class="badge-role-operator">🛠️ ปฏิบัติงาน</span> '
    st.sidebar.markdown(badge_html, unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")
    
    menu_options = [
        "โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)",
        "โมดูลที่ 2: กระดานงาน (Kanban Board)", 
        "โมดูลที่ 3: แดชบอร์ดคะแนน KPI"
    ]
    if is_admin:
        menu_options.append("⚙️ ผู้ดูแลระบบ (Admin Panel)")

    default_idx = 0 if is_commander else 1
    page = st.sidebar.radio("เมนูการใช้งาน", menu_options, index=default_idx)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    if page == "โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)":
        show_module1_commander_page()
    elif page == "โมดูลที่ 2: กระดานงาน (Kanban Board)":
        show_module2_kanban_page()
    elif page == "โมดูลที่ 3: แดชบอร์ดคะแนน KPI":
        show_module3_kpi_dashboard()
    elif page == "⚙️ ผู้ดูแลระบบ (Admin Panel)":
        show_admin_panel()
