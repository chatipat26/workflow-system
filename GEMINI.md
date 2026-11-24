# Project Context & AI Agent Rules — Accounting Automation (GEMINI.md)

## 1. การสื่อสารและการอธิบาย (Communication)
- **ภาษาที่ใช้:** ตอบคำถาม อธิบายขั้นตอน และสรุปการแก้ไขเป็น **ภาษาไทยที่กระชับ ตรงประเด็น**
- **ก่อนลงมือแก้โค้ดหรือ Workflow ใหญ่:** หากต้องแก้หลายไฟล์หรือเปลี่ยนโครงสร้าง Mapping ข้อมูล ให้สรุปแผนและจุดที่กระทบให้ยืนยันก่อนลงมือทำ

---

## 2. Tech Stack & โครงสร้างงาน Automation
- **Workflow & Integration:** n8n (JSON workflows, Webhooks, Code nodes), Python Scripts
- **Data & OCR:** Typhoon OCR, Google Sheets API, Google Drive, Netforce ERP (JSON-RPC)
- **Infrastructure:** Ubuntu VPS (Hostinger), Docker / Docker Compose, GitHub

---

## 3. กฎเหล็กสำหรับงานบัญชีและการกระทบยอด (Accounting & Reconciliation Rules)
- **ความแม่นยำของตัวเลข (Financial Precision):** ใน Python ให้ใช้ `Decimal` (จากโมดูล `decimal`) สำหรับการคำนวณยอดเงิน, ฐานภาษี, และ VAT 7% **ห้ามใช้ `float` คำนวณเงินโดยตรง** เพื่อป้องกันปัญหาทศนิยมคลาดเคลื่อน
- **มาตรฐานข้อมูลภาษีไทย:**
  - **เลขประจำตัวผู้เสียภาษี (Tax ID):** เก็บเป็น `String` เสมอ (13 หลัก) ห้ามเก็บเป็น `Integer` เพราะเลข `0` นำหน้าจะหาย
  - **รูปแบบวันที่:** ระวังการแปลงปี พ.ศ. (เช่น `2569` หรือ `69`) เป็น ค.ศ. (`2026`) และตรวจสอบ Format (`DD/MM/YYYY` vs `YYYY-MM-DD`) ให้ตรงกันระหว่างเอกสาร OCR กับข้อมูลจากระบบบัญชี
- **การจัดการข้อมูลไม่ตรงกัน (Mismatch Handling):** เมื่อเขียน Logic กระทบยอด (เช่น ภ.พ.30, ภ.ง.ด. 1, 3, 53) ให้แยกเคสชัดเจนระหว่าง *ยอดตรงกัน*, *ยอดต่างกัน (ระบุผลต่าง)*, และ *เอกสารตกหล่น* ห้ามข้ามรายการที่ Error ไปเงียบๆ

---

## 4. กฎการทำงานกับ API, n8n และทีม (Workflow & Security)
- **Rate Limit & Retry:** หากเขียนสคริปต์หรือโหนดเรียก External API (เช่น Typhoon OCR, Google Sheets, Netforce) ต้องใส่หน่วงเวลา (Wait/Sleep) และระบบ Retry เสมอเพื่อป้องกัน API บล็อกหรือ Timeout
- **ห้ามแก้ไฟล์ระบบและข้อมูลลับ:** ห้ามแก้ไข `.env`, `docker-compose.yml` โดยพลการ และห้าม Hardcode API Key, Token หรือ Credential ลงในโค้ดหรือไฟล์ JSON ของ n8n เด็ดขาด
- **ตรวจสอบ Git Status เสมอ:** เช็ก `git status` และ `git branch` ก่อนแก้ไฟล์เพื่อป้องกันการเขียนทับงานของทีม

---

## 5. การตรวจสอบหลังแก้ไข (Post-Edit Verification)
- ทดสอบ Logic การคำนวณด้วยตัวอย่างเคสที่มีทศนิยม, ยอดเป็น 0, หรือค่าว่าง (`null`/`None`) ทุกครั้งก่อนสรุปงาน
- หากเพิ่ม Python Library ใหม่ ให้อัปเดตลง `requirements.txt` เสมอ
