# Team Workflow SVV (FastAPI + Modern Web UI)

ระบบจัดการงานและประเมินผล KPI ทีมงาน SVV ในรูปแบบ **FastAPI Single App** (ไม่ใช้ Streamlit)
- **Refresh หน้าไม่หลุด 100%:** จดจำ Token ผ่าน LocalStorage / JWT
- **จำหน้าเดิมผ่าน URL:** เช่น `svvconnect.io/?page=kanban` กดรีเฟรชจะเปิดหน้าเดิมทันที
- **โครงสร้างข้อมูลเดิม:** ใช้ Supabase เดิม (`app_users`, `tasks`, `kpi_adjustments`, `task_logs`) ข้อมูลและโฟลว์งานไม่เปลี่ยนแปลง

---

## 🚀 วิธีรันบนเครื่อง Local หรือทดสอบ

1. ติดตั้ง Library (ถ้ายังไม่ได้ติดตั้ง):
```bash
pip install -r requirements.txt
```

2. รันเซิร์ฟเวอร์:
```bash
python run.py
```
3. เปิดเบราว์เซอร์ไปที่: `http://localhost:8000`

---

## 🌐 วิธีนำขึ้น Hostinger VPS (svvconnect.io)

### วิธีที่ 1: รันด้วย Docker (แนะนำและง่ายที่สุด)

1. อัปโหลดโฟลเดอร์ `workflow_system` ขึ้นไปบน VPS
2. เข้าไปในโฟลเดอร์แล้วสั่ง:
```bash
docker compose up -d --build
```
ระบบจะรัน Service พอร์ต `8000` ทันที

---

### วิธีที่ 2: รันด้วย Systemd (Service พื้นฐาน)

1. อัปโหลดไฟล์ขึ้น VPS (เช่นไว้ที่ `/var/www/workflow_system`)
2. สร้าง Service file:
```bash
sudo nano /etc/systemd/system/svv-workflow.service
```
ใส่ข้อความ:
```ini
[Unit]
Description=Team Workflow SVV FastAPI Service
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/workflow_system
ExecStart=/usr/bin/python3 run.py
Restart=always

[Install]
WantedBy=multi-user.target
```
3. สั่งเริ่มระบบ:
```bash
sudo systemctl daemon-reload
sudo systemctl start svv-workflow
sudo systemctl enable svv-workflow
```

---

### การตั้งค่า Nginx ให้กับโดเมน `svvconnect.io`

นำเนื้อหาในไฟล์ `nginx_svvconnect.conf` ไปใส่ใน `/etc/nginx/sites-available/svvconnect.io` แล้วสั่ง:
```bash
sudo ln -s /etc/nginx/sites-available/svvconnect.io /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```
และเปิด SSL ฟรีด้วย Certbot:
```bash
sudo certbot --nginx -d svvconnect.io -d www.svvconnect.io
```
