-- ========================================================
-- Complete Database Setup for Dokploy PostgreSQL (SVV_db)
-- Run this in Dokploy Terminal or pgAdmin / DBeaver
-- ========================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Table: app_users
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

-- 2. Table: tasks
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

-- 3. Table: kpi_adjustments
CREATE TABLE IF NOT EXISTS kpi_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    points NUMERIC NOT NULL,
    reason_type TEXT NOT NULL,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Table: task_logs
CREATE TABLE IF NOT EXISTS task_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT,
    action TEXT NOT NULL,
    performed_by TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Insert Default Admin User
INSERT INTO app_users (username, password_hash, fullname, role, roles, is_approved)
VALUES ('admin', 'admin1234', 'ผู้ดูแลระบบ (Admin)', 'Admin', 'ระดับสั่งการ, ปฏิบัติงาน', TRUE)
ON CONFLICT (username) DO NOTHING;
