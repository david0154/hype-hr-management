# 🏢 Hype HR Management System

<p align="center">
  <img src="logo.png" alt="Hype HR Management Logo" width="180"/>
</p>

<p align="center">
  <b>QR-based Attendance + HR + Payroll System</b><br/>
  Python Tkinter &middot; Android Kotlin &middot; Firebase &middot; PHP
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Android-blue?style=flat-square"/>
  <img src="https://img.shields.io/badge/Backend-Firebase-orange?style=flat-square"/>
  <img src="https://img.shields.io/badge/Automation-PHP-purple?style=flat-square"/>
  <img src="https://img.shields.io/badge/Developed%20by-David-informational?style=flat-square"/>
  <img src="https://img.shields.io/badge/Managed%20by-Nexuzy%20Lab-green?style=flat-square"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square"/>
</p>

---

## 🧠 Overview

**Hype HR Management** is a complete HR + Attendance + Payroll SaaS system for small and medium businesses:

| Layer | Technology |
|---|---|
| 🖥️ Windows Admin App | Python 3.x, Tkinter, Firebase Admin SDK, SQLite Cache |
| 📱 Android App | Kotlin, Firebase SDK, ML Kit QR Scanner, WorkManager |
| ☁️ Cloud Backend | Firebase Auth, Firestore, Storage, Cloud Functions |
| 🐘 PHP Automation | PHP 8.x, PHPMailer, FPDF, vlucas/phpdotenv |

---

## 🧠 Architecture

```
Admin Tkinter App (Role-Based: HR / CA / Manager / Admin / Super Admin)
   |
   v
SQLite Local Cache (instant reads) <--[background sync every 2 min]--> Firebase
   |
   v
Firebase Backend
   |-- Authentication
   |-- Firestore Database
   |-- Cloud Functions (real-time triggers)
   +-- Storage (Salary Slip PDFs, 12-month retention)
          |
          v
Android App                    PHP Cron (1st of every month, 00:05 IST)
   |-- Employee Mode         <-- 1. Fetch attendance from Firestore
   |-- Security/Supervisor      2. Apply duty/OT/Sunday rules
       Mode (QR scanner         3. Calculate salary
       for employees            4. Generate branded PDF
       without phones)          5. Upload to Firebase Storage
                                6. Save salary record to Firestore
                                7. Email employee (if email set + SMTP configured)
                                8. SMS alert (optional: Fast2SMS / MSG91 / Twilio)
                                9. Auto-cleanup slips older than 12 months
```

---

## 📁 Project Structure

```
hype-hr-management/
|-- admin_app/
|   |-- main.py
|   |-- modules/
|   |   |-- auth.py
|   |   |-- dashboard.py
|   |   |-- employees.py
|   |   |-- attendance.py
|   |   |-- salary.py
|   |   |-- id_card.py
|   |   |-- qr_generator.py
|   |   |-- settings.py
|   |   +-- roles.py
|   |-- utils/
|   |   |-- firebase_config.py
|   |   |-- local_cache.py
|   |   |-- db.py
|   |   |-- pdf_generator.py
|   |   +-- validators.py
|   |-- requirements.txt
|   +-- build.spec
|
|-- android_app/
|   +-- app/src/main/java/com/nexuzylab/hypehr/
|       |-- ui/auth/
|       |-- ui/employee/
|       |-- ui/security/
|       |-- data/firebase/
|       |-- utils/
|       |-- util/
|       +-- workers/
|
|-- php_backend/
|   |-- config.php
|   |-- firebase_api.php
|   |-- salary_calculator.php
|   |-- salary_generator.php
|   |-- mailer.php
|   |-- sms_service.php
|   |-- cron_job.php
|   |-- webhook.php
|   |-- install.php              # DELETE after use!
|   |-- composer.json
|   |-- .env.example
|   +-- temp/
|
|-- LICENSE
+-- README.md
```

---

## ⏱️ Attendance & OT Rules

> **Workday = 12 hours.** Both duty and OT use flat credited units — not hourly pay.

### Duty Session (First IN→OUT each day)

| Hours Worked | Status | Days Credited |
|---|---|---|
| < 4 hrs | Absent | 0 |
| 4 – 6.59 hrs | Half Day | 0.5 |
| ≥ 7 hrs | Full Day | 1.0 |

### OT Session (Second IN→OUT same day)

| Hours Worked | OT Status | OT Days Credited |
|---|---|---|
| < 4 hrs | No OT | 0 |
| 4 – 6.59 hrs | Half OT | 0.5 |
| ≥ 7 hrs | Full OT | 1.0 |

> **Key rule:** OT is credited as flat day units — **not per actual hour**.  
> Whether the OT session is 7 hrs or 13 hrs, it counts as **1.0 OT day**.

### ⚠️ Sunday Rule

| Saturday Present | Monday Present | Sunday Pay |
|---|---|---|
| ✔️ Yes | ✔️ Yes | Full Pay (1.0 day) |
| ✔️ Yes | ❌ No | Half Pay (0.5 day) |
| ❌ No | any | No Pay |

> Monday-only presence does **NOT** grant Sunday pay.

---

## 💰 Salary Formula

```
Final Salary = (Base Salary × Attendance Ratio)
             + OT Pay
             + Annual Bonus   ← MARCH ONLY, if employee worked ≥ 240 days previous year
             − Advance

Attendance Ratio = (Full Days + Half Days×0.5 + Paid Sundays) ÷ Monthly Working Days

OT Pay = OT Day Units × (Base Salary ÷ Working Days) × OT Multiplier (default 1.5×)
```

### Annual Bonus Rule

| Condition | Result |
|---|---|
| Month = March **AND** previous year ≥ 240 working days | Bonus added to March salary slip |
| Any other month | Bonus = ₹0 (not shown on slip) |
| March but < 240 days last year | Bonus = ₹0 (not eligible) |

> The bonus line is **hidden on all non-March slips**. It only appears on the March salary slip when the employee is eligible.

---

## 🮾 Salary Slip Format

### Regular Month (Jan, Feb, Apr – Dec except March)

```
============================================================
               HYPE PVT LTD
        123 Business Park, Kolkata, West Bengal
        Email: hr@hype.com  |  Ph: +91 XXXXXXXXXX
============================================================
                    SALARY SLIP
Employee : Rahul Das                     ID: EMP-0001
Month    : April 2026
------------------------------------------------------------
Present Days    : 22
Half Days       :  2
Absent Days     :  4
Paid Holidays   :  4   (Sunday rule)
OT              : 2 Full OT Days + 1 Half OT Day (2.5 units)
------------------------------------------------------------
Base Salary     :  Rs. 15,000
Attendance Sal  :  Rs. 14,000
Overtime Pay    :  Rs.  2,163   (2.5 units x Rs.577 x 1.5x)
Advance Deduct  :  Rs.      0
------------------------------------------------------------
FINAL SALARY    :  Rs. 16,163
Payment Mode    : CASH
------------------------------------------------------------
                   Authorized Signature
============================================================
```

### March Slip (Annual Bonus Month)

```
============================================================
               HYPE PVT LTD
        123 Business Park, Kolkata, West Bengal
        Email: hr@hype.com  |  Ph: +91 XXXXXXXXXX
============================================================
                    SALARY SLIP
Employee : Rahul Das                     ID: EMP-0001
Month    : March 2026
------------------------------------------------------------
Present Days    : 24
Half Days       :  1
Absent Days     :  2
Paid Holidays   :  3   (Sunday rule)
OT              : 1 Full OT Day (1.0 unit)
------------------------------------------------------------
Base Salary     :  Rs. 15,000
Attendance Sal  :  Rs. 14,423
Overtime Pay    :  Rs.    865   (1.0 unit x Rs.577 x 1.5x)
Annual Bonus    :  Rs.  5,000   (eligible: 262 days worked in 2025)
Advance Deduct  :  Rs.      0
------------------------------------------------------------
FINAL SALARY    :  Rs. 20,288
Payment Mode    : CASH
------------------------------------------------------------
                   Authorized Signature
============================================================
```

---

## 🔐 Admin App — Default Super Admin Login

| Field | Value |
|---|---|
| **Username** | `admin.hype` |
| **Password** | `Hype@2024#SuperAdmin` |
| **Role** | Super Admin |

> ⚠️ **Change the password immediately after first login** via Settings → My Account.

---

## 👥 Role-Based Access

| Role | Dashboard | Employees | Attendance | Salary | Bonus | Salary Raise | QR | ID Card | Settings |
|---|---|---|---|---|---|---|---|---|---|
| Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HR Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| CA | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manager | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 🛠️ Setup Guides

---

### 🖥️ Windows Admin App Setup

#### Requirements
- Windows 10 / 11
- Python 3.10 or higher
- Firebase project (service account JSON)

#### Step 1 — Clone the repo
```bash
git clone https://github.com/david0154/hype-hr-management.git
cd hype-hr-management/admin_app
```

#### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

#### Step 3 — Add Firebase service account
1. Firebase Console → Project Settings → Service Accounts → **Generate new private key**
2. Save as `admin_app/firebase-service-account.json`
3. Open `utils/firebase_config.py` and set:
```python
SERVICE_ACCOUNT_PATH = "firebase-service-account.json"
STORAGE_BUCKET       = "your-project-id.appspot.com"
```

#### Step 4 — Run the app
```bash
python main.py
```
Login: `admin.hype` / `Hype@2024#SuperAdmin`

#### Step 5 — Configure company
- Settings → 🏢 Company → fill name, address, email, phone, domain
- Settings → 📧 SMTP → add email credentials

#### Step 6 — Build EXE (optional)
```bash
pip install pyinstaller
pyinstaller build.spec
# Output: dist/HypeHR.exe
```
Copy `firebase-service-account.json` next to the EXE.

---

### 📱 Android App Setup

#### Requirements
- Android Studio Hedgehog or newer
- Android SDK 26+
- Same Firebase project as admin app

#### Step 1 — Add Firebase to Android
1. Firebase Console → Project Settings → Add Android App
2. Package name: `com.nexuzylab.hypehr`
3. Download `google-services.json`
4. Place in `android_app/app/google-services.json`

#### Step 2 — Open in Android Studio
```
File → Open → select android_app/ folder
```

#### Step 3 — Enable Firebase services
- ✅ Authentication (Email/Password)
- ✅ Firestore Database
- ✅ Storage

#### Step 4 — Firestore rules
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /employees/{id} {
      allow read: if request.auth != null;
      allow write: if false;
    }
    match /attendance_logs/{id} {
      allow read, write: if request.auth != null;
    }
    match /salary/{id} {
      allow read: if request.auth != null;
      allow write: if false;
    }
  }
}
```

#### Step 5 — Build APK
```bash
cd android_app/
./gradlew assembleRelease
```

#### Step 6 — First employee login
1. HR creates employee in Admin App
2. Employee opens app → username + password → sets 4-digit PIN
3. Dashboard opens instantly on next launch via PIN

#### Security / Supervisor Mode
1. Supervisor opens app → **Security Mode**
2. Login with supervisor credentials
3. Scan employee ID card QR → tap IN or OUT

---

### 🐘 PHP Backend Setup

#### Requirements
- PHP ≥ 7.4 (8.x recommended)
- Composer
- Hosting with cron job support + `allow_url_fopen = On`

#### Option A — One-Click Install (Recommended)

1. Upload `php_backend/` folder to your hosting
2. Visit: `https://yoursite.com/php_backend/install.php`
3. Fill Firebase Project ID, service account JSON, SMTP, SMS (optional)
4. Click **Install**
5. ⚠️ **Delete `install.php` immediately after!**

#### Option B — Manual Install

```bash
# Upload files then SSH in
cd /var/www/html/hype-hr/
composer install
cp .env.example .env
nano .env
```

**.env values:**
```dotenv
# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_JSON=/var/www/html/hype-hr/firebase-service-account.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_API_KEY=your-web-api-key

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your@gmail.com
SMTP_FROM_NAME=Hype HR Management
SMTP_ENCRYPTION=tls

# SMS (optional)
SMS_ENABLED=false
SMS_PROVIDER=fast2sms
SMS_API_KEY=your_api_key

# Security
API_SECRET=your-random-32-char-secret
```

```bash
# Set permissions
chmod 755 temp/
chmod 644 .env
chmod 600 firebase-service-account.json
```

#### Cron Job
```bash
crontab -e
# Add:
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/hype-hr/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
```

#### Test manually
```bash
php /var/www/html/hype-hr/cron_job.php
# or via browser:
https://yoursite.com/hype-hr/webhook.php?secret=your-api-secret
```

#### Gmail SMTP — App Password
1. Google Account → Security → Enable 2-Step Verification
2. Google Account → Security → App passwords → create one
3. Use the 16-char password as `SMTP_PASSWORD`

#### SMS Providers

| Provider | Best For |
|---|---|
| **Fast2SMS** | India (cheapest) |
| **MSG91** | India (bulk/OTP) |
| **Twilio** | International |

---

## 📧 Email + 📱 SMS Flow

```
Cron runs (1st of month, 00:05 IST)
  └── For each active employee:
       1. Fetch attendance from Firestore
       2. Apply duty / OT / Sunday rules
       3. Calculate salary
          └─ If month = March AND prev year ≥ 240 days → add annual bonus
          └─ All other months → no bonus line
       4. Generate branded PDF salary slip
       5. Upload PDF to Firebase Storage
       6. Save record to Firestore (with 12-month expiry)
       7. If employee.email exists → send PDF via email (PHPMailer)
       8. If SMS_ENABLED → send SMS notification
       9. Cleanup slips older than 12 months
```

---

## 🗄️ Firebase Structure

```
Firestore
|-- employees/{emp_id}
|   |-- name, username, mobile, aadhaar, salary
|   |-- designation, department, photo_url
|   |-- annual_bonus_amount, advance
|   +-- status: active | inactive
|
|-- attendance_logs/{log_id}
|   |-- employee_id, action: IN | OUT
|   |-- timestamp, location
|   +-- scanned_by (if security mode)
|
|-- sessions/{session_id}
|   |-- employee_id, date
|   |-- duty_hours, duty_status: full | half | absent
|   |-- ot_hours,  ot_status:   full | half | none
|   +-- ot_day_units: 0 / 0.5 / 1.0
|
|-- salary/{emp_id}_{YYYY_MM}
|   |-- base_salary, attendance_salary, ot_pay
|   |-- annual_bonus  ← 0 for non-March, set only if eligible in March
|   |-- advance, final_salary, payment_mode, slip_url
|   |-- ot_full_days, ot_half_days, ot_day_units
|   +-- slip_expires_at (12 months from generation)
|
|-- admin_users/{username}
|   |-- username, display_name, role, password_hash
|   +-- active, must_change_password
|
|-- settings/company
|   |-- name, address, email, phone, company_domain
|   |-- smtp_host, smtp_port, smtp_user, smtp_pass
|   +-- ot_rate_multiplier, default_payment_mode
```

---

## 🔐 Security

- Unique username: `name.company` (e.g. `rahul.nexuzy`)
- Aadhaar validation on employee creation
- Admin passwords hashed with SHA-256
- 15-minute QR scan cooldown (prevents double scan)
- RBAC: Super Admin / Admin / HR / CA / Manager
- PHP API endpoints protected by `API_SECRET`
- Salary slips auto-expire after 12 months
- Firebase service account kept outside web root

---

## 📱 Android App Features

### Employee Mode
- PIN login after first-time setup
- Dashboard: present/absent/OT days, today’s status
- Attendance history: date-wise IN/OUT logs
- Salary: monthly list + PDF download (last 12 months)
- Auto salary generation on 1st of month (WorkManager, IST)

### Security / Supervisor Mode
- Login with supervisor credentials
- Scan employee ID card QR code
- Mark IN/OUT for employees without smartphone
- All scans synced to Firestore in real-time

---

## 🖥️ Admin App Modules

| Module | Features |
|---|---|
| 🏠 Dashboard | Live attendance count, employees inside |
| 👥 Employees | CRUD, activate/deactivate, ID card generator |
| 📅 Attendance | Logs, IN/OUT timeline, date filters |
| 💰 Salary | Generate all, Bonus panel (March only), Salary Raise |
| 🔳 QR Generator | Location QR codes for gates/floors |
| 🪪 ID Cards | PNG ID card with QR (single or bulk export) |
| ⚙️ Settings | Company, SMTP, Salary Rules, Admin Users, My Account |

---

## 📦 Build

```bash
# Admin App (Windows EXE)
cd admin_app/
pip install -r requirements.txt
pyinstaller build.spec
# Output: dist/HypeHR.exe

# Android APK
cd android_app/
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release.apk
```

---

## ⚡ Performance Notes

The admin app uses a **local SQLite cache** to make all reads instant:

| Operation | Without Cache | With Cache |
|---|---|---|
| Load employee list | ~1–3 sec (Firebase) | < 5ms (SQLite) |
| Load salary records | ~1–2 sec | < 5ms |
| Write (save employee) | ~300–800ms | ~300ms (write-through) |
| Background sync | — | Every 2 min (daemon thread) |

---

## 🚀 Roadmap

- [ ] Face recognition attendance
- [ ] GPS geo-fencing validation
- [ ] Leave management system
- [ ] Multi-branch support
- [ ] WhatsApp delivery (Twilio / WATI)
- [ ] Employee self-service web portal
- [ ] Migrate usernames (bulk rename domain)
- [ ] Android Room DB cache

---

## 👨‍💻 Developer

**David** | Nexuzy Lab  
📧 [nexuzylab@gmail.com](mailto:nexuzylab@gmail.com)  
🔗 [github.com/david0154](https://github.com/david0154)  
📱 Built for Indian SMBs with love from Kolkata ❤️

---

<p align="center">
  <sub>© 2026 Nexuzy Lab — Hype HR Management System. MIT License.</sub>
</p>
