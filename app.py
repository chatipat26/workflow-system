# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from client import supabase

# --- UI/UX & CSS Styling ---
# ใช้โทนสี: Rose Gold (#e0b8b8), Muted Pastel Blue (#b4c6e7), Pastel Champagne (#f5e6b3)
st.set_page_config(page_title="Team Workflow Hub", layout="wide")
st.markdown("""
    <style>
    /* ปรับแต่งพื้นหลังและฟอนต์ */
    .stApp {
        background-color: #fcfcfc;
    }
    
    /* ตกแต่งการ์ดงาน (Kanban Board) ให้มีมุมโค้งมน */
    .task-card {
        background-color: #b4c6e7; /* Muted Pastel Blue */
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        color: #333333;
    }
    
    .task-card-title {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 5px;
        color: #2c3e50;
    }
    
    /* ป้ายกำกับ Project / Routine */
    .badge-project {
        background-color: #e0b8b8; /* Rose Gold */
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        color: #fff;
    }
    
    .badge-routine {
        background-color: #f5e6b3; /* Pastel Champagne */
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        color: #555;
    }
    
    /* ปรับแต่งปุ่มและฟอร์ม */
    div[data-baseweb="button"] > button {
        background-color: #e0b8b8 !important;
        border-radius: 10px !important;
        color: white !important;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State สำหรับ Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- Helper Functions ---
def fetch_tasks():
    response = supabase.table("tasks").select("*").execute()
    return pd.DataFrame(response.data)

def update_task_status(task_id, new_status, task_type, old_due_date):
    # อัปเดตสถานะงานปัจจุบัน
    supabase.table("tasks").update({"status": new_status}).eq("task_id", task_id).execute()
    
    # Automation: ถ้าระบุว่า Done และเป็น Routine ให้สร้างการ์ดใหม่ที่ To Do พร้อมขยับ Due Date 7 วัน
    if new_status == "Done" and task_type == "Routine":
        task_data = supabase.table("tasks").select("*").eq("task_id", task_id).execute().data[0]
        new_due = pd.to_datetime(old_due_date) + timedelta(days=7)
        
        new_task = {
            "title": task_data["title"],
            "description": task_data["description"],
            "task_type": "Routine",
            "status": "To Do",
            "priority": task_data["priority"],
            "start_date": datetime.today().strftime('%Y-%m-%d'),
            "due_date": new_due.strftime('%Y-%m-%d'),
            "assignee_name": task_data["assignee_name"],
            "requester_name": task_data["requester_name"],
            "requester_dept": task_data["requester_dept"]
        }
        supabase.table("tasks").insert(new_task).execute()
        st.success("🔄 Automation: สร้าง Routine Task รอบถัดไปเรียบร้อยแล้ว!")

# --- Page 1: Login / Authentication ---
def login_page():
    st.title("🔒 System Login")
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown('<div class="task-card">', unsafe_allow_html=True)
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                res = supabase.table("app_users").select("*").eq("username", username).eq("password_hash", password).execute()
                if len(res.data) > 0:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            st.markdown('</div>', unsafe_allow_html=True)

# --- Page 2: Kanban Board ---
def kanban_page():
    st.header("📋 Kanban Board")
    df = fetch_tasks()
    
    statuses = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
    cols = st.columns(len(statuses))
    
    for idx, status in enumerate(statuses):
        with cols[idx]:
            st.markdown(f"### {status}")
            if not df.empty:
                status_df = df[df['status'] == status]
                for _, row in status_df.iterrows():
                    badge_class = "badge-project" if row['task_type'] == "Project" else "badge-routine"
                    
                    st.markdown(f"""
                    <div class="task-card">
                        <span class="{badge_class}">{row['task_type']}</span>
                        <div class="task-card-title">{row['title']}</div>
                        <small>👷 {row['assignee_name']}</small><br/>
                        <small>📅 Due: {row['due_date']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ปุ่มอัปเดตสถานะ (แสดงด้วย Expander เพื่อความสะอาดของ UI)
                    with st.expander("Update Status"):
                        new_stat = st.selectbox("Move to:", statuses, index=statuses.index(status), key=f"sel_{row['task_id']}")
                        if st.button("Save", key=f"btn_{row['task_id']}"):
                            update_task_status(row['task_id'], new_stat, row['task_type'], row['due_date'])
                            st.rerun()

# --- Page 3: Task Request Form ---
def task_request_page():
    st.header("📝 Submit a New Task Request")
    
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            requester_name = st.text_input("Requester Name (ชื่อผู้ส่งงาน)")
            requester_dept = st.text_input("Department (แผนก)")
            title = st.text_input("Task Title (ชื่องาน)")
            task_type = st.selectbox("Task Type (ประเภทงาน)", ["Project", "Routine"])
        with col2:
            assignee_name = st.text_input("Assignee Name (ชื่อผู้รับผิดชอบ)")
            priority = st.selectbox("Priority (ความเร่งด่วน)", ["Normal", "High", "Urgent"])
            due_date = st.date_input("Due Date (วันกำหนดส่ง)")
            attachment = st.text_input("Attachment URL (ลิงก์ไฟล์แนบ หากมี)")
            
        description = st.text_area("Scope & Details (รายละเอียดงาน)")
        submitted = st.form_submit_button("Submit Request")
        
        if submitted:
            new_task = {
                "title": title,
                "description": description,
                "task_type": task_type,
                "status": "To Do",
                "priority": priority,
                "due_date": due_date.strftime('%Y-%m-%d'),
                "assignee_name": assignee_name,
                "requester_name": requester_name,
                "requester_dept": requester_dept,
                "attachment_url": attachment
            }
            supabase.table("tasks").insert(new_task).execute()
            st.success("✅ งานถูกส่งเข้าสู่ระบบ และปรากฏใน To Do เรียบร้อยแล้ว!")

# --- Page 4: Manager Dashboard ---
def dashboard_page():
    st.header("📊 Manager Dashboard & Monitor")
    df = fetch_tasks()
    
    if df.empty:
        st.info("ยังไม่มีข้อมูลในระบบ")
        return

    # Filter Section
    st.markdown("##### 🔍 Filters")
    col1, col2 = st.columns(2)
    with col1:
        assignee_filter = st.selectbox("กรองตามผู้รับผิดชอบ:", ["All"] + list(df['assignee_name'].dropna().unique()))
    with col2:
        overdue_only = st.checkbox("แสดงเฉพาะงานเกินกำหนด (Overdue)")

    # Apply Filters
    filtered_df = df.copy()
    if assignee_filter != "All":
        filtered_df = filtered_df[filtered_df['assignee_name'] == assignee_filter]
    if overdue_only:
        filtered_df['due_date'] = pd.to_datetime(filtered_df['due_date'])
        filtered_df = filtered_df[filtered_df['due_date'] < datetime.now()]

    # Metrics Overview
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("📌 Total Tasks", len(filtered_df))
    m2.metric("⏳ In Progress", len(filtered_df[filtered_df['status'] == 'In Progress']))
    m3.metric("✅ Done", len(filtered_df[filtered_df['status'] == 'Done']))

    # Workload Chart (Plotly)
    st.markdown("---")
    st.markdown("##### 📈 Workload by Assignee (Not Done)")
    workload_df = filtered_df[filtered_df['status'] != 'Done']
    if not workload_df.empty:
        workload_count = workload_df.groupby('assignee_name').size().reset_index(name='tasks')
        fig = px.bar(workload_count, x='assignee_name', y='tasks', 
                     color_discrete_sequence=['#b4c6e7'], 
                     title="ปริมาณงานค้างของแต่ละบุคคล")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("ไม่มีงานค้าง")

# --- Main App Logic (Sidebar Navigation) ---
if not st.session_state.logged_in:
    login_page()
else:
    st.sidebar.title(f"👤 Welcome, {st.session_state.username}")
    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigation", 
                           ["Kanban Board", "Task Request Form", "Manager Dashboard"])
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    if page == "Kanban Board":
        kanban_page()
    elif page == "Task Request Form":
        task_request_page()
    elif page == "Manager Dashboard":
        dashboard_page()