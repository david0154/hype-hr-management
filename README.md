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
| 🖥️ Windows Admin App | Python 3.x, Tkinter, Firebase Admin SDK |
| 📱 Android App | Kotlin, Firebase SDK, ML Kit QR Scanner |
| ☁️ Cloud Backend | Firebase Auth, Firestore, Storage, Cloud Functions |
| 🐘 PHP Automation | PHP 8.x, PHPMailer, FPDF, vlucas/phpdotenv |

---

## 🧠 Architecture

```
Admin Tkinter App (Role-Based: HR / CA / Manager / Admin)
   |
   v
Firebase Backend
   |-- Authentication
   |-- Firestore Database
   |-- Cloud Functions (real-time triggers)
   +-- Storage (Salary Slip PDFs, 1-yr retention)
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
|-- admin_app/                   # Python Tkinter Windows App
|   |-- main.py
|   |-- modules/
|   |   |-- auth.py              # Login + role management
|   |   |-- dashboard.py         # Live attendance dashboard
|   |   |-- employees.py         # Employee CRUD + ID card
|   |   |-- attendance.py        # Logs + duty/OT/Sunday rules
|   |   |-- salary.py            # Salary calc + PDF + email
|   |   |-- qr_generator.py      # Location QR + Employee ID card
|   |   |-- settings.py          # Company + SMTP + OT rate
|   |   +-- roles.py             # RBAC definitions
|   |-- utils/
|   |   |-- firebase_config.py
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
|       |-- utils/               # SalaryCalculator (canonical), SessionManager
|       |-- util/                # PdfUploader; SalaryCalculator here is @Deprecated → use utils/
|       +-- workers/             # SalarySlipAutoGenerateWorker (WorkManager)
|
|-- php_backend/
|   |-- config.php
|   |-- firebase_api.php         # Firestore + Storage REST wrapper
|   |-- salary_calculator.php    # Pure salary calculation
|   |-- salary_generator.php     # FPDF PDF builder
|   |-- mailer.php               # PHPMailer SMTP
|   |-- sms_service.php          # Fast2SMS / MSG91 / Twilio (optional)
|   |-- cron_job.php             # Monthly entry point
|   |-- webhook.php              # Manual trigger
|   |-- install.php              # One-click installer (delete after use)
|   |-- composer.json
|   |-- .env.example
|   +-- temp/
|
+-- logo.png
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

| Hours Worked | Status | OT Days Credited |
|---|---|---|
| < 4 hrs | No OT | 0 |
| 4 – 6.59 hrs | Half OT | 0.5 |
| ≥ 7 hrs | Full OT | 1.0 |

> **Key rule:** OT is credited as flat day units — **not per actual hour**.
> Whether the OT session is 7 hrs or 13 hrs, it counts as **1.0 OT day**.
> Max = 1.0 OT day per session.

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
             + Bonus
             − Deduction
             − Advance

Attendance Ratio = (Full Days + Half Days×0.5 + Paid Sundays) ÷ Monthly Working Days

OT Pay = OT Days × (Base Salary ÷ Working Days) × OT Multiplier (default 1.5×)
         └─ OT Days = flat units: 0 / 0.5 / 1.0 per OT session
         └─ NOT hourly rate — actual hours only determine the tier (0 / 0.5 / 1.0)
```

**Example:**
- Employee OT session = 9 hrs → counts as **1.0 OT day**
- OT Pay = 1.0 × (₹15000 ÷ 26) × 1.5 = **₹865.38**

---

## 🧾 Salary Slip Format

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
Half Days       : 2
Absent Days     : 4
Paid Holidays   : 4   (Sunday rule)
OT Days         : 3.0 (flat units: 0/0.5/1.0 per session)
------------------------------------------------------------
Base Salary     :  ₹ 15,000
Attendance Sal  :  ₹ 14,000
Overtime Pay    :  ₹  1,731   (3 days × ₹577 × 1.5×)
Bonus           :  ₹  1,000
Deduction       : −₹    500
Advance         :  ₹      0
------------------------------------------------------------
FINAL SALARY    :  ₹ 16,231
Payment Mode    : CASH
------------------------------------------------------------
                   Authorized Signature
============================================================
```

---

## 🚀 PHP Backend Setup

### Requirements
- PHP >= 7.4 (PHP 8.x recommended)
- Composer
- Firebase project with Firestore, Storage, and Auth enabled
- Hosting with cron job support

### 1. One-Click Install

```
https://yoursite.com/hype-hr/install.php
```

> ⚠️ **Delete `install.php` immediately after installation!**

### 2. Manual Install

```bash
cd php_backend/
cp .env.example .env
nano .env
composer install
chmod 755 temp/
chmod 644 .env
chmod 600 firebase-service-account.json
```

### 3. Cron Job

```bash
# Runs at 00:05 IST on the 1st of every month
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/php_backend/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
```

### 4. SMTP Config (Firestore `settings/smtp`)

```json
{
  "enabled": true,
  "host": "smtp.gmail.com",
  "port": 587,
  "username": "your@gmail.com",
  "password": "your-app-password",
  "from_email": "your@gmail.com",
  "from_name": "Hype HR Management",
  "encryption": "tls"
}
```

---

## 📧 Email + 📱 SMS

### Email (PHPMailer + SMTP)
- Auto-sent 1st of every month with PDF attached
- Only sent if employee has `email` in Firestore profile

### SMS (Optional)

| Provider | Region |
|---|---|
| **Fast2SMS** | India ✅ |
| **MSG91** | India |
| **Twilio** | International |

```bash
SMS_ENABLED=true
SMS_PROVIDER=fast2sms
SMS_API_KEY=your_api_key
```

---

## 🗄️ Firebase Structure

```
Firestore
|-- employees/{emp_id}
|-- attendance_logs/{log_id}
|-- sessions/{session_id}
|   |-- duty_hours  : float   # first IN→OUT
|   +-- ot_hours    : float   # second IN→OUT
|-- salary/{emp_id}_{month_key}
|   |-- ot_days     : float   # 0 / 0.5 / 1.0 flat units
|   +-- expires_at  : Timestamp  # 12-month auto-cleanup
|-- settings/smtp
|-- settings/company
+-- settings/app
```

---

## 🔐 Security

- Unique username: `name.company` (e.g. `rahul.hype`)
- Aadhaar validation on employee creation
- 15-min QR scan cooldown (prevent double scan)
- RBAC: HR / CA / Manager / Admin
- API endpoints protected by `API_SECRET`
- Salary slips auto-expire after 12 months

---

## 📱 Android App

### Employee Mode
- PIN login after first-time setup
- Dashboard: present/absent/OT days, today status
- Attendance history: date-wise IN/OUT
- Salary: monthly list + download (last 12 months)
- Auto salary generation on 1st of month (WorkManager, IST)

### Security / Supervisor Mode
- Scan employee QR from ID card
- Mark IN/OUT for employees without smartphone

---

## 🖥️ Admin App (Python Tkinter)

| Module | Features |
|---|---|
| Dashboard | Live attendance, inside count |
| Employees | CRUD, activate/deactivate, ID card print |
| Attendance | Logs, IN/OUT timeline, filters |
| Salary | Generate/edit, bonus/deduction/advance |
| QR Generator | Location QRs + Employee ID cards |
| Settings | Company details, SMTP, OT rate, working days |
| Roles | HR / CA / Manager / Admin permissions |

---

## 📦 Build

```bash
# Admin App (Windows EXE)
cd admin_app/
pip install -r requirements.txt
pyinstaller --onefile --windowed --name HypeHR main.py

# Android APK
cd android_app/
./gradlew assembleRelease
```

---

## 🚀 Roadmap

- [ ] Face recognition
- [ ] GPS geo-fencing
- [ ] Leave management
- [ ] Multi-branch support
- [ ] WhatsApp delivery
- [ ] Employee web portal

---

## 👨‍💻 Developer

**David** | Nexuzy Lab  
📧 nexuzylab@gmail.com  
🔗 [github.com/david0154](https://github.com/david0154)  
📱 Built for Indian SMBs with love from Kolkata ❤️

---

<p align="center">
  <sub>© 2026 Nexuzy Lab — Hype HR Management System. MIT License.</sub>
</p>
