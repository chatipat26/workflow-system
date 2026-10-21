import os
import base64
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from supabase import create_client, Client

# --- Logo & Watermark Helper (Cached เพื่อความเร็ว) ---
@st.cache_data
def get_file_base64_cached(filepath):
    """แปลงไฟล์ภาพเป็น Base64 และแคชไว้ในหน่วยความจำ"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for candidate in [filepath, os.path.join(base_dir, filepath), os.path.join(base_dir, "..", filepath)]:
        if os.path.exists(candidate):
            try:
                with open(candidate, "rb") as f:
                    return base64.b64encode(f.read()).decode()
            except Exception:
                pass
    return ""

def get_watermark_b64():
    for f in ["svv_bg_watermark.png", "svv_watermark_stamp.png", "bg_watermark.png", "watermark.png"]:
        b = get_file_base64_cached(f)
        if b:
            return b
    return ""

def get_logo_b64():
    for f in ["svv_logo_header.png", "svv_logo_transparent.png", "logo_thumb.jpg", "logo.jpg"]:
        b = get_file_base64_cached(f)
        if b:
            return b
    return ""

LOGO_B64 = get_logo_b64()
BG_WATERMARK_B64 = get_watermark_b64()

# --- Supabase Connection ---
@st.cache_resource
def get_supabase_client():
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
        print(f"Supabase connection error: {e}")
        return None

supabase = get_supabase_client()

# --- Configuration & Theme Setup ---
st.set_page_config(
    page_title="Team Workflow SVV",
    page_icon="📋",
    layout="wide"
)

# Custom CSS: โทนสีฟ้าเข้ากับโลโก้ SVV (Royal & Sky Blue) สะอาดตา อ่านง่าย โหลดเร็ว
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Sarabun', sans-serif !important;
    }
    
    /* พื้นหลังหน้าจอหลักสีสบายตา (Clean Soft Background) */
    [data-testid="stAppViewContainer"],
    .stApp {
        background-color: #f8fafc !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* ปิดหน้าจอโหลดสีเทาที่ทำให้ดูหน่วง */
    [data-testid="stAppViewContainer"].stAppRunning,
    div[data-testid="stAppViewContainer"] > section.main {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }

    /* การ์ดงานและแถบสีฟ้า SVV */
    .kanban-card {
        background-color: #ffffff !important;
        border: 1px solid #bae6fd;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 10px rgba(2, 132, 199, 0.05);
        border-left: 5px solid #0284c7;
    }
    
    /* ปุ่มกดสีฟ้า SVV Gradient */
    div[data-baseweb="button"] > button[kind="primary"] {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        border: none !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25) !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="button"] > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* ป้ายสถานะงาน */
    .badge-status {
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-todo { background-color: #f1f5f9; color: #475569; }
    .badge-progress { background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
    .badge-review { background-color: #fef3c7; color: #92400e; }
    .badge-revision { background-color: #ffedd5; color: #9a3412; }
    .badge-done { background-color: #dcfce7; color: #166534; }
    .badge-overdue { background-color: #fee2e2; color: #991b1b; font-weight: 700; }
    .badge-warning { background-color: #fef3c7; color: #b45309; font-weight: 700; }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border: 1.5px solid #bae6fd !important;
        border-radius: 16px !important;
        box-shadow: 0 6px 24px rgba(2, 132, 199, 0.08) !important;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] {
        background-color: #ffffff !important;
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

# --- Cached Fast Database Functions (TTL 2-5 นาที ลดแลค ลดรอ) ---

@st.cache_data(ttl=120)
def fetch_tasks():
    try:
        res = supabase.table("tasks").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_all_users():
    try:
        res = supabase.table("app_users").select("*").execute()
        return res.data or []
    except Exception:
        return []

@st.cache_data(ttl=120)
def fetch_kpi_adjustments():
    try:
        res = supabase.table("kpi_adjustments").select("*").order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def clear_all_cache():
    st.cache_data.clear()

def delete_task_record(task_id, task_title=""):
    """ลบงานออกจากฐานข้อมูล ทั้ง task_logs และ tasks พร้อมล้างแคชเพื่อให้จำนวนงานและคะแนน KPI ลดลงทันที"""
    try:
        supabase.table("task_logs").delete().eq("task_id", task_id).execute()
    except Exception as e:
        print(f"Log delete error: {e}")
    try:
        supabase.table("tasks").delete().eq("task_id", task_id).execute()
        clear_all_cache()
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการลบงาน: {e}")
        return False

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

@st.cache_data(ttl=180)
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
    """ดึงข้อมูลบันทึกความคืบหน้าและประวัติการทำงานทั้งหมดของงานนี้"""
    try:
        res = supabase.table("task_logs").select("*").eq("task_id", task_id).order("created_at", desc=False).execute()
        return res.data or []
    except Exception:
        return []

def format_datetime_thai(dt_val):
    """แปลงเวลาเป็นเวลาประเทศไทย (UTC+7) รูปแบบอ่านง่าย"""
    if not dt_val:
        return "-"
    try:
        dt = pd.to_datetime(dt_val)
        if dt.tz is None:
            dt = dt + pd.Timedelta(hours=7)
        else:
            dt = dt.tz_convert("Asia/Bangkok")
        return dt.strftime("%d/%m/%Y %H:%M น.")
    except Exception:
        return str(dt_val)[:16]

def user_can_edit_task_progress(curr_user, task):
    """ตรวจสอบสิทธิ์: เพิ่มเติมแก้ไขบันทึกได้เฉพาะผู้รับผิดชอบงาน และ User ระดับสั่งการ / Admin เท่านั้น"""
    if not curr_user or not task:
        return False
    # 1. Admin
    if curr_user.get("role") == "Admin" or curr_user.get("username") == "admin":
        return True
    # 2. ผู้มียศ 'ระดับสั่งการ'
    if user_has_role(curr_user, "ระดับสั่งการ"):
        return True
    # 3. ผู้รับผิดชอบงาน (Assignee)
    curr_username = str(curr_user.get("username", "")).strip()
    assignees_str = str(task.get("assignee_name") or task.get("assignees") or "")
    if curr_username and curr_username in assignees_str:
        return True
    return False

@st.dialog("📝 บันทึกความคืบหน้า & สรุปผลงาน", width="large")
def show_task_progress_dialog(task, curr_user):
    tid = task.get("task_id")
    title = task.get("title", "ไม่มีชื่อ")
    status = task.get("status", "To Do")
    assignee = task.get("assignee_name", "-")
    creator = task.get("creator_username", "-")
    due_date = task.get("due_date", "-")
    desc = task.get("description", "-")
    attachment = task.get("attachment_url")

    can_edit = user_can_edit_task_progress(curr_user, task)

    # 1. กล่องสรุปภาพรวมของงาน
    with st.container(border=True):
        st.markdown(f"#### 📌 {title}")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**สถานะ:** `{status}`")
        c2.markdown(f"**ผู้รับผิดชอบ:** `{assignee}`")
        c3.markdown(f"**ผู้สั่งการ:** `@{creator}`")
        c4.markdown(f"**กำหนดส่ง:** `{due_date}`")
        if desc and desc != "-":
            st.caption(f"**ขอบเขตงาน (Scope):** {desc}")
        if attachment:
            st.markdown(f"📎 **ไฟล์แนบ / ลิงก์:** [{attachment}]({attachment})")

    st.markdown("---")

    # 2. ประวัติการรายงานความคืบหน้าและการปฏิบัติงานย้อนหลังทั้งหมด
    st.markdown("#### 📜 ประวัติความคืบหน้า & บันทึกงานย้อนหลังทั้งหมด")
    logs = fetch_task_logs(tid)

    if not logs:
        st.info("ℹ️ ยังไม่มีบันทึกความคืบหน้าสำหรับงานนี้ สามารถเพิ่มบันทึกแรกได้ด้านล่าง")
    else:
        for l in logs:
            action = l.get("action", "บันทึก")
            performed_by = l.get("performed_by", "-")
            details = l.get("details", "")
            created_at_fmt = format_datetime_thai(l.get("created_at"))

            badge_style = "background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd;"
            if "ความคืบหน้า" in action:
                badge_style = "background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd;"
            elif "สรุป" in action:
                badge_style = "background:#dcfce7; color:#166534; border:1px solid #bbf7d0;"
            elif "ปัญหา" in action or "อุปสรรค" in action:
                badge_style = "background:#fee2e2; color:#991b1b; border:1px solid #fecaca;"
            elif "สร้างงาน" in action:
                badge_style = "background:#f1f5f9; color:#475569;"
            elif "อนุมัติ" in action:
                badge_style = "background:#fef3c7; color:#92400e; border:1px solid #fde68a;"

            with st.container(border=True):
                head_col, time_col = st.columns([3.2, 1.8])
                with head_col:
                    st.markdown(f"""
                        <span class="badge-status" style="{badge_style} font-weight:700;">{action}</span>
                        <span style="font-size:0.9rem; margin-left:6px; color:#334155;">โดย <b>@{performed_by}</b></span>
                    """, unsafe_allow_html=True)
                with time_col:
                    st.caption(f"🕒 {created_at_fmt}")

                st.markdown(f"<div style='margin-top:6px; font-size:0.95rem; color:#1e293b; line-height:1.5;'>{details if details else '-'}</div>", unsafe_allow_html=True)

                # สิทธิ์แก้ไขหรือลบบันทึก: เฉพาะผู้เขียนบันทึกนั้นๆ หรือ User ระดับสั่งการ / Admin
                is_author = (curr_user.get("username") == performed_by)
                has_modify_right = is_author or user_has_role(curr_user, "ระดับสั่งการ") or (curr_user.get("role") == "Admin") or (curr_user.get("username") == "admin")
                if can_edit and has_modify_right and action not in ["สร้างงานใหม่"]:
                    with st.expander("✏️ แก้ไข / ลบบันทึกนี้"):
                        new_txt = st.text_area("แก้ไขเนื้อหา:", value=details, key=f"ed_txt_{l['log_id']}")
                        btn_c1, btn_c2 = st.columns([1, 1])
                        with btn_c1:
                            if st.button("บันทึกการแก้ไข", key=f"btn_sv_{l['log_id']}", type="primary", use_container_width=True):
                                if new_txt.strip():
                                    supabase.table("task_logs").update({"details": new_txt.strip()}).eq("log_id", l["log_id"]).execute()
                                    st.success("บันทึกการแก้ไขเรียบร้อยแล้ว!")
                                    st.rerun(scope="fragment")
                                else:
                                    st.warning("กรุณาระบุข้อความ")
                        with btn_c2:
                            if st.button("🗑️ ลบบันทึกนี้", key=f"btn_dl_{l['log_id']}", use_container_width=True):
                                supabase.table("task_logs").delete().eq("log_id", l["log_id"]).execute()
                                st.success("ลบบันทึกเรียบร้อยแล้ว!")
                                st.rerun(scope="fragment")

    st.markdown("---")

    # 3. ฟอร์มเพิ่มบันทึกรายงานความคืบหน้า / สรุปงานใหม่ (เฉพาะผู้รับผิดชอบงาน และ User ระดับสั่งการ)
    if can_edit:
        st.markdown("#### ➕ เพิ่มบันทึกรายงานความคืบหน้า / สรุปงานใหม่")
        with st.form(f"add_progress_form_{tid}", clear_on_submit=True):
            f_col1, f_col2 = st.columns([1.5, 2.5])
            with f_col1:
                log_type = st.selectbox("ประเภทบันทึก:", [
                    "📌 รายงานความคืบหน้า",
                    "📝 สรุปงาน / ส่งมอบงาน",
                    "⚠️ ปัญหา / อุปสรรค",
                    "💡 บันทึก / หมายเหตุทั่วไป"
                ])
            with f_col2:
                st.caption(f"ผู้บันทึก: **@{curr_user.get('username')}** (มีสิทธิ์บันทึก/แก้ไข)")

            progress_detail = st.text_area("รายละเอียดความคืบหน้า / รายงานสรุปงาน *:", placeholder="ระบุสิ่งที่ทำเสร็จแล้ว ขั้นตอนต่อไป ผลลัพธ์ หรือลิงก์เอกสาร...")

            submitted = st.form_submit_button("💾 บันทึกรายงานความคืบหน้า", type="primary", use_container_width=True)

            if submitted:
                if not progress_detail.strip():
                    st.error("กรุณาระบุรายละเอียดก่อนกดบันทึก")
                else:
                    try:
                        clean_action = log_type.split(" ", 1)[1] if " " in log_type else log_type
                        supabase.table("task_logs").insert({
                            "task_id": tid,
                            "action": clean_action,
                            "performed_by": curr_user.get("username"),
                            "details": progress_detail.strip()
                        }).execute()
                        clear_all_cache()
                        st.success("✅ บันทึกรายงานความคืบหน้าสำเร็จแล้ว!")
                        st.rerun(scope="fragment")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
    else:
        st.info(f"🔒 **สิทธิ์การบันทึก/แก้ไข:** เฉพาะผู้รับผิดชอบงานนี้ (`{assignee}`) และผู้มียศ **ระดับสั่งการ** เท่านั้น (คุณสามารถกดดูประวัติย้อนหลังได้ทั้งหมด)")

    st.write("")
    if st.button("✖️ ปิดหน้าต่าง (Close)", key=f"cls_dlg_{tid}", use_container_width=True):
        st.rerun()

def get_available_months(tasks_df):
    """ดึงรายการเดือน-ปี ทั้งหมดที่มีในระบบเพื่อใช้เป็นตัวกรองผลงานย้อนหลัง"""
    if tasks_df.empty:
        return []
    months = set()
    thai_months = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    for _, r in tasks_df.iterrows():
        d_val = r.get("completed_at") or r.get("due_date") or r.get("created_at")
        if d_val:
            try:
                dt = pd.to_datetime(d_val)
                m_label = f"{thai_months[dt.month]} {dt.year + 543}"
                months.add((dt.year, dt.month, m_label))
            except Exception:
                pass
    sorted_m = sorted(list(months), key=lambda x: (x[0], x[1]), reverse=True)
    return [x[2] for x in sorted_m]

def task_matches_month(task_row, month_label):
    """ตรวจสอบว่างานนี้อยู่ในเดือน-ปีที่เลือกหรือไม่"""
    if not month_label or month_label == "ทุกเดือน":
        return True
    d_val = task_row.get("completed_at") or task_row.get("due_date") or task_row.get("created_at")
    if not d_val:
        return False
    try:
        dt = pd.to_datetime(d_val)
        thai_months = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
        m_label = f"{thai_months[dt.month]} {dt.year + 543}"
        return m_label == month_label
    except Exception:
        return False

@st.dialog("↩️ ความคิดเห็นต่อผลงาน & กำหนดวันส่งใหม่", width="medium")
def show_return_task_dialog(task, curr_user):
    tid = task.get("task_id")
    title = task.get("title", "")
    assignee = task.get("assignee_name", "-")
    curr_due = task.get("due_date")
    try:
        def_due = pd.to_datetime(curr_due).date() if curr_due else datetime.today().date()
    except Exception:
        def_due = datetime.today().date()
        
    st.markdown(f"#### 📌 ชื่องาน: **{title}**")
    st.caption(f"ผู้รับผิดชอบงาน: **{assignee}** | กำหนดส่งเดิม: **{curr_due or '-'}**")
    st.divider()

    with st.form(f"form_return_{tid}"):
        choice = st.radio(
            "การตัดสินใจของผู้สั่งการ:", 
            ["🚀 อนุมัติให้ทำงานต่อ (ย้ายไป In Progress)", "🔧 ส่งกลับไปแก้ไข (ย้ายไป Revision)"],
            index=0
        )
        
        feedback = st.text_area(
            "💬 ข้อความแสดงความคิดเห็นต่อผลงาน (Feedback / สิ่งที่ต้องแก้ไข) *:",
            placeholder="ระบุคำแนะนำ ข้อคิดเห็น หรือรายละเอียดที่ต้องการให้ดำเนินการต่อ..."
        )
        
        new_due = st.date_input(
            "📅 กำหนดวันส่งงานใหม่ (New Due Date) สำหรับคำนวณ KPI *:",
            value=def_due if def_due > datetime.today().date() else datetime.today().date() + timedelta(days=3),
            min_value=datetime.today().date()
        )
        
        submitted = st.form_submit_button("💾 ยืนยันการส่งงานกลับ", type="primary", use_container_width=True)
        
        if submitted:
            if not feedback.strip():
                st.error("กรุณากรอกข้อความแสดงความคิดเห็นต่อผลงานก่อนกดยืนยัน")
            else:
                target_status = "In Progress" if "In Progress" in choice else "Revision"
                try:
                    supabase.table("tasks").update({
                        "status": target_status,
                        "due_date": new_due.strftime("%Y-%m-%d"),
                        "completed_at": None,
                        "is_ontime": None,
                        "submission_note": feedback.strip()
                    }).eq("task_id", tid).execute()
                    
                    action_title = "อนุมัติให้ทำงานต่อ" if target_status == "In Progress" else "ส่งกลับไปแก้ไข"
                    log_msg = f"{feedback.strip()} (กำหนดวันส่งใหม่: {new_due.strftime('%Y-%m-%d')})"
                    supabase.table("task_logs").insert({
                        "task_id": tid,
                        "action": action_title,
                        "performed_by": curr_user.get("username"),
                        "details": log_msg
                    }).execute()
                    
                    clear_all_cache()
                    st.success(f"✅ ส่งงานกลับไปยัง {target_status} เรียบร้อยแล้ว! กำหนดวันส่งใหม่: {new_due.strftime('%Y-%m-%d')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
    
    if st.button("✖️ ปิดหน้าต่าง (ยกเลิก)", key=f"cls_ret_{tid}", use_container_width=True):
        st.rerun()

@st.dialog("🏆 ตรวจรับงานสำเร็จ & ประเมินคะแนน KPI", width="medium")
def show_approve_done_dialog(task, curr_user):
    tid = task.get("task_id")
    title = task.get("title", "")
    assignee = task.get("assignee_name", "-")
    task_type = task.get("task_type", "Project")
    curr_due = task.get("due_date")
    is_ot = task.get("is_ontime")
    
    st.markdown(f"#### 🏆 ตรวจรับงาน: **{title}**")
    st.caption(f"ผู้รับผิดชอบงาน: **{assignee}** | ประเภทงาน: **{task_type}** | กำหนดส่ง: **{curr_due or '-'}**")
    
    ot_badge = "🟢 ส่งตรงเวลา (+10 แต้ม)" if is_ot is True else ("🔴 ส่งเกินกำหนด (-5 แต้ม)" if is_ot is False else "⚪ ตรวจสอบวันส่ง")
    st.markdown(f"**สถานะการส่งงาน:** {ot_badge}")
    st.divider()

    with st.form(f"form_done_{tid}"):
        rating = st.slider("⭐ คะแนนความพึงพอใจต่อผลงาน (1-5 ดาว):", min_value=1, max_value=5, value=5)
        st.caption(f"💡 คะแนนดาวนี้จะนำไปคูณ 4 แต้มสำหรับคำนวณ KPI ({rating} x 4 = {rating * 4} แต้ม)")
        
        feedback = st.text_area(
            "💬 ข้อความแสดงความคิดเห็น / คำชมเชยในการตรวจรับงาน:",
            placeholder="เช่น ผลงานเรียบร้อยตรงตามเป้าหมาย ส่งมอบงานสมบูรณ์..."
        )
        
        submitted = st.form_submit_button("🏆 ยืนยันตรวจรับงานสำเร็จ (ย้ายไป Done)", type="primary", use_container_width=True)
        
        if submitted:
            now_iso = datetime.now().isoformat()
            try:
                if task_type == "Routine":
                    old_due = pd.to_datetime(curr_due) if curr_due else datetime.today()
                    next_due = (old_due + pd.DateOffset(months=1)).strftime('%Y-%m-%d')
                    supabase.table("tasks").update({
                        "status": "To Do",
                        "due_date": next_due,
                        "satisfaction_rating": rating,
                        "completed_at": now_iso,
                        "submission_note": feedback.strip() if feedback else None
                    }).eq("task_id", tid).execute()
                    st.info(f"งาน Routine ได้ขยายรอบกำหนดส่งเดือนถัดไป ({next_due}) เรียบร้อยแล้ว")
                else:
                    supabase.table("tasks").update({
                        "status": "Done",
                        "satisfaction_rating": rating,
                        "completed_at": now_iso,
                        "submission_note": feedback.strip() if feedback else None
                    }).eq("task_id", tid).execute()

                log_details = f"อนุมัติผลงานสำเร็จ ({rating} ดาว) " + (f"- {feedback.strip()}" if feedback else "")
                supabase.table("task_logs").insert({
                    "task_id": tid,
                    "action": "อนุมัติงานสำเร็จ",
                    "performed_by": curr_user.get("username"),
                    "details": log_details
                }).execute()
                
                clear_all_cache()
                st.success(f"✅ ตรวจรับงานสำเร็จเรียบร้อย! งานถูกย้ายไป Done และบันทึกลงในแดชบอร์ดผลงานย้อนหลังประจำเดือนแล้ว")
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    if st.button("✖️ ปิดหน้าต่าง (ยกเลิก)", key=f"cls_dn_{tid}", use_container_width=True):
        st.rerun()

# --- Authentication & Registration Page (โลโก้กะทัดรัด & ลายน้ำ Watermark บนแบคกราว) ---

def show_auth_page():
    # จัดโลโก้ SVV ให้อยู่กึ่งกลางหน้าจออย่างสมบูรณ์แบบ (Center Alignment)
    if LOGO_B64:
        logo_img_tag = f'<img src="data:image/png;base64,{LOGO_B64}" width="120" style="display: block; margin: 0 auto 12px auto; filter: drop-shadow(0 4px 12px rgba(2, 132, 199, 0.22)); object-fit: contain;" />'
    else:
        logo_img_tag = '<div style="font-size: 3rem; margin-bottom: 8px;">📋</div>'
    
    st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; margin-top: 0.5rem; margin-bottom: 1.25rem;">
            {logo_img_tag}
            <h2 style="color: #0369a1; font-weight: 800; font-size: 1.65rem; margin: 0; letter-spacing: 0.5px;">TEAM WORKFLOW SVV</h2>
            <p style="color: #64748b; font-size: 0.92rem; font-weight: 500; margin-top: 5px; margin-bottom: 0;">ระบบจัดการงาน Kanban และประเมินผล KPI ทีมงาน SVV</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register, tab_reset = st.tabs([
            "🔒 เข้าสู่ระบบ", 
            "📝 สมัครสมาชิกใหม่", 
            "🔑 ลืม / เปลี่ยนรหัสผ่าน"
        ])

        with tab_login:
            with st.container(border=True):
                st.markdown("""
                    <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e0f2fe; padding-bottom: 12px; margin-bottom: 18px;">
                        <div>
                            <h3 style="color: #0369a1; margin: 0; font-size: 1.25rem; font-weight: 800; line-height: 1.2;">🔒 เข้าสู่ระบบ</h3>
                            <p style="color: #64748b; margin: 2px 0 0 0; font-size: 0.82rem; font-weight: 500;">TEAM WORKFLOW SVV</p>
                        </div>
                        <span style="font-size: 0.78rem; background: #e0f2fe; color: #0369a1; padding: 4px 12px; border-radius: 20px; font-weight: 700; border: 1px solid #bae6fd;">SVV Portal</span>
                    </div>
                """, unsafe_allow_html=True)
                with st.form("login_form", clear_on_submit=False):
                    username = st.text_input("ชื่อผู้ใช้งาน (Username)", key="l_user")
                    password = st.text_input("รหัสผ่าน (Password)", type="password", key="l_pass")
                    
                    submit_btn = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True, type="primary")
                    if submit_btn:
                        if not username or not password:
                            st.warning("กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
                        else:
                            try:
                                res = supabase.table("app_users").select("*").eq("username", username.strip()).eq("password_hash", password).execute()
                                if res.data and len(res.data) > 0:
                                    user = res.data[0]
                                    is_approved = user.get("is_approved")
                                    if is_approved is False and user.get("role") != "Admin" and user.get("username") != "admin":
                                        st.warning("⏳ บัญชีของคุณอยู่ระหว่างรอ Admin อนุมัติและกำหนดยศ กรุณาติดต่อ Admin")
                                    else:
                                        st.session_state.logged_in = True
                                        st.session_state.user = user
                                        clear_all_cache()
                                        st.rerun()
                                else:
                                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาด: {e}")

        with tab_register:
            with st.container(border=True):
                st.markdown("""
                    <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e0f2fe; padding-bottom: 12px; margin-bottom: 18px;">
                        <div>
                            <h3 style="color: #0369a1; margin: 0; font-size: 1.25rem; font-weight: 800; line-height: 1.2;">📝 ลงทะเบียนพนักงานใหม่</h3>
                            <p style="color: #64748b; margin: 2px 0 0 0; font-size: 0.82rem; font-weight: 500;">TEAM WORKFLOW SVV</p>
                        </div>
                        <span style="font-size: 0.78rem; background: #e0f2fe; color: #0369a1; padding: 4px 12px; border-radius: 20px; font-weight: 700; border: 1px solid #bae6fd;">ลงทะเบียน</span>
                    </div>
                """, unsafe_allow_html=True)
                with st.form("reg_form", clear_on_submit=True):
                    r_user = st.text_input("Username *")
                    r_name = st.text_input("ชื่อ - สกุล *")
                    r_email = st.text_input("Email *")
                    r_phone = st.text_input("เบอร์โทรศัพท์ *")
                    r_p1 = st.text_input("รหัสผ่าน *", type="password")
                    r_p2 = st.text_input("ยืนยันรหัสผ่าน *", type="password")
                    
                    if st.form_submit_button("ส่งคำขอสมัครสมาชิก", use_container_width=True, type="primary"):
                        if not (r_user and r_name and r_email and r_phone and r_p1):
                            st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")
                        elif r_p1 != r_p2:
                            st.error("รหัสผ่านไม่ตรงกัน")
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
                                    "role": "User",
                                    "roles": "ปฏิบัติงาน",
                                    "is_approved": False
                                }
                                try:
                                    supabase.table("app_users").insert(new_u).execute()
                                    clear_all_cache()
                                    st.success("✅ สมัครสำเร็จ! กรุณารอ Admin อนุมัติสิทธิ์เข้าใช้งาน")
                                except Exception as e:
                                    st.error(f"เกิดข้อผิดพลาดในการสมัครสมาชิก: {e}")

        with tab_reset:
            with st.container(border=True):
                st.markdown("""
                    <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e0f2fe; padding-bottom: 12px; margin-bottom: 18px;">
                        <div>
                            <h3 style="color: #0369a1; margin: 0; font-size: 1.25rem; font-weight: 800; line-height: 1.2;">🔑 ตั้งรหัสผ่านใหม่</h3>
                            <p style="color: #64748b; margin: 2px 0 0 0; font-size: 0.82rem; font-weight: 500;">TEAM WORKFLOW SVV</p>
                        </div>
                        <span style="font-size: 0.78rem; background: #e0f2fe; color: #0369a1; padding: 4px 12px; border-radius: 20px; font-weight: 700; border: 1px solid #bae6fd;">กู้คืนรหัส</span>
                    </div>
                """, unsafe_allow_html=True)
                with st.form("reset_form"):
                    rs_user = st.text_input("Username *")
                    rs_contact = st.text_input("Email หรือ เบอร์โทรที่ลงทะเบียนไว้ *")
                    rs_p1 = st.text_input("รหัสผ่านใหม่ *", type="password")
                    rs_p2 = st.text_input("ยืนยันรหัสผ่านใหม่ *", type="password")
                    
                    if st.form_submit_button("บันทึกรหัสผ่านใหม่", use_container_width=True, type="primary"):
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
                                    clear_all_cache()
                                    st.success("✅ แก้ไขรหัสผ่านสำเร็จแล้ว! สามารถเข้าสู่ระบบด้วยรหัสใหม่ได้ทันที")
                                else:
                                    st.error("Email หรือ เบอร์โทรไม่ตรงกับข้อมูลในระบบ")

# --- Module 1: ระบบสั่งการและมอบหมายงาน (เฉพาะยศ 'ระดับสั่งการ') ---

def show_module1_commander_page():
    curr_user = st.session_state.user
    if not user_has_role(curr_user, "ระดับสั่งการ"):
        st.error("⛔ จำกัดสิทธิ์: โมดูลนี้อนุญาตเฉพาะผู้มียศ **'ระดับสั่งการ'** เท่านั้น")
        return

    st.header("🎯 โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)")
    
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
            submitted = st.form_submit_button("บันทึกและส่งงานไปยังกระดาน", use_container_width=True, type="primary")

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
                        clear_all_cache()
                        st.success("✅ มอบหมายงานสำเร็จแล้ว!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

        st.markdown("---")
        st.subheader("📋 รายการงานล่าสุดที่คุณสร้าง (ลบได้หากสร้างผิดพลาด)")
        all_t = fetch_tasks()
        if not all_t.empty and "creator_username" in all_t.columns:
            show_all_m1 = st.checkbox("🔍 แสดงงานทั้งหมดในระบบ (สำหรับผู้สั่งการ/Admin)", value=False, key="m1_show_all")
            if curr_user.get("role") == "Admin" or show_all_m1:
                recent_t = all_t.head(15)
            else:
                recent_t = all_t[all_t["creator_username"] == curr_user.get("username")].head(15)

            if not recent_t.empty:
                for _, r in recent_t.iterrows():
                    with st.container(border=True):
                        c_inf, c_prg, c_del = st.columns([3.5, 1.2, 1.2])
                        with c_inf:
                            st.markdown(f"**{r.get('title')}** | สถานะ: `{r.get('status')}` | ผู้รับผิดชอบ: {r.get('assignee_name') or '-'}")
                            st.caption(f"ผู้สั่งการ: @{r.get('creator_username') or '-'} | กำหนดส่ง: {r.get('due_date') or '-'}")
                        with c_prg:
                            if st.button("📝 ความคืบหน้า", key=f"m1_prg_{r['task_id']}", use_container_width=True):
                                show_task_progress_dialog(r.to_dict(), curr_user)
                        with c_del:
                          with st.expander("🗑️ ลบงาน"):
                            if st.button("ยืนยันลบ", key=f"m1_del_{r['task_id']}", type="primary", use_container_width=True):
                                if delete_task_record(r["task_id"], r.get("title", "")):
                                    st.success("✅ ลบงานสำเร็จ! ลดยอดจำนวนงานเรียบร้อยแล้ว")
                                    st.rerun()
            else:
                st.caption("ยังไม่มีรายการงานที่คุณสร้าง")

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
                    with st.container(border=True):
                        st.markdown(f"**งาน:** {row['title']} | **กำหนดส่ง:** {row.get('due_date') or '-'}")
                        st.write(f"ผู้รับผิดชอบเดิม: `{row.get('assignee_name') or '-'}` ➡️ ส่งต่อให้: `{row.get('handover_to') or '-'}`")
                        st.caption(f"เหตุผล: {row.get('handover_reason') or '-'}")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ อนุมัติส่งต่อ", key=f"ap_ho_{row['task_id']}", use_container_width=True, type="primary"):
                                new_assignee = row.get("handover_to")
                                supabase.table("tasks").update({
                                    "assignee_name": new_assignee,
                                    "assignees": new_assignee,
                                    "handover_status": "Approved"
                                }).eq("task_id", row["task_id"]).execute()
                                log_task_action(row["task_id"], "อนุมัติส่งต่องาน", curr_user.get("username"), f"ส่งต่อให้ {new_assignee}")
                                clear_all_cache()
                                st.rerun()
                        with c2:
                            if st.button("❌ ปฏิเสธ", key=f"rj_ho_{row['task_id']}", use_container_width=True):
                                supabase.table("tasks").update({"handover_status": "Rejected"}).eq("task_id", row["task_id"]).execute()
                                clear_all_cache()
                                st.rerun()
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
                st.info("ไม่มีงานที่รอการตรวจรับในขณะนี้")
            else:
                for _, row in reviews.iterrows():
                    with st.container(border=True):
                        ot_badge = "🟢 ส่งตรงเวลา" if row.get("is_ontime") is True else ("🔴 ส่งเกินกำหนด" if row.get("is_ontime") is False else "⚪ รอตรวจสอบวันส่ง")
                        st.markdown(f"**ชื่องาน:** {row['title']} | {ot_badge}")
                        st.write(f"ผู้รับผิดชอบ: **{row.get('assignee_name') or '-'}** | ผลงานที่ส่ง: {row.get('submission_note') or row.get('attachment_url') or '-'}")
                        
                        c_bt1, c_bt2, c_bt3 = st.columns([1.5, 1.5, 1])
                        with c_bt1:
                            if st.button("🏆 ตรวจรับงานสำเร็จ (Done)", key=f"dn_{row['task_id']}", use_container_width=True, type="primary"):
                                show_approve_done_dialog(row.to_dict(), curr_user)
                        with c_bt2:
                            if st.button("↩️ ส่งกลับไป In Progress / แก้ไข", key=f"rv_{row['task_id']}", use_container_width=True):
                                show_return_task_dialog(row.to_dict(), curr_user)
                        with c_bt3:
                            if st.button("📝 ความคืบหน้า", key=f"m1_rev_prg_{row['task_id']}", use_container_width=True):
                                show_task_progress_dialog(row.to_dict(), curr_user)
        else:
            st.info("ยังไม่มีข้อมูลงานในระบบ")

    with sub4:
        st.subheader("แบบฟอร์มเพิ่มหรือลดคะแนน KPI")
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

                if st.form_submit_button("บันทึกการปรับคะแนน", use_container_width=True, type="primary"):
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
                        clear_all_cache()
                        st.success(f"✅ บันทึกคะแนน {calc_p:+} ให้ @{adj_user} เรียบร้อยแล้ว!")

# --- Module 2: กระดานงาน (แบบตารางกระชับทีละบรรทัด อ่านง่าย โหลดเร็วมาก) ---

def show_module2_kanban_page():
    curr_user = st.session_state.user
    curr_username = curr_user.get("username")
    is_commander = user_has_role(curr_user, "ระดับสั่งการ")

    st.header("📋 โมดูลที่ 2: กระดานงาน (Task Board)")
    render_task_board(curr_user, curr_username, is_commander)

def render_task_board(curr_user, curr_username, is_commander):
    df = fetch_tasks()

    # --- ตัวกรองผู้รับผิดชอบ & วันที่กำหนดส่งจากปฏิทิน ---
    operators = fetch_operators()
    assignee_options = ["ทั้งหมด"] + [op["username"] for op in operators]
    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.5, 1.2, 1, 1])
        with c1:
            f_assignee = st.selectbox("👤 ผู้รับผิดชอบ:", assignee_options, key="f_assignee")
        with c2:
            use_date = st.checkbox("กรองตามวันกำหนดส่ง", value=False)
            f_date = st.date_input("📅 วันที่กำหนดส่ง:", value=datetime.today().date(), disabled=not use_date)
        with c3:
            f_status = st.selectbox("📌 สถานะ:", ["ทั้งหมด", "To Do", "In Progress", "In Review", "Revision", "Done"])
        with c4:
            f_type = st.selectbox("🏷️ ประเภท:", ["ทั้งหมด", "Project", "Routine"])

    # กรองข้อมูล
    filtered_df = df.copy() if not df.empty else pd.DataFrame()
    if not filtered_df.empty:
        if f_assignee != "ทั้งหมด" and "assignee_name" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["assignee_name"].fillna("").str.contains(f_assignee)]
        if use_date and f_date and "due_date" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["due_date"] == f_date.strftime("%Y-%m-%d")]
        if f_status != "ทั้งหมด" and "status" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["status"] == f_status]
        if f_type != "ทั้งหมด" and "task_type" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["task_type"] == f_type]

    if filtered_df.empty:
        st.info("ไม่พบรายการงานที่ตรงตามเงื่อนไขตัวกรอง")
        return

    # มุมมองแสดงผล
    view_style = st.radio("รูปแบบมุมมอง:", ["📄 แสดงเป็นบรรทัดกระชับ (Compact List - อ่านง่าย โหลดไว)", "📊 แสดงแยก 5 ช่องสถานะ (Kanban Columns)"], horizontal=True)

    # 1. แสดงเป็นรายการทีละบรรทัด (โหลดไวมาก อ่านง่าย)
    if "Compact List" in view_style:
        total_matched = len(filtered_df)
        st.markdown(f"**พบรายการงานทั้งหมด:** `{total_matched} รายการ`")

        for _, row in filtered_df.iterrows():
            status = row.get("status", "To Do")
            due_str = row.get("due_date") or "-"
            
            stat_color = "badge-todo"
            if status == "In Progress": stat_color = "badge-progress"
            elif status == "In Review": stat_color = "badge-review"
            elif status == "Revision": stat_color = "badge-revision"
            elif status == "Done": stat_color = "badge-done"

            alert_tag = ""
            if status != "Done" and row.get("due_date"):
                try:
                    diff = (pd.to_datetime(row["due_date"]).date() - datetime.today().date()).days
                    if diff < 0:
                        alert_tag = f'<span class="badge-status badge-overdue">🚨 เกิน {abs(diff)} วัน</span>'
                    elif diff <= 3:
                        alert_tag = f'<span class="badge-status badge-warning">⚠️ เหลือ {diff} วัน</span>'
                except Exception:
                    pass

            handover_tag = '<span class="badge-status" style="background:#ffedd5; color:#c2410c;">🔄 รออนุมัติส่งต่อ</span>' if row.get("handover_status") == "Pending" else ""

            with st.container(border=True):
                col_info, col_act = st.columns([4.4, 1.1])
                with col_info:
                    st.markdown(f"""
                        <div style="font-size: 1.05rem; font-weight: 700; color: #1e293b;">
                            {row.get('title')} 
                            <span class="badge-status {stat_color}">{status}</span>
                            <span class="badge-status" style="background:#f0f9ff; color:#0369a1; border:1px solid #bae6fd;">{row.get('task_type')}</span>
                            {alert_tag} {handover_tag}
                        </div>
                        <div style="font-size: 0.85rem; color: #64748b; margin-top: 4px;">
                            👑 ผู้สั่งการ: <b>@{row.get('creator_username') or '-'}</b> | 
                            👤 ผู้รับผิดชอบ: <b>{row.get('assignee_name') or '-'}</b> | 
                            📅 กำหนดส่ง: <b>{due_str}</b>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col_act:
                    with st.popover("⚙️ จัดการงาน", use_container_width=True):
                        st.markdown(f"**ชื่องาน:** {row.get('title')}")
                        st.caption(f"รายละเอียด: {row.get('description') or 'ไม่มีรายละเอียด'}")
                        if row.get("attachment_url"):
                            st.markdown(f"📎 [ไฟล์แนบ]({row['attachment_url']})")

                        st.divider()

                        # 1. ปุ่มเปิดดูความคืบหน้า & สรุปผลงาน
                        if st.button("📝 รายงานความคืบหน้า & สรุปผลงาน", key=f"pop_prog_{row['task_id']}", use_container_width=True):
                            show_task_progress_dialog(row.to_dict(), curr_user)

                        # 2. ส่วนส่งต่องานระหว่างพนักงาน (ยศปฏิบัติงาน)
                        if status != 'Done':
                            st.divider()
                            if row.get("handover_status") == "Pending":
                                st.info(f"⏳ **สถานะ:** อยู่ระหว่างรอผู้มอบหมายอนุมัติส่งต่องานให้ **@{row.get('handover_to')}**")
                                if is_commander or curr_user.get("role") == "Admin" or curr_username == "admin":
                                    c_ap1, c_ap2 = st.columns(2)
                                    with c_ap1:
                                        if st.button("✅ อนุมัติส่งต่อ", key=f"pop_ap_ho_{row['task_id']}", use_container_width=True, type="primary"):
                                            new_assignee = row.get("handover_to")
                                            supabase.table("tasks").update({
                                                "assignee_name": new_assignee,
                                                "assignees": new_assignee,
                                                "handover_status": "Approved"
                                            }).eq("task_id", row["task_id"]).execute()
                                            log_task_action(row["task_id"], "อนุมัติส่งต่องาน", curr_username, f"อนุมัติส่งต่อให้ {new_assignee}")
                                            clear_all_cache()
                                            st.success(f"อนุมัติส่งต่องานให้ @{new_assignee} แล้ว!")
                                            st.rerun()
                                    with c_ap2:
                                        if st.button("❌ ปฏิเสธ", key=f"pop_rj_ho_{row['task_id']}", use_container_width=True):
                                            supabase.table("tasks").update({"handover_status": "Rejected"}).eq("task_id", row["task_id"]).execute()
                                            log_task_action(row["task_id"], "ปฏิเสธการส่งต่องาน", curr_username, "ปฏิเสธคำขอ")
                                            clear_all_cache()
                                            st.rerun()
                                else:
                                    if st.button("❌ ยกเลิกคำขอส่งต่อ", key=f"pop_cn_ho_{row['task_id']}", use_container_width=True):
                                        supabase.table("tasks").update({"handover_status": "None", "handover_to": None, "handover_reason": None}).eq("task_id", row["task_id"]).execute()
                                        clear_all_cache()
                                        st.rerun()
                            else:
                                with st.expander("🤝 ส่งต่องานให้เพื่อนร่วมงาน (ยศปฏิบัติงาน)"):
                                    st.caption("เลือกเพื่อนร่วมงานที่ต้องการส่งต่องานให้ และระบุเหตุผลเพื่อรอผู้มอบหมายอนุมัติ")
                                    colleague_ops = [op["username"] for op in operators if op["username"] != curr_username]
                                    if not colleague_ops:
                                        st.caption("ไม่มีรายชื่อเพื่อนร่วมงานอื่นในระบบ")
                                    else:
                                        to_op = st.selectbox("เลือกผู้รับมอบหมายต่อ:", colleague_ops, key=f"ho_{row['task_id']}")
                                        ho_r = st.text_input("เหตุผลการส่งต่องาน *:", key=f"hr_{row['task_id']}")
                                        if st.button("📤 ยืนยันส่งต่องาน (รออนุมัติ)", key=f"hbtn_{row['task_id']}", use_container_width=True, type="primary"):
                                            if not ho_r.strip():
                                                st.error("กรุณาระบุเหตุผลการส่งต่องาน")
                                            else:
                                                supabase.table("tasks").update({
                                                    "handover_to": to_op,
                                                    "handover_reason": ho_r.strip(),
                                                    "handover_status": "Pending"
                                                }).eq("task_id", row["task_id"]).execute()
                                                log_task_action(row["task_id"], "ขอส่งต่องาน", curr_username, f"ขอส่งต่อให้ @{to_op} (เหตุผล: {ho_r.strip()}) - รอผู้มอบหมายอนุมัติ")
                                                clear_all_cache()
                                                st.success("✅ ส่งคำขอส่งต่องานแล้ว! กำลังรอผู้มอบหมายอนุมัติ")
                                                st.rerun()

                        # 3. ปุ่มดำเนินงานของผู้ปฏิบัติงาน
                        if status in ['To Do', 'Revision']:
                            st.divider()
                            if st.button("🚀 เริ่มดำเนินงาน (In Progress)", key=f"btn_st_{row['task_id']}", use_container_width=True, type="primary"):
                                supabase.table("tasks").update({"status": "In Progress"}).eq("task_id", row["task_id"]).execute()
                                log_task_action(row["task_id"], "เริ่มดำเนินงาน", curr_username, "ย้ายไป In Progress")
                                clear_all_cache()
                                st.rerun()

                        if status == 'In Progress':
                            st.divider()
                            st.caption("📤 **ส่งงานเพื่อรอผู้มอบหมายตรวจรับ:**")
                            s_note = st.text_input("ลิงก์ส่งงาน / หมายเหตุสรุปผลงาน:", key=f"nt_{row['task_id']}")
                            if st.button("✅ ส่งงานเพื่อรออนุมัติ", key=f"sub_{row['task_id']}", use_container_width=True, type="primary"):
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
                                log_task_action(row["task_id"], "ส่งงานเพื่อรออนุมัติ", curr_username, f"หมายเหตุ: {s_note}")
                                clear_all_cache()
                                st.success("ส่งงานสำเร็จ! งานย้ายไป In Review แล้ว")
                                st.rerun()

                        # 4. ปุ่มสำหรับผู้สั่งการ (ตรวจรับ / ย้ายสถานะ)
                        if is_commander or curr_user.get("role") == "Admin" or curr_username == "admin":
                            st.divider()
                            st.caption("👑 **สิทธิ์ผู้สั่งการ: ตรวจรับและย้ายสถานะงาน**")
                            if status == "In Review":
                                if st.button("🏆 ตรวจรับผ่าน (ย้ายไป Done)", key=f"c_dn_{row['task_id']}", type="primary", use_container_width=True):
                                    show_approve_done_dialog(row.to_dict(), curr_user)
                                if st.button("↩️ ส่งกลับ In Progress / แก้ไข", key=f"c_rt_{row['task_id']}", use_container_width=True):
                                    show_return_task_dialog(row.to_dict(), curr_user)
                            all_stats = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
                            new_s = st.selectbox("ย้ายไปสถานะ:", all_stats, index=all_stats.index(status), key=f"cmd_s_{row['task_id']}")
                            if st.button("อัปเดตสถานะงาน", key=f"cmd_upd_{row['task_id']}", use_container_width=True):
                                if new_s in ["In Progress", "Revision"] and status == "In Review":
                                    show_return_task_dialog(row.to_dict(), curr_user)
                                elif new_s == "Done":
                                    show_approve_done_dialog(row.to_dict(), curr_user)
                                else:
                                    supabase.table("tasks").update({"status": new_s}).eq("task_id", row["task_id"]).execute()
                                    log_task_action(row["task_id"], "ย้ายสถานะ", curr_username, f"ย้ายไป {new_s}")
                                    clear_all_cache()
                                    st.rerun()

                        # 5. ปุ่มลบงาน (Delete Task)
                        can_del = is_commander or (curr_user.get("role") == "Admin") or (curr_username == "admin") or (row.get("creator_username") == curr_username) or (curr_username in str(row.get("assignee_name", "")))
                        if can_del:
                            st.divider()
                            with st.expander("🗑️ ลบงานนี้ (กรณีสร้างผิดพลาด / ไม่ได้ทำ)"):
                                st.caption(f"ต้องการลบงาน: **{row.get('title')}** หรือไม่? ระบบจะตัดยอดงานนี้ออกจากสถิติและลดคะแนน KPI ทันที")
                                if st.button("❌ ยืนยันการลบงานถาวร", key=f"del_task_{row['task_id']}", type="primary", use_container_width=True):
                                    if delete_task_record(row["task_id"], row.get("title", "")):
                                        st.success("✅ ลบงานเรียบร้อยแล้ว! ลดยอดจำนวนงานและคะแนน KPI ทันที")
                                        st.rerun()

    # 2. แสดงแยก 5 ช่องสถานะ (Kanban Columns)
    else:
        statuses = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
        cols = st.columns(len(statuses))
        for idx, status in enumerate(statuses):
            with cols[idx]:
                status_df = filtered_df[filtered_df['status'] == status] if 'status' in filtered_df.columns else pd.DataFrame()
                st.markdown(f"#### {status} ({len(status_df)})")
                for _, row in status_df.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row.get('title')}**")
                        st.caption(f"👤 {row.get('assignee_name') or '-'}\n📅 {row.get('due_date') or '-'}")
                        if row.get("handover_status") == "Pending":
                            st.markdown(f'<span class="badge-status" style="background:#ffedd5; color:#c2410c; font-weight:700;">🔄 รออนุมัติส่งต่อ (@{row.get("handover_to")})</span>', unsafe_allow_html=True)
                        
                        with st.popover("⚙️ จัดการ / ความคืบหน้า", use_container_width=True):
                            st.markdown(f"**ชื่องาน:** {row.get('title')}")
                            if st.button("📝 รายงานความคืบหน้า & สรุปผลงาน", key=f"k_pop_prg_{row['task_id']}", use_container_width=True):
                                show_task_progress_dialog(row.to_dict(), curr_user)
                            
                            # ส่งต่องานระหว่างพนักงาน
                            if status != 'Done':
                                st.divider()
                                if row.get("handover_status") == "Pending":
                                    st.info(f"⏳ **รออนุมัติส่งต่อให้:** @{row.get('handover_to')}")
                                    if is_commander or curr_user.get("role") == "Admin" or curr_username == "admin":
                                        ck_ap1, ck_ap2 = st.columns(2)
                                        with ck_ap1:
                                            if st.button("✅ อนุมัติ", key=f"k_ap_{row['task_id']}", use_container_width=True, type="primary"):
                                                new_assignee = row.get("handover_to")
                                                supabase.table("tasks").update({
                                                    "assignee_name": new_assignee,
                                                    "assignees": new_assignee,
                                                    "handover_status": "Approved"
                                                }).eq("task_id", row["task_id"]).execute()
                                                log_task_action(row["task_id"], "อนุมัติส่งต่องาน", curr_username, f"ส่งต่อให้ {new_assignee}")
                                                clear_all_cache()
                                                st.rerun()
                                        with ck_ap2:
                                            if st.button("❌ ปฏิเสธ", key=f"k_rj_{row['task_id']}", use_container_width=True):
                                                supabase.table("tasks").update({"handover_status": "Rejected"}).eq("task_id", row["task_id"]).execute()
                                                clear_all_cache()
                                                st.rerun()
                                else:
                                    with st.expander("🤝 ส่งต่องานให้เพื่อนร่วมงาน (ยศปฏิบัติงาน)"):
                                        colleague_ops_k = [op["username"] for op in operators if op["username"] != curr_username]
                                        if colleague_ops_k:
                                            to_op_k = st.selectbox("เลือกผู้รับมอบหมายต่อ:", colleague_ops_k, key=f"k_ho_{row['task_id']}")
                                            ho_r_k = st.text_input("เหตุผลการส่งต่องาน *:", key=f"k_hr_{row['task_id']}")
                                            if st.button("📤 ยืนยันส่งต่องาน", key=f"k_hbtn_{row['task_id']}", use_container_width=True, type="primary"):
                                                if ho_r_k.strip():
                                                    supabase.table("tasks").update({
                                                        "handover_to": to_op_k,
                                                        "handover_reason": ho_r_k.strip(),
                                                        "handover_status": "Pending"
                                                    }).eq("task_id", row["task_id"]).execute()
                                                    log_task_action(row["task_id"], "ขอส่งต่องาน", curr_username, f"ส่งต่อให้ @{to_op_k}")
                                                    clear_all_cache()
                                                    st.rerun()

                            # ตรวจรับงานและย้ายสถานะสำหรับระดับสั่งการ
                            if is_commander or curr_user.get("role") == "Admin" or curr_username == "admin":
                                st.divider()
                                st.caption("👑 **ตรวจรับงาน / ย้ายสถานะ:**")
                                if status == "In Review":
                                    if st.button("🏆 ตรวจรับผ่าน ➡️ Done", key=f"k_done_{row['task_id']}", type="primary", use_container_width=True):
                                        show_approve_done_dialog(row.to_dict(), curr_user)
                                    if st.button("↩️ ส่งกลับ ➡️ In Progress / แก้ไข", key=f"k_ret_{row['task_id']}", use_container_width=True):
                                        show_return_task_dialog(row.to_dict(), curr_user)
                                all_stats = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
                                target_s = st.selectbox("ย้ายไปสถานะ:", all_stats, index=all_stats.index(status), key=f"k_sel_{row['task_id']}")
                                if st.button("ยืนยันย้ายสถานะ", key=f"k_btn_mv_{row['task_id']}", use_container_width=True):
                                    if target_s in ["In Progress", "Revision"] and status == "In Review":
                                        show_return_task_dialog(row.to_dict(), curr_user)
                                    elif target_s == "Done":
                                        show_approve_done_dialog(row.to_dict(), curr_user)
                                    else:
                                        supabase.table("tasks").update({"status": target_s}).eq("task_id", row["task_id"]).execute()
                                        clear_all_cache()
                                        st.rerun()

                            can_del_k = is_commander or (curr_user.get("role") == "Admin") or (curr_username == "admin") or (row.get("creator_username") == curr_username) or (curr_username in str(row.get("assignee_name", "")))
                            if can_del_k:
                                st.divider()
                                with st.expander("🗑️ ลบงาน"):
                                    if st.button("ยืนยันลบถาวร", key=f"k_del_{row['task_id']}", type="primary", use_container_width=True):
                                        if delete_task_record(row["task_id"], row.get("title", "")):
                                            st.success("ลบงานสำเร็จ!")
                                            st.rerun()

# --- Module 3: แดชบอร์ดคะแนน KPI & รายงานผลงานเก่าเรียกดูย้อนหลัง ---

@st.cache_data(ttl=120)
def compute_kpi_summary_df(tasks_records, operators_records, adjustments_records):
    tasks_df = pd.DataFrame(tasks_records) if tasks_records else pd.DataFrame()
    adjustments = adjustments_records or []
    kpi_records = []
    for op in operators_records:
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

        # หากยังไม่มีงานที่เสร็จ (d_count == 0) จะยังไม่มีคะแนนดาวประเมิน และไม่ได้รับแต้มความพึงพอใจล่วงหน้า
        if d_count > 0:
            avg_r = sum(ratings) / len(ratings) if ratings else 5.0
            satisfaction_pts = avg_r * 4
        else:
            avg_r = 0.0
            satisfaction_pts = 0.0

        user_adjs = [a for a in adjustments if a.get("username") == uname]
        man_pts = sum(float(a.get("points", 0)) for a in user_adjs)
        
        tot_kpi = max(0, round((d_count * 5) + (ontime_c * 10) - (late_c * 5) + satisfaction_pts + man_pts, 1))

        kpi_records.append({
            "username": uname,
            "fullname": fullname,
            "total_tasks": tot,
            "done_tasks": d_count,
            "ontime_count": ontime_c,
            "late_count": late_c,
            "avg_rating": round(avg_r, 1) if d_count > 0 else 0.0,
            "manual_points": man_pts,
            "total_kpi": tot_kpi
        })

    kpi_df = pd.DataFrame(kpi_records)
    if not kpi_df.empty:
        kpi_df = kpi_df.sort_values(by="total_kpi", ascending=False).reset_index(drop=True)
    return kpi_df

def show_module3_kpi_dashboard():
    import plotly.express as px
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
    m3.metric("🔍 รอตรวจรับ", in_rev)
    m4.metric("✅ เสร็จสิ้น", done_c)

    # จัดการและลบงานในระบบโดยตรง (เพื่อให้สามารถตัดยอดงานที่สร้างผิดพลาดได้ทันที)
    if not tasks_df.empty:
        with st.expander("🛠️ ตรวจสอบ / ลบงานในระบบ (หากสร้างผิดพลาดหรือไม่ได้ทำ เพื่อตัดยอดจำนวนงานออกทันที)"):
            st.caption("💡 เมื่อลบงาน งานจะถูกตัดออกจากระบบและลดจำนวนงานในแดชบอร์ด KPI ทันที")
            for _, r in tasks_df.iterrows():
                with st.container(border=True):
                    c_info, c_prg, c_del = st.columns([3.5, 1.2, 1.2])
                    with c_info:
                        st.markdown(f"**{r.get('title')}** | สถานะ: `{r.get('status')}` | ผู้รับผิดชอบ: **{r.get('assignee_name') or '-'}**")
                        st.caption(f"ผู้สั่งการ: @{r.get('creator_username') or '-'} | กำหนดส่ง: {r.get('due_date') or '-'}")
                    with c_prg:
                        if st.button("📝 ความคืบหน้า", key=f"m3_prg_{r['task_id']}", use_container_width=True):
                            show_task_progress_dialog(r.to_dict(), curr_user)
                    with c_del:
                        if st.button("🗑️ ยืนยันลบงานนี้", key=f"m3_del_{r['task_id']}", type="primary", use_container_width=True):
                            if delete_task_record(r["task_id"], r.get("title", "")):
                                st.success(f"✅ ลบงาน '{r.get('title')}' สำเร็จ! ลดยอดจำนวนงานเรียบร้อยแล้ว")
                                st.rerun()

    st.divider()

    tab_kpi, tab_history = st.tabs([
        "📈 คะแนน KPI พนักงาน (Leaderboard)", 
        "📜 รายงานผลงานเก่า & เรียกดูย้อนหลัง (Historical Work Report)"
    ])

    with tab_kpi:
        st.caption("💡 **เกณฑ์การคำนวณคะแนน KPI:** งานที่เสร็จแล้ว (Done) +5 แต้ม | ส่งตรงเวลา +10 แต้ม | ส่งล่าช้า -5 แต้ม | คะแนนความพึงพอใจ (1-5 ดาว) x 4 แต้ม | แต้มพิเศษ (+/-) *(หมายเหตุ: หากยังไม่มีงานที่ทำเสร็จ จะยังไม่ได้รับคะแนนดาวความพึงพอใจ)*")
        tasks_records = tasks_df.to_dict('records') if not tasks_df.empty else []
        kpi_df = compute_kpi_summary_df(tasks_records, operators, adjustments)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📈 อันดับคะแนน KPI รวม")
            if not kpi_df.empty:
                fig1 = px.bar(
                    kpi_df, 
                    x="fullname", 
                    y="total_kpi", 
                    labels={"fullname": "พนักงาน", "total_kpi": "คะแนน KPI รวม"},
                    color_discrete_sequence=['#0284c7']
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
                    color_discrete_map={"ontime_count": "#0284c7", "late_count": "#f87171"}
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
                    if st.form_submit_button("บันทึกการปรับคะแนน", type="primary"):
                        clean_tp = "ความดีความชอบ" if points_e >= 0 else "ความผิดพลาด"
                        supabase.table("kpi_adjustments").insert({
                            "username": target_e,
                            "points": points_e,
                            "reason_type": clean_tp,
                            "description": reason_e,
                            "created_by": curr_user.get("username")
                        }).execute()
                        clear_all_cache()
                        st.success("บันทึกคะแนนเรียบร้อยแล้ว!")
                        st.rerun()

    # 2. รายงานผลงานเก่า & เรียกดูย้อนหลัง (แยกรายเดือน & สรุป KPI)
    with tab_history:
        st.subheader("📜 รายงานผลงานเก่า & เรียกดูย้อนหลังประจำเดือน")
        st.caption("ตรวจสอบว่าพนักงานคนไหน ทำงานอะไรสำเร็จไปแล้วบ้าง พร้อมรายละเอียดคะแนนความพึงพอใจและแต้ม KPI แยกรายเดือน")

        ch1, ch2, ch3 = st.columns([1.5, 1.2, 1.2])
        with ch1:
            filter_emp = st.selectbox("👤 เลือกพนักงานที่ต้องการดูรีพอร์ต:", ["ทุกคน"] + [op["username"] for op in operators], key="hist_emp_sel")
        with ch2:
            available_months = ["ทุกเดือน"] + get_available_months(tasks_df)
            filter_month = st.selectbox("📅 ประจำเดือน:", available_months, key="hist_month_sel")
        with ch3:
            filter_stat = st.selectbox("📌 สถานะงาน:", ["เฉพาะงานที่สำเร็จแล้ว (Done)", "งานทุกสถานะ"], key="hist_stat_sel")

        rep_df = tasks_df.copy() if not tasks_df.empty else pd.DataFrame()
        if not rep_df.empty:
            if filter_stat == "เฉพาะงานที่สำเร็จแล้ว (Done)":
                rep_df = rep_df[rep_df["status"] == "Done"]
            if filter_emp != "ทุกคน":
                rep_df = rep_df[rep_df["assignee_name"].fillna("").str.contains(filter_emp)]
            if filter_month != "ทุกเดือน":
                rep_df = rep_df[rep_df.apply(lambda r: task_matches_month(r, filter_month), axis=1)]

        if rep_df.empty:
            st.info(f"ℹ️ ไม่มีประวัติผลงานตามเงื่อนไขที่เลือก (เดือน: {filter_month} | พนักงาน: {filter_emp})")
        else:
            # การ์ดสรุปเมตริกประจำเดือน/ประจำเงื่อนไข
            done_sub = rep_df[rep_df["status"] == "Done"] if "status" in rep_df.columns else pd.DataFrame()
            cnt_done = len(done_sub)
            cnt_ot = len(done_sub[done_sub["is_ontime"] == True]) if not done_sub.empty and "is_ontime" in done_sub.columns else 0
            cnt_late = len(done_sub[done_sub["is_ontime"] == False]) if not done_sub.empty and "is_ontime" in done_sub.columns else 0
            ratings = [r for r in done_sub["satisfaction_rating"].dropna() if r > 0] if not done_sub.empty and "satisfaction_rating" in done_sub.columns else []
            avg_rt = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
            total_kpi_pts = (cnt_done * 5) + (cnt_ot * 10) - (cnt_late * 5) + int(avg_rt * 4)

            with st.container(border=True):
                st.markdown(f"##### 📊 สรุปภาพรวมผลงานย้อนหลัง: `{filter_month}` | พนักงาน: `{filter_emp}`")
                sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                sc1.metric("🏆 งานที่เสร็จ", f"{cnt_done} งาน")
                sc2.metric("🟢 ส่งตรงเวลา", f"{cnt_ot} งาน")
                sc3.metric("🔴 ส่งล่าช้า", f"{cnt_late} งาน")
                sc4.metric("⭐ ดาวเฉลี่ย", f"{avg_rt}/5" if avg_rt > 0 else "-")
                sc5.metric("💎 แต้ม KPI งานนี้", f"+{total_kpi_pts}" if total_kpi_pts >= 0 else str(total_kpi_pts))

            rep_list = []
            thai_months = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            for _, r in rep_df.iterrows():
                is_ot = r.get("is_ontime")
                ot_str = "🟢 ตรงเวลา (+10)" if is_ot is True else ("🔴 ล่าช้า (-5)" if is_ot is False else "⚪ ปกติ")
                rating = r.get("satisfaction_rating") or 0
                
                base_pt = 5 if r.get("status") == "Done" else 0
                time_pt = 10 if is_ot is True else (-5 if is_ot is False else 0)
                star_pt = rating * 4
                task_kpi = base_pt + time_pt + star_pt

                comp_dt = r.get("completed_at")
                month_display = "-"
                if comp_dt:
                    try:
                        p_dt = pd.to_datetime(comp_dt)
                        month_display = f"{thai_months[p_dt.month]} {p_dt.year + 543}"
                    except Exception:
                        pass
                elif r.get("due_date"):
                    try:
                        p_dt = pd.to_datetime(r["due_date"])
                        month_display = f"{thai_months[p_dt.month]} {p_dt.year + 543}"
                    except Exception:
                        pass

                rep_list.append({
                    "ชื่องาน": r.get("title"),
                    "ผู้รับผิดชอบงาน": r.get("assignee_name") or "-",
                    "ผู้สั่งการ": r.get("creator_username") or r.get("requester_name") or "-",
                    "ประเภท": r.get("task_type"),
                    "กำหนดส่ง": r.get("due_date") or "-",
                    "วันที่ส่งงานจริง": str(r.get("completed_at") or "-")[:10],
                    "ประจำเดือน": month_display,
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
                mime="text/csv",
                type="primary"
            )

            with st.expander("🔍 ดูความคืบหน้า / ลบงานในรายงานนี้ (กรณีพบงานที่สร้างผิดพลาด)"):
                for _, r in rep_df.iterrows():
                    c_h1, c_hp, c_h2 = st.columns([3.5, 1.2, 1.2])
                    with c_h1:
                        st.markdown(f"**{r.get('title')}** | สถานะ: `{r.get('status')}` | ผู้รับผิดชอบ: {r.get('assignee_name') or '-'}")
                    with c_hp:
                        if st.button("📝 ความคืบหน้า", key=f"rep_prg_{r['task_id']}", use_container_width=True):
                            show_task_progress_dialog(r.to_dict(), curr_user)
                    with c_h2:
                        if st.button("ยืนยันลบ", key=f"rep_del_{r['task_id']}", use_container_width=True):
                            if delete_task_record(r["task_id"], r.get("title", "")):
                                st.success("✅ ลบงานสำเร็จ! ลดยอดจำนวนงานแล้ว")
                                st.rerun()

# --- Admin Panel: จัดการผู้ใช้งาน ---

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
                with st.container(border=True):
                    st.write(f"**ชื่อ-สกุล:** {pu.get('fullname') or '-'} | **Username:** @{pu.get('username')}")
                    st.caption(f"Email: {pu.get('email') or '-'} | โทร: {pu.get('phone') or '-'}")
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        new_r = st.multiselect(f"กำหนดยศให้ @{pu.get('username')}:", ["ระดับสั่งการ", "ปฏิบัติงาน"], default=["ปฏิบัติงาน"], key=f"r_{pu['user_id']}")
                    with c2:
                        if st.button("อนุมัติและเปิดใช้งาน", key=f"ap_{pu['user_id']}", use_container_width=True, type="primary"):
                            supabase.table("app_users").update({
                                "is_approved": True,
                                "roles": ", ".join(new_r) if new_r else "ปฏิบัติงาน"
                            }).eq("user_id", pu["user_id"]).execute()
                            clear_all_cache()
                            st.success(f"อนุมัติ @{pu.get('username')} เรียบร้อยแล้ว!")
                            st.rerun()
                        if st.button("ลบคำขอ", key=f"dl_{pu['user_id']}", use_container_width=True):
                            supabase.table("app_users").delete().eq("user_id", pu["user_id"]).execute()
                            clear_all_cache()
                            st.rerun()

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
                        clear_all_cache()
                        st.success("บันทึกยศสำเร็จ!")
                        st.rerun()
                with b2:
                    if u.get("username") != "admin":
                        if st.button("ลบผู้ใช้", key=f"dl_u_{u['user_id']}"):
                            supabase.table("app_users").delete().eq("user_id", u["user_id"]).execute()
                            clear_all_cache()
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
    
    # แสดงโลโก้ใน Sidebar
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_file = None
    for cand in ["svv_logo_header.png", "logo.jpg", os.path.join(base_dir, "svv_logo_header.png"), os.path.join(base_dir, "logo.jpg")]:
        if os.path.exists(cand):
            logo_file = cand
            break
    if logo_file:
        sb_c1, sb_c2 = st.sidebar.columns([1, 2.5])
        with sb_c1:
            st.image(logo_file, width=48)
        with sb_c2:
            st.markdown(f"**{curr_fullname}**<br/><small style='color:#64748b;'>@{curr_username}</small>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: **{curr_fullname}**")
        st.sidebar.caption(f"Username: @{curr_username}")
    
    badge_html = ""
    if is_admin:
        badge_html += '<span class="badge-status badge-overdue">🛡️ Admin</span> '
    for r in curr_roles:
        if r == "ระดับสั่งการ":
            badge_html += '<span class="badge-status badge-review">👑 สั่งการ</span> '
        elif r == "ปฏิบัติงาน":
            badge_html += '<span class="badge-status badge-done">🛠️ ปฏิบัติงาน</span> '
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
    col_sb1, col_sb2 = st.sidebar.columns(2)
    with col_sb1:
        if st.sidebar.button("🔄 ซิงค์ข้อมูล", use_container_width=True):
            clear_all_cache()
            st.rerun()
    with col_sb2:
        if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            clear_all_cache()
            st.rerun()

    if page == "โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)":
        show_module1_commander_page()
    elif page == "โมดูลที่ 2: กระดานงาน (Kanban Board)":
        show_module2_kanban_page()
    elif page == "โมดูลที่ 3: แดชบอร์ดคะแนน KPI":
        show_module3_kpi_dashboard()
    elif page == "⚙️ ผู้ดูแลระบบ (Admin Panel)":
        show_admin_panel()
