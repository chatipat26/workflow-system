-- ========================================================
-- Complete Database Setup WITH DATA from Supabase
-- Run this in Dokploy Terminal or DBeaver/pgAdmin
-- ========================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS app_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    fullname TEXT,
    email TEXT,
    phone TEXT,
    role TEXT DEFAULT 'User',
    roles TEXT DEFAULT 'ปฏิบัติงาน',
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT DEFAULT 'Project',
    status TEXT DEFAULT 'To Do',
    priority TEXT DEFAULT 'Normal',
    due_date TEXT,
    assignee_name TEXT,
    assignees TEXT,
    creator_username TEXT,
    requester_name TEXT,
    requester_dept TEXT DEFAULT 'ระดับสั่งการ',
    attachment_url TEXT,
    handover_to TEXT,
    handover_reason TEXT,
    handover_status TEXT DEFAULT 'None',
    satisfaction_rating INT DEFAULT 0,
    completed_at TIMESTAMPTZ,
    is_ontime BOOLEAN,
    submission_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kpi_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    points NUMERIC NOT NULL,
    reason_type TEXT NOT NULL,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT,
    action TEXT NOT NULL,
    performed_by TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== EXISTING USERS ====================
INSERT INTO app_users (user_id, username, password_hash, fullname, email, phone, role, roles, is_approved) VALUES ('836bb483-4d15-4b3f-b518-5ce35b7ef1bd', 'chatipat', 'kingkong', 'ชาติพัฒน์ อัศวโชค', 'chatipat.ooy@gmail.com', '0888993242', 'User', 'ปฏิบัติงาน', TRUE) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, fullname = EXCLUDED.fullname, roles = EXCLUDED.roles, is_approved = EXCLUDED.is_approved;
INSERT INTO app_users (user_id, username, password_hash, fullname, email, phone, role, roles, is_approved) VALUES ('dcdae6a1-3dc5-47b1-b6ad-a52d8be9c7f3', 'sam', 'samsvvacc', 'sam us', 'somsakus@gmail.com', '0886805777', 'User', 'ระดับสั่งการ', TRUE) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, fullname = EXCLUDED.fullname, roles = EXCLUDED.roles, is_approved = EXCLUDED.is_approved;
INSERT INTO app_users (user_id, username, password_hash, fullname, email, phone, role, roles, is_approved) VALUES ('a81e2f2f-e901-484f-9ae6-6fd58d981ccb', 'Sucheeda', '20113819tT', 'Toy U.', 'toysucheeda@gmail.com', '0816416857', 'User', 'ระดับสั่งการ', TRUE) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, fullname = EXCLUDED.fullname, roles = EXCLUDED.roles, is_approved = EXCLUDED.is_approved;
INSERT INTO app_users (user_id, username, password_hash, fullname, email, phone, role, roles, is_approved) VALUES ('3e49048d-776a-4f92-81ab-ac656368aefe', 'Chaiwat.u', 'A248624', 'Chaiwat Ussawachoke', 'Chaiwat.uss@gmail com', '0988619237', 'User', 'ปฏิบัติงาน, ระดับสั่งการ', TRUE) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, fullname = EXCLUDED.fullname, roles = EXCLUDED.roles, is_approved = EXCLUDED.is_approved;
INSERT INTO app_users (user_id, username, password_hash, fullname, email, phone, role, roles, is_approved) VALUES ('6183e14b-dd00-4e5e-945d-9428b2ee8483', 'patpongu', '99Oo@00pp', 'พัฒน์พงษ์ อัศวโชค', 'patpongu@gmail.com', '0864053090', 'User', 'ปฏิบัติงาน', TRUE) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, fullname = EXCLUDED.fullname, roles = EXCLUDED.roles, is_approved = EXCLUDED.is_approved;
INSERT INTO app_users (user_id, username, password_hash, fullname, email, phone, role, roles, is_approved) VALUES ('0709bd6d-0e56-4d12-87d9-5762a09e4144', 'Voravut.U', '1234567890', 'วรวุฒิ อัศวโชค', 'voravut.u@gmail.com', '0818185326', 'User', 'ปฏิบัติงาน', TRUE) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, fullname = EXCLUDED.fullname, roles = EXCLUDED.roles, is_approved = EXCLUDED.is_approved;
INSERT INTO app_users (user_id, username, password_hash, fullname, email, phone, role, roles, is_approved) VALUES ('62b00489-3b22-4bfa-ae40-b6e0e0aa695f', 'admin', 'admin123', 'ผู้ดูแลระบบ (Admin)', NULL, NULL, 'Admin', 'ระดับสั่งการ', TRUE) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, fullname = EXCLUDED.fullname, roles = EXCLUDED.roles, is_approved = EXCLUDED.is_approved;

-- ==================== EXISTING TASKS ====================
INSERT INTO tasks (task_id, title, description, task_type, status, priority, due_date, assignee_name, assignees, creator_username, requester_name, requester_dept, attachment_url, handover_to, handover_reason, handover_status, satisfaction_rating, completed_at, is_ontime, submission_note) VALUES ('7f178111-e2e0-432c-8d25-58c34294ef23', 'Svv Server', '1.install Vps of hostinger
2.สร้างDocker Container
3.push appลงcontainer
4จัดการสิท', 'Project', 'In Review', 'Normal', '2026-10-25', 'chatipat, Voravut.U', 'chatipat, Voravut.U', 'admin', 'ผู้ดูแลระบบ (Admin)', 'ระดับสั่งการ', NULL, NULL, NULL, 'Approved', 0, '2026-10-22T16:22:03.44387+00:00', TRUE, 'https://app.svvconnect.io/') ON CONFLICT (task_id) DO NOTHING;
INSERT INTO tasks (task_id, title, description, task_type, status, priority, due_date, assignee_name, assignees, creator_username, requester_name, requester_dept, attachment_url, handover_to, handover_reason, handover_status, satisfaction_rating, completed_at, is_ontime, submission_note) VALUES ('e6cbf14b-8ee2-4ab3-a63c-1696462ae698', 'Wego trading', 'ขอapiออกรีพอตใหม่จากnet force', 'Project', 'To Do', 'Normal', '2026-10-26', 'patpongu', 'patpongu', 'admin', 'ผู้ดูแลระบบ (Admin)', 'ระดับสั่งการ', NULL, NULL, NULL, 'None', 0, NULL, NULL, NULL) ON CONFLICT (task_id) DO NOTHING;
INSERT INTO tasks (task_id, title, description, task_type, status, priority, due_date, assignee_name, assignees, creator_username, requester_name, requester_dept, attachment_url, handover_to, handover_reason, handover_status, satisfaction_rating, completed_at, is_ontime, submission_note) VALUES ('c59049b8-958c-49d0-8ef9-e5172c0df9f9', 'Sawasdee App', 'ระบบแจ้งเตือนผ่าน whats app
ระบบแจ้งเตือนบำรุงรักษา
ภาษาอังกฤษ
ระบบชำระเงิน', 'Project', 'In Progress', 'Normal', '2026-10-26', 'chatipat, Chaiwat.u', 'chatipat, Chaiwat.u', 'admin', 'ผู้ดูแลระบบ (Admin)', 'ระดับสั่งการ', NULL, NULL, NULL, 'None', 0, NULL, NULL, NULL) ON CONFLICT (task_id) DO NOTHING;

-- ==================== TASK LOGS ====================
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('c03d4d39-6b9b-414a-906f-0e1a19e77f02', 'e6cbf14b-8ee2-4ab3-a63c-1696462ae698', 'สร้างงานใหม่', 'admin', 'มอบหมายให้: patpongu') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('5741ae4e-7642-440c-baee-bf790bb46072', '7f178111-e2e0-432c-8d25-58c34294ef23', 'สร้างงานใหม่', 'admin', 'มอบหมายให้: chatipat, Voravut') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('0d5df86c-17c6-4b6f-a136-9648373f822e', 'c59049b8-958c-49d0-8ef9-e5172c0df9f9', 'สร้างงานใหม่', 'admin', 'มอบหมายให้: chatipat, Chaiwat.u') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('e749b1d4-ae86-4e66-af4f-282e4d5a458b', 'c59049b8-958c-49d0-8ef9-e5172c0df9f9', 'เริ่มดำเนินงาน', 'chatipat', 'ลากการ์ดงานไป In Progress (Drag & Drop)') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('9d165778-08ad-4ae4-ac51-300bc242c098', '7f178111-e2e0-432c-8d25-58c34294ef23', 'เริ่มดำเนินงาน', 'chatipat', 'ลากการ์ดงานไป In Progress (Drag & Drop)') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('be62a281-85ca-4509-9387-882e2dd76cb0', '7f178111-e2e0-432c-8d25-58c34294ef23', 'ส่งงานเพื่อรออนุมัติ', 'chatipat', 'หมายเหตุ: https://app.svvconnect.io/') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('d9f7ca1c-fde0-4fb0-9271-58881d525e24', '7f178111-e2e0-432c-8d25-58c34294ef23', 'รายงานความคืบหน้า', 'chatipat', 'https://rental.svvconnect.io/') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('6f94de81-b83b-4f05-96a1-0e51c1237cd6', '7f178111-e2e0-432c-8d25-58c34294ef23', 'รายงานความคืบหน้า', 'chatipat', 'โครงสร้างแบบนี้จะดีกว่าฝังครับเพราะคอนโทรลตัวเดียวง่ายและประหยัดแรมมากๆครับ

[ATTACHED_IMAGE: https://drive.google.com/file/d/1wFSz7glnQpRFt5n06SwqACqXxI4oYsXY/view?usp=drive_link]') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('8c99db7a-0ad6-4d11-8d0a-894bb796b49b', '7f178111-e2e0-432c-8d25-58c34294ef23', 'รายงานความคืบหน้า', 'chatipat', '

[ATTACHED_IMAGE: https://drive.google.com/file/d/1m1PpaLbmwje0a2DgumgJg497eREZF-0r/view?usp=drive_link]') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('9e8103d6-8bf4-4294-989e-f47089d7dd52', '7f178111-e2e0-432c-8d25-58c34294ef23', 'รายงานความคืบหน้า', 'chatipat', 'https://db.svvconnect.io/project/default') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('0bcac43f-693c-4d6c-89bf-d8127c7c8892', '7f178111-e2e0-432c-8d25-58c34294ef23', 'รายงานความคืบหน้า', 'chatipat', 'แก้เป็นself hostใช้supabaseครับ

[ATTACHED_IMAGE: https://drive.google.com/file/d/1yLJQ_wfBCENMCvRepuqMbvojAZmrfrBJ/view?usp=drive_link]') ON CONFLICT (log_id) DO NOTHING;
INSERT INTO task_logs (log_id, task_id, action, performed_by, details) VALUES ('2f0ad2ba-27ce-4a5d-82eb-15c0f635b5f2', '7f178111-e2e0-432c-8d25-58c34294ef23', 'แก้ไขผู้รับผิดชอบงาน', 'admin', 'ปรับเปลี่ยนผู้รับผิดชอบเป็น: chatipat, Voravut.U (เหตุผล: ลบuserเก่าสมัครใหม่)') ON CONFLICT (log_id) DO NOTHING;