-- ========================================================
-- SQL Migration Script for Workflow System
-- Run this script in Supabase SQL Editor
-- ========================================================

-- 1. เพิ่มคอลัมน์ในตาราง app_users สำหรับเก็บข้อมูลพนักงานและการอนุมัติสิทธิ์
ALTER TABLE app_users 
ADD COLUMN IF NOT EXISTS fullname TEXT,
ADD COLUMN IF NOT EXISTS email TEXT,
ADD COLUMN IF NOT EXISTS phone TEXT,
ADD COLUMN IF NOT EXISTS roles TEXT DEFAULT 'ปฏิบัติงาน',
ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;

-- ให้สิทธิ์ Admin เดิมให้ได้รับการอนุมัติและมียศครบทุกระดับ
UPDATE app_users 
SET is_approved = TRUE, 
    roles = 'ระดับสั่งการ, ปฏิบัติงาน',
    fullname = 'ผู้ดูแลระบบ (Admin)'
WHERE username = 'admin' OR role = 'Admin';

-- 2. เพิ่มคอลัมน์ในตาราง tasks สำหรับระบบสั่งการ, การส่งต่อ, และการประเมิน KPI
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

-- 3. สร้างตาราง kpi_adjustments สำหรับบันทึกคะแนนเพิ่ม/ลด (ความดีความชอบ / ความผิดพลาด)
CREATE TABLE IF NOT EXISTS kpi_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    points NUMERIC NOT NULL,
    reason_type TEXT NOT NULL, -- 'ความดีความชอบ' หรือ 'ความผิดพลาด'
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. สร้างตาราง task_logs สำหรับบันทึกประวัติการส่งต่องานและการเปลี่ยนสถานะ
CREATE TABLE IF NOT EXISTS task_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID,
    action TEXT NOT NULL,
    performed_by TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. ปิด RLS เพื่อให้ API สามารถอ่านและเขียนข้อมูลตารางใหม่ได้
ALTER TABLE IF EXISTS kpi_adjustments DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_logs DISABLE ROW LEVEL SECURITY;

-- ให้สิทธิ์การเข้าถึงแก่ anon และ authenticated
GRANT ALL ON TABLE app_users TO anon, authenticated, service_role;
GRANT ALL ON TABLE tasks TO anon, authenticated, service_role;
GRANT ALL ON TABLE kpi_adjustments TO anon, authenticated, service_role;
GRANT ALL ON TABLE task_logs TO anon, authenticated, service_role;
