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

# Custom CSS (รองรับ Dark/Light Mode และปรับ Card UI)
st.markdown("""
    <style>
    font-family: 'Sarabun', sans-serif;
    
    .kanban-card {
        background-color: var(--background-color);
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #b4c6e7;
    }
    
    .kanban-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 8px;
        margin-top: 8px;
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

    div[data-baseweb="button"] > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State Management ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- Helper Functions ---
def fetch_tasks():
    res = supabase.table("tasks").select("*").execute()
    return pd.DataFrame(res.data)

def update_task_status(task_id, new_status, task_type, current_due_date):
    if new_status == "Done" and task_type == "Routine":
        # แก้ไขให้ "ใช้การ์ดเดิม" ย้ายกลับไป To Do พร้อมบวกเวลา 24 วัน (ไม่เพิ่มการ์ดใหม่แล้ว)
        old_due = pd.to_datetime(current_due_date) if current_due_date else datetime.today()
        next_due = (old_due + timedelta(days=24)).strftime('%Y-%m-%d')
        
        supabase.table("tasks").update({
            "status": "To Do",
            "due_date": next_due
        }).eq("task_id", task_id).execute()
        st.toast("🔄 งาน Routine ถูกรีเซ็ตกลับไป 'To Do' พร้อมอัปเดตวันส่งอีก 24 วัน!")
    else:
        # อัปเดตสถานะงานปกติ
        supabase.table("tasks").update({"status": new_status}).eq("task_id", task_id).execute()

# --- Module 1: Authentication Page ---
def show_login_page():
    st.title("🔒 เข้าสู่ระบบ (System Login)")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="kanban-card">', unsafe_allow_html=True)
        username = st.text_input("ชื่อผู้ใช้งาน (Username)")
        password = st.text_input("รหัสผ่าน (Password)", type="password")
        
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            res = supabase.table("app_users").select("*").eq("username", username).eq("password_hash", password).execute()
            if len(res.data) > 0:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Module 2: Kanban Board Page ---
def show_kanban_page():
    st.header("📋 Kanban Board (ติดตามสถานะงาน)")
    df = fetch_tasks()
    
    statuses = ['To Do', 'In Progress', 'In Review', 'Revision', 'Done']
    cols = st.columns(len(statuses))
    
    for idx, status in enumerate(statuses):
        with cols[idx]:
            st.markdown(f"#### {status}")
            if not df.empty and 'status' in df.columns:
                status_df = df[df['status'] == status]
                for _, row in status_df.iterrows():
                    badge_class = "badge-project" if row['task_type'] == "Project" else "badge-routine"
                    urgent_badge = '<span class="badge-urgent">🔥 Urgent</span>' if row['priority'] == 'Urgent' else ''
                    
                    if status == 'Done':
                        # --- UI การ์ดย่อขนาดสำหรับช่อง Done ---
                        st.markdown(f"""
                        <div class="kanban-card" style="padding: 12px; border-left: 5px solid #a7f3d0; opacity: 0.75; margin-bottom: 8px;">
                            <span class="{badge_class}" style="font-size: 0.65rem; padding: 2px 6px;">{row['task_type']}</span>
                            <div class="kanban-card-title" style="font-size: 0.9rem; margin: 6px 0; text-decoration: line-through; color: #6b7280;">{row['title']}</div>
                            <small style="font-size: 0.75rem; color: #6b7280;">📅 {row['due_date'] or '-'}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.expander("⚙️ แก้ไขสถานะ"):
                            new_stat = st.selectbox("ย้ายการ์ดกลับ:", statuses, index=statuses.index(status), key=f"sel_{row['task_id']}")
                            if st.button("อัปเดต", key=f"btn_{row['task_id']}", use_container_width=True):
                                update_task_status(row['task_id'], new_stat, row['task_type'], row['due_date'])
                                st.rerun()
                    else:
                        # --- UI การ์ดขนาดปกติสำหรับช่องอื่นๆ ---
                        st.markdown(f"""
                        <div class="kanban-card">
                            <span class="{badge_class}">{row['task_type']}</span> {urgent_badge}
                            <div class="kanban-card-title">{row['title']}</div>
                            <small>👤 รับผิดชอบ: {row['assignee_name'] or '-'}</small><br/>
                            <small>📅 กำหนดส่ง: {row['due_date'] or '-'}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.expander("🔍 ดูรายละเอียด / อัปเดต"):
                            st.markdown(f"**ผู้ขอเปิดงาน:** {row['requester_name'] or '-'} ({row['requester_dept'] or '-'})")
                            st.markdown(f"**รายละเอียดงาน:**")
                            st.info(row['description'] or 'ไม่มีข้อมูลรายละเอียด')
                            
                            if row['attachment_url']:
                                st.markdown(f"[📎 คลิกดูไฟล์แนบ]({row['attachment_url']})")
                            
                            st.divider()
                            new_stat = st.selectbox("เลื่อนการ์ดไปที่:", statuses, index=statuses.index(status), key=f"sel_{row['task_id']}")
                            if st.button("บันทึกสถานะ", key=f"btn_{row['task_id']}", use_container_width=True):
                                update_task_status(row['task_id'], new_stat, row['task_type'], row['due_date'])
                                st.rerun()

# --- Module 3: Task Request Form Page ---
def show_request_form_page():
    st.header("📝 ฟอร์มส่งขอเปิดงานใหม่ (Task Request Form)")
    
    with st.form("task_request_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            requester_name = st.text_input("ชื่อผู้ส่งงาน *")
            requester_dept = st.text_input("แผนก/ฝ่ายผู้ส่ง *")
            title = st.text_input("ชื่องาน / หัวข้อโปรเจกต์ *")
            task_type = st.selectbox("ประเภทงาน", ["Project", "Routine"])
        with col2:
            assignee_name = st.text_input("มอบหมายให้ผู้รับผิดชอบ (ถ้าทราบ)")
            priority = st.selectbox("ระดับความเร่งด่วน", ["Normal", "High", "Urgent"])
            due_date = st.date_input("วันที่ต้องการงาน (Due Date)")
            attachment = st.text_input("ลิงก์ไฟล์แนบ (Google Drive / Cloud Link)")
            
        description = st.text_area("รายละเอียดขอบเขตงาน (Scope of Work)")
        submitted = st.form_submit_button("ส่งขอเปิดงานใหม่")
        
        if submitted:
            if not requester_name or not title:
                st.error("กรุณากรอกชื่อผู้ส่งและชื่องานให้ครบถ้วน")
            else:
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
                st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว งานถูกส่งไปที่ช่อง 'To Do' บนกระดาน Kanban")

# --- Module 4: Manager Dashboard Page ---
def show_dashboard_page():
    st.header("📊 Manager Dashboard & Monitor")
    df = fetch_tasks()
    
    if df.empty:
        st.info("ยังไม่มีข้อมูลงานในระบบ")
        return

    st.markdown("##### 🔍 ตัวกรองค้นหา")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        assignees = ["ทั้งหมด"] + [a for a in df['assignee_name'].dropna().unique() if a]
        selected_assignee = st.selectbox("เลือกตามชื่อผู้รับผิดชอบ:", assignees)
    with f_col2:
        show_overdue = st.checkbox("แสดงเฉพาะงานที่เกินกำหนด (Overdue)")

    filtered_df = df.copy()
    if selected_assignee != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df['assignee_name'] == selected_assignee]
        
    if show_overdue:
        filtered_df['due_date_dt'] = pd.to_datetime(filtered_df['due_date'])
        filtered_df = filtered_df[(filtered_df['due_date_dt'] < datetime.now()) & (filtered_df['status'] != 'Done')]

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📌 งานทั้งหมด", len(filtered_df))
    m2.metric("⏳ กำลังดำเนินการ", len(filtered_df[filtered_df['status'] == 'In Progress']))
    m3.metric("🔍 อยู่ระหว่างตรวจ/แก้ไข", len(filtered_df[filtered_df['status'].isin(['In Review', 'Revision'])]))
    m4.metric("✅ เสร็จสิ้น", len(filtered_df[filtered_df['status'] == 'Done']))

    st.markdown("---")
    st.markdown("##### 📈 ปริมาณงานค้างมือรายบุคคล (Workload View)")
    pending_df = filtered_df[filtered_df['status'] != 'Done']
    
    if not pending_df.empty:
        workload = pending_df.groupby('assignee_name').size().reset_index(name='task_count')
        fig = px.bar(
            workload, 
            x='assignee_name', 
            y='task_count',
            labels={'assignee_name': 'ผู้รับผิดชอบ', 'task_count': 'จำนวนงานที่ถืออยู่'},
            color_discrete_sequence=['#b4c6e7']
        )
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("ไม่มีงานตกค้างในระบบ")

# --- Main Application Controller ---
if not st.session_state.logged_in:
    show_login_page()
else:
    st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: **{st.session_state.username}**")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio("เมนูการใช้งาน", [
        "Kanban Board", 
        "Task Request Form", 
        "Manager Dashboard"
    ])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("ออกจากระบบ (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    if page == "Kanban Board":
        show_kanban_page()
    elif page == "Task Request Form":
        show_request_form_page()
    elif page == "Manager Dashboard":
        show_dashboard_page()