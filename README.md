# TRUST LAB THAILAND — Django + Ajax + Bootstrap 5 + PostgreSQL

ระบบใหม่ที่ย้ายมาจากโปรเจกต์เดิม (`Documents/trustlab` : Next.js + Django REST) ให้เหลือโปรเจกต์ Django เดียว
หน้าเว็บใช้ Django Template + Bootstrap 5.3.8 (เก็บในโปรเจกต์ ไม่ใช้ CDN) + JavaScript ล้วน (Ajax ผ่าน `fetch`)
ไอคอนเป็นชุด lucide เดิม รวมเป็นไฟล์ `static/icons/sprite.svg` (ไม่มีอิโมจิ)

## โครงสร้าง

```
config/settings/{base,local,production,test}.py   แยก settings ตามสภาพแวดล้อม
config/celery.py                                  Celery app
apps/
  core/          ตัวช่วยกลาง: decorator สิทธิ์ + Ajax, ไอคอน, PromptPay, ไฟล์ที่สร้างเบื้องหลัง (GeneratedFile)
  accounts/      StaffUser, Branch, หน้า login พนักงาน
  catalog/       แพ็กเกจ ราคา ระดับสมาชิก โค้ดส่วนลด   -> services/pricing_service.py (คิดราคา)
  customers/     ลูกค้า กระเป๋าเครดิต เติมเงิน          -> services/credit_service.py
  bookings/      การจอง ชำระเงิน ยกเลิก/คืนเงิน
  inspections/   งานตรวจ ใบรับรอง ส่งคืน รูปภาพ walk-in
  inquiries/     ฟอร์มติดต่อ / พาร์ทเนอร์
  notifications/ อีเมล LINE WeChat (ทำงานใน Celery)
  audit/         WorkflowEvent (ประวัติการทำรายการ)
  reports/       สรุปยอดรายวัน + PDF
  website/       หน้าเว็บสาธารณะ + หน้าสมาชิก
  backoffice/    ระบบหลังบ้านสำหรับพนักงาน (แทน Django Admin)
```

หน้าตาเว็บลอกจากโค้ด Next.js เดิมทีละ component (สี ขนาดตัวอักษร ระยะห่าง เท่าเดิม) อยู่ใน
`static/css/public.css` (หน้าเว็บ) และ `static/css/backoffice.css` (หลังบ้าน) ไอคอนที่เว็บเดิมวาดเองอยู่ใน `scripts/custom_icons.py`

ทุกแอปแยก `services/` (business logic) และ `selectors/` (query) — view แค่รับ request → เรียก service → ตอบกลับ

## เริ่มใช้งานบนเครื่อง

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements/local.txt
cp .env.example .env        # แก้ DATABASE_URL, DJANGO_SECRET_KEY และตั้ง CELERY_TASK_ALWAYS_EAGER=true ถ้าไม่มี Redis
createdb trustlabx
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

- หน้าเว็บ: http://localhost:8000/
- หลังบ้าน: http://localhost:8000/login/ → /authenzs/administator/ (path เดียวกับเว็บเดิม)
- หน้าผู้เชี่ยวชาญ: /authenzs/expert/jobs/ (expert ล็อกอินแล้วเข้าหน้านี้อัตโนมัติ)
- Django Admin เดิม (เฉพาะ superuser): /django-admin/

ทดสอบ: `.venv/bin/python manage.py test --settings=config.settings.test`

## Production

```bash
DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 127.0.0.1:8000
celery -A config worker -l info          # ต้องรันคู่กันเสมอ (อีเมล, PDF, LINE)
```

- `DEBUG=False`, HTTPS, HSTS, secure cookies ตั้งไว้ใน `production.py`
- Static: WhiteNoise (hashed + compressed) หรือให้ Nginx เสิร์ฟ `staticfiles/`
- Media (รูปสินค้า สลิป PDF): ให้ Nginx เสิร์ฟ `MEDIA_ROOT` ที่ `/media/`
- ต้องมี Redis สำหรับ Celery (`CELERY_BROKER_URL`)

## ต่อกับฐานข้อมูลเดิม

ทุก model ใช้ชื่อตารางเดิม (`bookings`, `jobs`, `certificates`, `staff_users`, `api_creditentry` ฯลฯ)
migration แรกของแต่ละแอปตรงกับ schema เดิม ส่วนที่เพิ่มใหม่ (index, `payment_slip`, `GeneratedFile`) อยู่ใน migration ถัดไป

```bash
# สำรองฐานข้อมูลก่อนเสมอ
pg_dump -Fc trustlab > trustlab-before-migrate.dump
DATABASE_URL=postgres:///trustlab python manage.py migrate --fake-initial
```

ข้อควรรู้: ตาราง `django_content_type` และสิทธิ์ (permissions) ของแอป `api` เดิมจะไม่ถูกใช้ — ไม่กระทบข้อมูลธุรกิจ

## Celery tasks

| งาน | ที่อยู่ |
|---|---|
| อีเมลยืนยันชำระเงิน / แจ้งผล / ส่งใบรับรอง | `apps/notifications/tasks.py` |
| แจ้ง LINE กลุ่มเมื่อมีการจอง, outbox แจ้งพนักงาน | `apps/notifications/tasks.py` |
| สร้าง PDF ใบรับรอง, รายงาน, ใบปะหน้า, ZIP รูป | `apps/core/tasks.py` → builders ใน services |

ใบเสร็จ / ใบกำกับภาษี / ใบรับสินค้า เป็นหน้าพิมพ์ HTML (เหมือนเว็บเดิม) ไม่ต้องผ่าน Celery: `apps/bookings/services/tax_document_service.py`
ข้อมูลผู้ขายบนเอกสารตั้งได้ใน `.env` (`COMPANY_*`)

หน้าเว็บขอไฟล์ → ได้ `status_url` → `TL.waitForFile()` รอจนพร้อม แล้วดาวน์โหลด

## สิ่งที่ยังไม่ได้ย้าย (เฟสถัดไป)

- แอปกล้อง `trustlabcam` แบบเต็มจอ และหน้า POS display สำหรับลูกค้า (ตอนนี้ถ่าย/อัปโหลดรูปได้จาก modal งานใน Job List)
- เข้าสู่ระบบด้วย LINE, ตรวจสลิปอัตโนมัติ EasySlip
- เนื้อหาหน้า about/services แบบเต็มทุกย่อหน้า และคำแปลภาษาอังกฤษของหน้าภายใน
