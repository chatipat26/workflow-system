import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, status, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from supabase import create_client, Client

import config

app = FastAPI(title="Team Workflow SVV", version="2.1.0")

# Enable CORS for local dev / reverse proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Database (Dokploy PostgreSQL via DATABASE_URL or Supabase)
if config.DATABASE_URL:
    from pg_client import PgClient
    print("Connecting via direct PostgreSQL (DATABASE_URL)...")
    supabase = PgClient(config.DATABASE_URL)
elif config.SUPABASE_URL and config.SUPABASE_KEY:
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    print("Connecting via Supabase API...")
else:
    raise RuntimeError("Either DATABASE_URL or SUPABASE_URL and SUPABASE_KEY must be configured.")

# Static files setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Helper Functions ---

def parse_roles(roles_val: Any) -> List[str]:
    if not roles_val:
        return ["ปฏิบัติงาน"]
    if isinstance(roles_val, list):
        return [str(r).strip() for r in roles_val if str(r).strip()]
    if isinstance(roles_val, str):
        return [r.strip() for r in roles_val.split(",") if r.strip()]
    return ["ปฏิบัติงาน"]

def user_has_role(user_dict: Optional[Dict[str, Any]], role_name: str) -> bool:
    if not user_dict:
        return False
    if user_dict.get("role") == "Admin" or user_dict.get("username") == "admin":
        return True
    roles = parse_roles(user_dict.get("roles"))
    return role_name in roles

def user_can_edit_task_progress(curr_user: Dict[str, Any], task: Dict[str, Any]) -> bool:
    if not curr_user or not task:
        return False
    if curr_user.get("role") == "Admin" or curr_user.get("username") == "admin":
        return True
    if user_has_role(curr_user, "ระดับสั่งการ"):
        return True
    curr_username = str(curr_user.get("username", "")).strip()
    assignees_str = str(task.get("assignee_name") or task.get("assignees") or "")
    if curr_username and curr_username in [a.strip() for a in assignees_str.split(",")]:
        return True
    return False

def create_jwt_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=config.JWT_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authentication token")
    token = authorization.split(" ")[1].strip()
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    res = supabase.table("app_users").select("*").eq("username", username).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    user = res.data[0]
    if user.get("is_approved") is False and user.get("role") != "Admin" and user.get("username") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="บัญชีของคุณอยู่ระหว่างรอ Admin อนุมัติ")
    return user

def log_task_action(task_id: str, action: str, performed_by: str, details: str = ""):
    try:
        supabase.table("task_logs").insert({
            "task_id": str(task_id),
            "action": action,
            "performed_by": performed_by,
            "details": details
        }).execute()
    except Exception as e:
        print(f"Error logging task action: {e}")

# --- Pydantic Schemas ---

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    fullname: str
    email: str
    phone: str
    password: str

class ResetPasswordRequest(BaseModel):
    username: str
    contact: str
    new_password: str

class TaskCreateRequest(BaseModel):
    title: str
    description: str
    task_type: str = "Project"
    priority: str = "Normal"
    due_date: str
    assignees: List[str]
    attachment_url: Optional[str] = None

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    assignees: Optional[List[str]] = None
    attachment_url: Optional[str] = None

class TaskMoveRequest(BaseModel):
    target_status: str

class TaskSubmitRequest(BaseModel):
    submission_note: str
    attachment_url: Optional[str] = None

class TaskApproveRequest(BaseModel):
    satisfaction_rating: int
    feedback: Optional[str] = ""

class TaskReturnRequest(BaseModel):
    target_status: str = "In Progress"
    feedback: str
    new_due_date: Optional[str] = None
    rating: Optional[int] = 5

class TaskHandoverRequest(BaseModel):
    handover_to: List[str]
    reason: str

class TaskHandoverActionRequest(BaseModel):
    action: str  # "approve", "reject", "cancel"

class TaskProgressLogRequest(BaseModel):
    action: Optional[str] = "รายงานความคืบหน้า"
    note: str
    attachment_url: Optional[str] = None

class TaskLogEditRequest(BaseModel):
    details: str

class KpiAdjustmentRequest(BaseModel):
    username: str
    points: float
    reason_type: str
    description: str

class RoleUpdateRequest(BaseModel):
    roles: List[str]

# --- Auth Endpoints ---

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    uname = req.username.strip()
    pwd = req.password.strip()
    res = supabase.table("app_users").select("*").eq("username", uname).eq("password_hash", pwd).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    user = res.data[0]
    if user.get("is_approved") is False and user.get("role") != "Admin" and user.get("username") != "admin":
        raise HTTPException(status_code=403, detail="⏳ บัญชีของคุณอยู่ระหว่างรอ Admin อนุมัติและกำหนดยศ กรุณาติดต่อ Admin")

    token = create_jwt_token({"sub": user["username"], "user_id": str(user.get("user_id"))})
    user_safe = {k: v for k, v in user.items() if k != "password_hash"}
    user_safe["parsed_roles"] = parse_roles(user.get("roles"))
    user_safe["is_admin"] = user.get("role") == "Admin" or user.get("username") == "admin"
    user_safe["is_commander"] = user_has_role(user, "ระดับสั่งการ")
    user_safe["is_operator"] = user_has_role(user, "ปฏิบัติงาน")
    return {"token": token, "user": user_safe}

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    uname = req.username.strip()
    check = supabase.table("app_users").select("username").eq("username", uname).execute()
    if check.data:
        raise HTTPException(status_code=400, detail="Username นี้มีอยู่ในระบบแล้ว")
    new_user = {
        "username": uname,
        "password_hash": req.password,
        "fullname": req.fullname.strip(),
        "email": req.email.strip(),
        "phone": req.phone.strip(),
        "role": "User",
        "roles": "ปฏิบัติงาน",
        "is_approved": False
    }
    supabase.table("app_users").insert(new_user).execute()
    return {"success": True, "message": "✅ สมัครสมาชิกสำเร็จ! กรุณารอ Admin อนุมัติสิทธิ์เข้าใช้งาน"}

@app.post("/api/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    uname = req.username.strip()
    u_res = supabase.table("app_users").select("*").eq("username", uname).execute()
    if not u_res.data:
        raise HTTPException(status_code=400, detail="ไม่พบบัญชีผู้ใช้นี้")
    ud = u_res.data[0]
    contact_val = req.contact.strip().lower()
    user_email = str(ud.get("email") or "").strip().lower()
    user_phone = str(ud.get("phone") or "").strip()
    if contact_val not in [user_email, user_phone]:
        raise HTTPException(status_code=400, detail="Email หรือ เบอร์โทรไม่ตรงกับข้อมูลในระบบ")

    supabase.table("app_users").update({"password_hash": req.new_password}).eq("user_id", ud["user_id"]).execute()
    return {"success": True, "message": "✅ แก้ไขรหัสผ่านสำเร็จ! สามารถเข้าสู่ระบบด้วยรหัสใหม่ได้ทันที"}

@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    user_safe = {k: v for k, v in user.items() if k != "password_hash"}
    user_safe["parsed_roles"] = parse_roles(user.get("roles"))
    user_safe["is_admin"] = user.get("role") == "Admin" or user.get("username") == "admin"
    user_safe["is_commander"] = user_has_role(user, "ระดับสั่งการ")
    user_safe["is_operator"] = user_has_role(user, "ปฏิบัติงาน")
    return {"user": user_safe}

# --- Users & Admin Endpoints ---

@app.get("/api/users/operators")
async def get_operators(current_user: dict = Depends(get_current_user)):
    res = supabase.table("app_users").select("user_id, username, fullname, email, phone, role, roles, is_approved").execute()
    users = res.data or []
    ops = []
    for u in users:
        # Match original fetch_operators(): only approved users with 'ปฏิบัติงาน' in roles
        if u.get("is_approved") is not False:
            roles = parse_roles(u.get("roles"))
            if "ปฏิบัติงาน" in roles:
                display_name = f"{u.get('fullname') or u.get('username')} (@{u.get('username')})"
                ops.append({
                    "username": u["username"],
                    "fullname": u.get("fullname") or u["username"],
                    "display_name": display_name,
                    "roles": roles
                })
    return ops

@app.get("/api/admin/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    if not (current_user.get("role") == "Admin" or current_user.get("username") == "admin"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะ Admin เท่านั้น")
    res = supabase.table("app_users").select("user_id, username, fullname, email, phone, role, roles, is_approved, created_at").order("created_at", desc=True).execute()
    users = res.data or []
    for u in users:
        u["parsed_roles"] = parse_roles(u.get("roles"))
    return users

@app.put("/api/admin/users/{user_id}/approve")
async def approve_user(user_id: str, req: RoleUpdateRequest, current_user: dict = Depends(get_current_user)):
    if not (current_user.get("role") == "Admin" or current_user.get("username") == "admin"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะ Admin เท่านั้น")
    roles_str = ", ".join(req.roles) if req.roles else "ปฏิบัติงาน"
    supabase.table("app_users").update({"is_approved": True, "roles": roles_str}).eq("user_id", user_id).execute()
    return {"success": True, "message": "อนุมัติผู้ใช้งานเรียบร้อยแล้ว"}

@app.put("/api/admin/users/{user_id}/roles")
async def update_user_roles(user_id: str, req: RoleUpdateRequest, current_user: dict = Depends(get_current_user)):
    if not (current_user.get("role") == "Admin" or current_user.get("username") == "admin"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะ Admin เท่านั้น")
    roles_str = ", ".join(req.roles)
    supabase.table("app_users").update({"roles": roles_str}).eq("user_id", user_id).execute()
    return {"success": True, "message": "บันทึกการแก้ไขยศสำเร็จ"}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if not (current_user.get("role") == "Admin" or current_user.get("username") == "admin"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะ Admin เท่านั้น")
    check = supabase.table("app_users").select("username").eq("user_id", user_id).execute()
    if check.data and check.data[0].get("username") == "admin":
        raise HTTPException(status_code=400, detail="ไม่อนุญาตให้ลบบัญชีผู้ดูแลระบบหลัก")
    supabase.table("app_users").delete().eq("user_id", user_id).execute()
    return {"success": True, "message": "ลบผู้ใช้เรียบร้อย"}

# --- Task Endpoints ---

@app.get("/api/tasks")
async def get_tasks(current_user: dict = Depends(get_current_user)):
    res = supabase.table("tasks").select("*").order("created_at", desc=True).execute()
    tasks = res.data or []
    today = datetime.today().date()
    curr_uname = current_user.get("username")
    is_comm = user_has_role(current_user, "ระดับสั่งการ") or current_user.get("role") == "Admin" or curr_uname == "admin"

    for t in tasks:
        due = t.get("due_date")
        t["is_overdue"] = False
        t["days_diff"] = None
        if due and t.get("status") != "Done":
            try:
                due_d = datetime.strptime(str(due)[:10], "%Y-%m-%d").date()
                diff = (due_d - today).days
                t["days_diff"] = diff
                if diff < 0:
                    t["is_overdue"] = True
            except Exception:
                pass
        t["can_edit"] = is_comm or (t.get("creator_username") == curr_uname)
        t["can_delete"] = is_comm or (t.get("creator_username") == curr_uname) or (curr_uname in str(t.get("assignee_name") or ""))
        t["can_edit_progress"] = user_can_edit_task_progress(current_user, t)
    return tasks

@app.post("/api/tasks")
async def create_task(req: TaskCreateRequest, current_user: dict = Depends(get_current_user)):
    if not user_has_role(current_user, "ระดับสั่งการ"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะผู้มียศระดับสั่งการเท่านั้น")
    if not req.title or not req.description or not req.assignees:
        raise HTTPException(status_code=400, detail="กรุณากรอกข้อมูลที่จำเป็นและเลือกผู้ปฏิบัติงานอย่างน้อย 1 คน")

    assigned_str = ", ".join(req.assignees)
    new_t = {
        "title": req.title.strip(),
        "description": req.description.strip(),
        "task_type": req.task_type,
        "status": "To Do",
        "priority": req.priority,
        "due_date": req.due_date,
        "assignee_name": assigned_str,
        "assignees": assigned_str,
        "creator_username": current_user.get("username"),
        "requester_name": current_user.get("fullname") or current_user.get("username"),
        "requester_dept": "ระดับสั่งการ",
        "attachment_url": req.attachment_url,
        "handover_status": "None"
    }
    res = supabase.table("tasks").insert(new_t).execute()
    if res.data and len(res.data) > 0:
        created_tid = res.data[0].get("task_id")
        log_task_action(created_tid, "สร้างงานใหม่", current_user.get("username"), f"มอบหมายให้: {assigned_str}")
        return {"success": True, "task": res.data[0]}
    return {"success": True}

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, req: TaskUpdateRequest, current_user: dict = Depends(get_current_user)):
    is_comm = user_has_role(current_user, "ระดับสั่งการ")
    is_admin = current_user.get("role") == "Admin" or current_user.get("username") == "admin"
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงานนี้ในระบบ")
    t = t_res.data[0]
    if not (is_comm or is_admin or t.get("creator_username") == current_user.get("username")):
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์แก้ไขงานนี้")

    upd = {}
    if req.title is not None: upd["title"] = req.title.strip()
    if req.description is not None: upd["description"] = req.description.strip()
    if req.task_type is not None: upd["task_type"] = req.task_type
    if req.priority is not None: upd["priority"] = req.priority
    if req.due_date is not None: upd["due_date"] = req.due_date
    if req.assignees is not None:
        assigned_str = ", ".join(req.assignees)
        upd["assignee_name"] = assigned_str
        upd["assignees"] = assigned_str
    if req.attachment_url is not None and req.attachment_url != "":
        upd["attachment_url"] = req.attachment_url

    if upd:
        supabase.table("tasks").update(upd).eq("task_id", task_id).execute()
        log_task_action(
            task_id,
            "แก้ไขข้อมูลงาน",
            current_user.get("username"),
            f"แก้ไขรายละเอียดงานโดย @{current_user.get('username')}: ผู้รับผิดชอบ={upd.get('assignee_name', t.get('assignee_name'))}, กำหนดส่ง={upd.get('due_date', t.get('due_date'))}"
        )
    return {"success": True, "message": "✅ แก้ไขและปรับเปลี่ยนข้อมูลงานเรียบร้อยแล้ว!"}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    is_comm = user_has_role(current_user, "ระดับสั่งการ")
    is_admin = current_user.get("role") == "Admin" or current_user.get("username") == "admin"
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงานนี้ในระบบ")
    t = t_res.data[0]
    assignee_str = str(t.get("assignee_name") or "")
    if not (is_comm or is_admin or t.get("creator_username") == current_user.get("username") or current_user.get("username") in assignee_str):
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ลบงานนี้")

    try:
        supabase.table("task_logs").delete().eq("task_id", str(task_id)).execute()
    except Exception:
        pass
    supabase.table("tasks").delete().eq("task_id", task_id).execute()
    return {"success": True, "message": f"✅ ลบงาน '{t.get('title')}' สำเร็จ! ลดยอดจำนวนงานเรียบร้อยแล้ว"}

@app.post("/api/tasks/{task_id}/move")
async def move_task(task_id: str, req: TaskMoveRequest, current_user: dict = Depends(get_current_user)):
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    t = t_res.data[0]
    curr_status = t.get("status")
    target_status = req.target_status
    curr_username = current_user.get("username")
    is_comm = user_has_role(current_user, "ระดับสั่งการ") or current_user.get("role") == "Admin" or curr_username == "admin"

    if curr_status == target_status:
        return {"success": True}

    if target_status == "Done" and not is_comm:
        raise HTTPException(status_code=403, detail="⚠️ เฉพาะผู้สั่งการเท่านั้นที่สามารถตรวจรับงานและย้ายไป Done ได้")

    if target_status in ["To Do", "Revision"] and curr_status != "To Do" and not is_comm:
        raise HTTPException(status_code=403, detail="⚠️ เฉพาะผู้สั่งการเท่านั้นที่สามารถย้ายกลับสถานะนี้ได้")

    action_label = "เริ่มดำเนินงาน" if (curr_status in ["To Do", "Revision"] and target_status == "In Progress") else "ย้ายสถานะงาน"
    supabase.table("tasks").update({"status": target_status}).eq("task_id", task_id).execute()
    log_task_action(task_id, action_label, curr_username, f"ย้ายสถานะจาก {curr_status} ไป {target_status}")
    return {"success": True}

@app.post("/api/tasks/{task_id}/submit")
async def submit_work(task_id: str, req: TaskSubmitRequest, current_user: dict = Depends(get_current_user)):
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    t = t_res.data[0]
    curr_due = t.get("due_date")
    today = datetime.today().date()
    is_ontime = True
    if curr_due:
        try:
            due_d = datetime.strptime(str(curr_due)[:10], "%Y-%m-%d").date()
            if today > due_d:
                is_ontime = False
        except Exception:
            pass

    comb_sub = (req.submission_note or "").strip()
    if req.attachment_url:
        comb_sub = f"{comb_sub}\n\n[ATTACHED_IMAGE: {req.attachment_url}]".strip()

    upd_data = {
        "status": "In Review",
        "submission_note": comb_sub,
        "completed_at": datetime.now().isoformat(),
        "is_ontime": is_ontime
    }
    if req.attachment_url and not t.get("attachment_url"):
        upd_data["attachment_url"] = req.attachment_url

    supabase.table("tasks").update(upd_data).eq("task_id", task_id).execute()
    log_task_action(task_id, "ส่งงานเพื่อรออนุมัติ", current_user.get("username"), f"หมายเหตุ: {comb_sub}")
    return {"success": True, "message": "✅ ส่งงานสำเร็จ! งานย้ายไป In Review เรียบร้อยแล้ว"}

@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, req: TaskApproveRequest, current_user: dict = Depends(get_current_user)):
    if not user_has_role(current_user, "ระดับสั่งการ"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะผู้มียศระดับสั่งการเท่านั้น")
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    t = t_res.data[0]
    task_type = t.get("task_type", "Project")
    curr_due = t.get("due_date")
    now_iso = datetime.now().isoformat()
    rating = max(1, min(5, req.satisfaction_rating))

    # Extract attached image from submission_note if present so we preserve it in logs
    sub_raw = t.get("submission_note") or ""
    done_img = None
    if "[ATTACHED_IMAGE:" in sub_raw:
        try:
            done_img = sub_raw.split("[ATTACHED_IMAGE:")[1].split("]")[0].strip()
        except Exception:
            pass

    if task_type == "Routine":
        try:
            old_due = datetime.strptime(str(curr_due)[:10], "%Y-%m-%d") if curr_due else datetime.today()
            next_due = (old_due + timedelta(days=30)).strftime("%Y-%m-%d")
        except Exception:
            next_due = (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        supabase.table("tasks").update({
            "status": "To Do",
            "due_date": next_due,
            "satisfaction_rating": rating,
            "completed_at": now_iso,
            "submission_note": req.feedback.strip() if (req.feedback and req.feedback.strip()) else None
        }).eq("task_id", task_id).execute()
        msg = f"✅ ตรวจรับงาน Routine สำเร็จ ({rating} ดาว) และขยายรอบกำหนดส่งเดือนถัดไป ({next_due}) เรียบร้อยแล้ว"
    else:
        final_sub_note = sub_raw
        if req.feedback and req.feedback.strip():
            final_sub_note = req.feedback.strip()
            if done_img:
                final_sub_note += f"\n\n[ATTACHED_IMAGE: {done_img}]"
        supabase.table("tasks").update({
            "status": "Done",
            "satisfaction_rating": rating,
            "completed_at": now_iso,
            "submission_note": final_sub_note
        }).eq("task_id", task_id).execute()
        msg = f"✅ ตรวจรับงานสำเร็จ ({rating} ดาว) งานย้ายไป Done และบันทึกลงแดชบอร์ด KPI แล้ว"

    log_details = f"อนุมัติผลงานสำเร็จ ({rating} ดาว) " + (f"- {req.feedback.strip()}" if req.feedback and req.feedback.strip() else "")
    if done_img:
        log_details += f"\n\n[ATTACHED_IMAGE: {done_img}]"
    log_task_action(task_id, "อนุมัติงานสำเร็จ", current_user.get("username"), log_details)
    return {"success": True, "message": msg}

@app.post("/api/tasks/{task_id}/return")
async def return_task(task_id: str, req: TaskReturnRequest, current_user: dict = Depends(get_current_user)):
    if not user_has_role(current_user, "ระดับสั่งการ"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะผู้มียศระดับสั่งการเท่านั้น")
    target_status = req.target_status if req.target_status in ["In Progress", "Revision", "To Do"] else "In Progress"
    if target_status == "In Progress":
        action_title = "อนุมัติให้ดำเนินงานต่อ"
    elif target_status == "To Do":
        action_title = "ย้อนกลับไป To Do"
    else:
        action_title = "ส่งกลับไปแก้ไข"

    rating = req.rating if req.rating and 1 <= req.rating <= 5 else 5
    upd: Dict[str, Any] = {
        "status": target_status,
        "satisfaction_rating": rating,
        "completed_at": None,
        "is_ontime": None,
        "submission_note": req.feedback.strip()
    }
    if req.new_due_date:
        upd["due_date"] = req.new_due_date

    supabase.table("tasks").update(upd).eq("task_id", task_id).execute()
    due_txt = req.new_due_date or "-"
    log_msg = f"{req.feedback.strip()} (กำหนดวันส่งใหม่: {due_txt}) [ประเมินความพึงพอใจ: {rating} ดาว]"
    log_task_action(task_id, action_title, current_user.get("username"), log_msg)
    return {"success": True, "message": f"✅ บันทึกและย้ายงานไปยัง {target_status} เรียบร้อยแล้ว! (ประเมิน {rating} ดาว)"}

@app.post("/api/tasks/{task_id}/handover")
async def handover_task(task_id: str, req: TaskHandoverRequest, current_user: dict = Depends(get_current_user)):
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    is_comm = user_has_role(current_user, "ระดับสั่งการ") or current_user.get("role") == "Admin" or current_user.get("username") == "admin"
    new_assignees = ", ".join(req.handover_to)
    if is_comm:
        supabase.table("tasks").update({
            "assignee_name": new_assignees,
            "assignees": new_assignees,
            "handover_status": "Approved"
        }).eq("task_id", task_id).execute()
        log_task_action(task_id, "แก้ไขผู้รับผิดชอบงาน", current_user.get("username"), f"ปรับเปลี่ยนผู้รับผิดชอบเป็น: {new_assignees} (เหตุผล: {req.reason.strip()})")
        return {"success": True, "message": f"✅ บันทึกผู้รับผิดชอบงานเรียบร้อย: {new_assignees}"}
    else:
        supabase.table("tasks").update({
            "handover_to": new_assignees,
            "handover_reason": req.reason.strip(),
            "handover_status": "Pending"
        }).eq("task_id", task_id).execute()
        log_task_action(task_id, "ขอปรับเปลี่ยนผู้รับผิดชอบ", current_user.get("username"), f"ขอเปลี่ยนเป็น: {new_assignees} (เหตุผล: {req.reason.strip()}) - รอผู้มอบหมายอนุมัติ")
        return {"success": True, "message": f"✅ ส่งคำขอปรับเปลี่ยนผู้รับผิดชอบเป็น {new_assignees} แล้ว! กำลังรอผู้มอบหมายอนุมัติ"}

@app.post("/api/tasks/{task_id}/handover-action")
async def handover_action(task_id: str, req: TaskHandoverActionRequest, current_user: dict = Depends(get_current_user)):
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    t = t_res.data[0]
    action = req.action.lower()
    if action == "cancel":
        supabase.table("tasks").update({"handover_status": "None", "handover_to": None, "handover_reason": None}).eq("task_id", task_id).execute()
        log_task_action(task_id, "ยกเลิกคำขอส่งต่องาน", current_user.get("username"), "ยกเลิกคำขอ")
        return {"success": True, "message": "ยกเลิกคำขอส่งต่องานเรียบร้อย"}

    if not user_has_role(current_user, "ระดับสั่งการ"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะผู้มียศระดับสั่งการเท่านั้น")

    if action == "approve":
        new_assignee = t.get("handover_to")
        supabase.table("tasks").update({
            "assignee_name": new_assignee,
            "assignees": new_assignee,
            "handover_status": "Approved"
        }).eq("task_id", task_id).execute()
        log_task_action(task_id, "อนุมัติเปลี่ยนผู้รับผิดชอบ", current_user.get("username"), f"อนุมัติเปลี่ยนเป็น {new_assignee} โดยผู้สั่งการ @{current_user.get('username')}")
        return {"success": True, "message": f"✅ อนุมัติเปลี่ยนผู้รับผิดชอบเป็น @{new_assignee} แล้ว!"}
    elif action == "reject":
        supabase.table("tasks").update({"handover_status": "Rejected"}).eq("task_id", task_id).execute()
        log_task_action(task_id, "ปฏิเสธการส่งต่องาน", current_user.get("username"), f"ปฏิเสธคำขอโดยผู้สั่งการ @{current_user.get('username')}")
        return {"success": True, "message": "❌ ปฏิเสธคำขอส่งต่องานแล้ว"}

@app.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, current_user: dict = Depends(get_current_user)):
    res = supabase.table("task_logs").select("*").eq("task_id", str(task_id)).order("created_at", desc=True).execute()
    return res.data or []

@app.post("/api/tasks/{task_id}/logs")
async def add_task_log(task_id: str, req: TaskProgressLogRequest, current_user: dict = Depends(get_current_user)):
    t_res = supabase.table("tasks").select("*").eq("task_id", task_id).execute()
    if not t_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    task = t_res.data[0]
    if not user_can_edit_task_progress(current_user, task):
        raise HTTPException(status_code=403, detail="เฉพาะผู้รับผิดชอบงานนี้และผู้มียศระดับสั่งการเท่านั้นที่มีสิทธิ์บันทึกความคืบหน้า")

    if not req.note.strip() and not req.attachment_url:
        raise HTTPException(status_code=400, detail="กรุณาระบุรายละเอียดหรือแนบไฟล์ก่อนกดบันทึก")

    clean_action = req.action or "รายงานความคืบหน้า"
    if " " in clean_action and clean_action[0] in ["📌", "📝", "⚠️", "💡"]:
        clean_action = clean_action.split(" ", 1)[1]

    full_details = req.note.strip()
    if req.attachment_url:
        full_details = f"{full_details}\n\n[ATTACHED_IMAGE: {req.attachment_url}]".strip()

    log_task_action(task_id, clean_action, current_user.get("username"), full_details)
    return {"success": True, "message": "✅ บันทึกรายงานความคืบหน้าสำเร็จแล้ว!"}

@app.put("/api/logs/{log_id}")
async def update_task_log(log_id: str, req: TaskLogEditRequest, current_user: dict = Depends(get_current_user)):
    l_res = supabase.table("task_logs").select("*").eq("log_id", log_id).execute()
    if not l_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกนี้")
    log_row = l_res.data[0]
    curr_uname = current_user.get("username")
    is_comm = user_has_role(current_user, "ระดับสั่งการ") or current_user.get("role") == "Admin" or curr_uname == "admin"
    if log_row.get("performed_by") != curr_uname and not is_comm:
        raise HTTPException(status_code=403, detail="คุณไม่มีสิทธิ์แก้ไขบันทึกนี้")

    # Preserve existing [ATTACHED_IMAGE: ...] if present
    old_details = log_row.get("details") or ""
    img_part = None
    if "[ATTACHED_IMAGE:" in old_details:
        try:
            img_part = old_details.split("[ATTACHED_IMAGE:")[1].split("]")[0].strip()
        except Exception:
            pass
    final_details = req.details.strip()
    if img_part and "[ATTACHED_IMAGE:" not in final_details:
        final_details = f"{final_details}\n\n[ATTACHED_IMAGE: {img_part}]"

    supabase.table("task_logs").update({"details": final_details}).eq("log_id", log_id).execute()
    return {"success": True, "message": "บันทึกการแก้ไขเรียบร้อยแล้ว!"}

@app.delete("/api/logs/{log_id}")
async def delete_task_log(log_id: str, current_user: dict = Depends(get_current_user)):
    l_res = supabase.table("task_logs").select("*").eq("log_id", log_id).execute()
    if not l_res.data:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกนี้")
    log_row = l_res.data[0]
    curr_uname = current_user.get("username")
    is_comm = user_has_role(current_user, "ระดับสั่งการ") or current_user.get("role") == "Admin" or curr_uname == "admin"
    if log_row.get("performed_by") != curr_uname and not is_comm:
        raise HTTPException(status_code=403, detail="คุณไม่มีสิทธิ์ลบบันทึกนี้")

    supabase.table("task_logs").delete().eq("log_id", log_id).execute()
    return {"success": True, "message": "ลบบันทึกเรียบร้อยแล้ว!"}

# --- KPI Endpoints ---

@app.get("/api/kpi/summary")
async def get_kpi_summary(current_user: dict = Depends(get_current_user)):
    t_res = supabase.table("tasks").select("*").execute()
    tasks = t_res.data or []
    
    u_res = supabase.table("app_users").select("username, fullname, roles, is_approved").execute()
    users = u_res.data or []
    user_map = {u["username"]: (u.get("fullname") or u["username"]) for u in users if u.get("username")}
    
    adj_res = supabase.table("kpi_adjustments").select("*").order("created_at", desc=True).execute()
    adjustments = adj_res.data or []
    for a in adjustments:
        uname_target = a.get("username") or ""
        uname_creator = a.get("created_by") or ""
        a["target_fullname"] = user_map.get(uname_target, uname_target)
        a["creator_fullname"] = user_map.get(uname_creator, uname_creator)

    # Filter operators (exact match with fetch_operators in original app.py)
    operators = [u for u in users if u.get("is_approved") is not False and "ปฏิบัติงาน" in parse_roles(u.get("roles"))]

    summary = []
    for op in operators:
        uname = op["username"]
        fname = op.get("fullname") or uname
        my_tasks = [t for t in tasks if uname in str(t.get("assignee_name") or "")]
        done_tasks = [t for t in my_tasks if t.get("status") == "Done"]
        ontime_c = len([t for t in done_tasks if t.get("is_ontime") is True])
        late_c = len([t for t in done_tasks if t.get("is_ontime") is False])
        
        ratings = []
        for t in done_tasks:
            r = t.get("satisfaction_rating")
            if r is not None and str(r).strip() != "":
                try:
                    rv = float(r)
                    if rv > 0:
                        ratings.append(rv)
                except Exception:
                    pass

        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            satisfaction_pts = avg_rating * 4.0
        else:
            avg_rating = 0.0
            satisfaction_pts = 0.0

        user_adjs = [a for a in adjustments if a.get("username") == uname]
        manual_pts = sum(float(a.get("points", 0)) for a in user_adjs)

        # Original formula from app.py line 2508:
        # tot_kpi = max(0, round((d_count * 5) + (ontime_c * 10) - (late_c * 5) + satisfaction_pts + man_pts, 1))
        total_kpi = max(0.0, round((len(done_tasks) * 5) + (ontime_c * 10) - (late_c * 5) + satisfaction_pts + manual_pts, 1))

        summary.append({
            "username": uname,
            "fullname": fname,
            "total_tasks": len(my_tasks),
            "done_tasks": len(done_tasks),
            "ontime_count": ontime_c,
            "late_count": late_c,
            "avg_rating": round(avg_rating, 1) if ratings else 0.0,
            "manual_points": manual_pts,
            "total_kpi": total_kpi
        })

    summary.sort(key=lambda x: x["total_kpi"], reverse=True)
    
    overview = {
        "total_tasks": len(tasks),
        "in_progress": len([t for t in tasks if t.get("status") == "In Progress"]),
        "in_review": len([t for t in tasks if t.get("status") in ["In Review", "Revision"]]),
        "done": len([t for t in tasks if t.get("status") == "Done"])
    }
    return {"overview": overview, "leaderboard": summary, "adjustments": adjustments}

@app.post("/api/kpi/adjustments")
async def add_kpi_adjustment(req: KpiAdjustmentRequest, current_user: dict = Depends(get_current_user)):
    if not user_has_role(current_user, "ระดับสั่งการ"):
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะผู้มียศระดับสั่งการเท่านั้น")
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุเหตุผลการปรับคะแนน")

    if "ความผิดพลาด" in req.reason_type or req.points < 0:
        points = -abs(req.points)
        clean_type = "ความผิดพลาด"
    else:
        points = abs(req.points)
        clean_type = "ความดีความชอบ"

    supabase.table("kpi_adjustments").insert({
        "username": req.username,
        "points": points,
        "reason_type": clean_type,
        "description": req.description.strip(),
        "created_by": current_user.get("username")
    }).execute()
    return {"success": True, "message": f"✅ บันทึกคะแนน {points:+} ให้ @{req.username} เรียบร้อยแล้ว!"}

@app.delete("/api/kpi/adjustments/{adj_id}")
async def delete_kpi_adjustment(adj_id: str, current_user: dict = Depends(get_current_user)):
    is_comm = user_has_role(current_user, "ระดับสั่งการ") or current_user.get("role") == "Admin" or current_user.get("username") == "admin"
    if not is_comm:
        raise HTTPException(status_code=403, detail="สิทธิ์เฉพาะผู้มียศระดับสั่งการหรือ Admin เท่านั้น")
    supabase.table("kpi_adjustments").delete().eq("id", adj_id).execute()
    return {"success": True, "message": "🗑️ ลบรายการปรับคะแนน KPI เรียบร้อยแล้ว"}

# Serve Frontend HTML
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(request: Request, full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Team Workflow SVV</h1><p>Frontend static files initializing...</p>")
