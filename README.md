# \ud83c\udfe2 Hype HR Management System

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

## \ud83e\udde0 Overview

**Hype HR Management** is a complete HR + Attendance + Payroll SaaS system for small and medium businesses:

| Layer | Technology |
|---|---|
| \ud83d\udda5\ufe0f Windows Admin App | Python 3.x, Tkinter, Firebase Admin SDK |
| \ud83d\udcf1 Android App | Kotlin, Firebase SDK, ML Kit QR Scanner |
| \u2601\ufe0f Cloud Backend | Firebase Auth, Firestore, Storage, Cloud Functions |
| \ud83d\udc18 PHP Automation | PHP 8.x, PHPMailer, FPDF, vlucas/phpdotenv |

---

## \ud83e\udde0 Architecture

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
Android App                    PHP Cron (1st of every month)
   |-- Employee Mode         <-- 1. Fetch attendance from Firestore
   |-- Security/Supervisor      2. Apply duty/OT/Sunday rules
       Mode (QR scanner         3. Calculate salary
       for employees            4. Generate branded PDF
       without phones)          5. Upload to Firebase Storage
                                6. Save salary record to Firestore
                                7. Email employee (if mail set + SMTP)
                                8. SMS alert (optional: Fast2SMS/MSG91/Twilio)
                                9. Cleanup slips older than 12 months
```

---

## \ud83d\udcc1 Project Structure

```
hype-hr-management/
|-- admin_app/                   # Python Tkinter Windows App
|   |-- main.py                  # Entry point + sidebar nav
|   |-- modules/
|   |   |-- auth.py              # Login + role management (HR/CA/Manager/Admin)
|   |   |-- dashboard.py         # Live attendance dashboard
|   |   |-- employees.py         # Employee CRUD + ID card generation
|   |   |-- attendance.py        # Logs + duty/OT/Sunday rules engine
|   |   |-- salary.py            # Salary calc + PDF + email
|   |   |-- qr_generator.py      # Location QR + Employee ID card QR
|   |   |-- settings.py          # Company details + SMTP + OT rate
|   |   +-- roles.py             # RBAC definitions
|   |-- utils/
|   |   |-- firebase_config.py
|   |   |-- pdf_generator.py     # Salary slip FPDF (backup)
|   |   +-- validators.py        # Aadhaar/PAN/mobile validators
|   |-- requirements.txt
|   +-- build.spec
|
|-- android_app/                 # Kotlin Android App
|   +-- app/src/main/java/com/nexuzylab/hypehr/
|       |-- ui/auth/             # Login + PIN setup screens
|       |-- ui/employee/         # Dashboard, history, salary list
|       |-- ui/security/         # Security/Supervisor QR scan mode
|       |-- data/firebase/       # Firestore + Storage helpers
|       +-- utils/               # QR scanner, salary auto-trigger
|
|-- php_backend/                 # PHP Automation Backend
|   |-- config.php               # Constants + .env loader
|   |-- firebase_api.php         # Firestore + Storage REST API wrapper
|   |-- salary_calculator.php    # Pure salary calculation logic
|   |-- salary_generator.php     # FPDF salary slip PDF builder
|   |-- mailer.php               # PHPMailer SMTP email sender
|   |-- sms_service.php          # Fast2SMS / MSG91 / Twilio SMS (optional)
|   |-- cron_job.php             # Monthly automation entry point
|   |-- webhook.php              # Manual trigger endpoint (API_SECRET protected)
|   |-- install.php              # One-click web installer (delete after use)
|   |-- composer.json            # PHP dependencies
|   |-- .env.example             # Environment variable template
|   +-- temp/                    # Temporary PDF storage (auto-cleaned)
|
+-- logo.png                     # Company logo for PDF header
```

---

## \u23f1\ufe0f Attendance Rules (12-Hour Workday)

### Duty Session (First IN\u2192OUT of the day)

| Hours Worked | Status |
|---|---|
| < 4 hrs | Absent (0 pay) |
| 4 \u2013 6.59 hrs | Half Day (0.5 pay) |
| \u2265 7 hrs | Full Day (1.0 pay) |

### OT Session (Second IN\u2192OUT same day)

| Hours Worked | OT Credited |
|---|---|
| < 4 hrs | No OT |
| 4 \u2013 6.59 hrs | Half OT (4 hrs credited) |
| \u2265 7 hrs | Full OT (actual hours credited) |

### Sunday Rule

| Saturday Present | Monday Present | Sunday Pay |
|---|---|---|
| \u2714\ufe0f Yes | \u2714\ufe0f Yes | Full Pay (1.0) |
| \u2714\ufe0f Yes | \u274c No | Half Pay (0.5) |
| \u274c No | \u274c No | No Pay (0) |

---

## \ud83d\udcb0 Salary Formula

```
Final Salary = (Base Salary x Attendance Ratio)
             + OT Pay
             + Bonus
             - Deduction
             - Advance

Attendance Ratio = (Full Days + Half Days x 0.5 + Paid Sundays) / Working Days
OT Pay           = OT Hours x (Base / Working Days / 12) x OT Multiplier (1.5x)
```

---

## \ud83e\udde7 Salary Slip Format

```
====================================
         HYPE PVT LTD
   123 Business Park, Kolkata
   Email: hr@hype.com | Ph: XXXXXXXXXX
====================================
        SALARY SLIP
Employee: Rahul Das         EMP-0001
Month   : April 2026
------------------------------------
Present Days    : 22
Half Days       : 2
Absent Days     : 4
Paid Holidays   : 4 (Sunday rule)
OT Hours        : 18 hrs
------------------------------------
Base Salary     :  15,000
Attendance Sal  :  14,000
Overtime Pay    :   3,000
Bonus           :   1,000
Deduction       :    -500
Advance         :       0
------------------------------------
FINAL SALARY    :  17,500
Payment Mode    : CASH
------------------------------------
           Authorized Signature
====================================
```

---

## \ud83d\ude80 PHP Backend Setup

### Requirements
- PHP >= 7.4 (PHP 8.x recommended)
- Composer
- Firebase project with Firestore, Storage, and Auth enabled
- Hosting with cron job support (any shared/VPS hosting)

### 1. One-Click Install (Web Installer)

```
https://yoursite.com/hype-hr/install.php
```

Fill in Firebase Project ID, API Key, SMTP settings, and optional SMS provider. The installer writes your `.env` file automatically.

> \u26a0\ufe0f **Delete `install.php` immediately after installation!**

### 2. Manual Install

```bash
# 1. Clone and go to php_backend/
cd php_backend/

# 2. Copy .env template and fill in your values
cp .env.example .env
nano .env

# 3. Install PHP dependencies
composer install

# 4. Upload your Firebase service account JSON
# Get it from Firebase Console -> Project Settings -> Service Accounts
# Upload as: php_backend/firebase-service-account.json

# 5. Set file permissions
chmod 755 temp/
chmod 644 .env
chmod 600 firebase-service-account.json
```

### 3. Configure Cron Job

Add to server crontab (`crontab -e`):

```bash
# Runs at 00:05 IST on the 1st of every month
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/php_backend/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
```

### 4. Configure SMTP in Firestore

Create a Firestore document at `settings/smtp`:

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

## \ud83d\udce7 Email + \ud83d\udcf1 SMS Notifications

### Email (PHPMailer + SMTP)
- Auto-sent on the 1st of every month after salary slip generation
- Salary slip attached as PDF
- HTML email with full attendance + salary breakdown
- Only sent if employee has an email address in their profile
- SMTP configured via Firestore `settings/smtp` or `.env` file

### SMS (Optional \u2014 choose one provider)

| Provider | Region | Config Key |
|---|---|---|
| **Fast2SMS** | India (recommended) | `SMS_API_KEY` |
| **MSG91** | India | `SMS_API_KEY` + `SMS_SENDER_ID` |
| **Twilio** | International | `SMS_ACCOUNT_SID` + `SMS_AUTH_TOKEN` |

Set in `.env`:
```bash
SMS_ENABLED=true
SMS_PROVIDER=fast2sms     # or msg91 / twilio
SMS_API_KEY=your_api_key
```

---

## \ud83d\uddc4\ufe0f Firebase Data Structure

```
Firestore
|-- employees/{emp_id}
|   |-- employee_id: "EMP-0001"
|   |-- name: "Rahul Das"
|   |-- username: "rahul.hype"
|   |-- mobile: "9876543210"
|   |-- email: "rahul@email.com"   # optional
|   |-- aadhaar: "XXXX-XXXX-XXXX"
|   |-- salary: 15000
|   |-- payment_mode: "CASH"
|   |-- is_active: true
|   +-- company_id: "hype"
|
|-- attendance_logs/{log_id}
|   |-- employee_id: "EMP-0001"
|   |-- timestamp: Timestamp
|   |-- location: "Gate"
|   +-- action: "IN" | "OUT"
|
|-- sessions/{session_id}
|   |-- employee_id: "EMP-0001"
|   |-- date: "2026-04-06"
|   |-- duty_hours: 7.5
|   |-- ot_hours: 4.0
|   +-- session_type: "duty" | "ot"
|
|-- salary/{emp_id}_{month_key}
|   |-- employee_id: "EMP-0001"
|   |-- month_key: "2026-04"
|   |-- final_salary: 17500
|   |-- slip_url: "https://storage.googleapis.com/..."
|   |-- generated_at: Timestamp
|   +-- expires_at: Timestamp   # 12 months, auto-cleanup
|
|-- settings/smtp             # SMTP config (see above)
|-- settings/company          # Company name, address, logo
+-- settings/app              # OT multiplier, working days/month
```

---

## \ud83d\udd10 Security Features

- Unique username format: `name.company` (e.g. `rahul.hype`)
- Aadhaar validation on employee creation
- Prevent double QR scan (15-min cooldown per employee per location)
- Role-based access in Admin App (HR, CA, Manager, Admin)
- API endpoints protected by `API_SECRET` header
- Service account JSON never exposed to client apps
- Salary slips auto-expire after 12 months (Storage + Firestore)

---

## \ud83d\udcf1 Android App Features

### Employee Mode
- Login: Username + Password \u2192 Set PIN \u2192 Daily PIN login
- Dashboard: Present count, absent count, OT hours, today status
- Attendance history: Date-wise IN/OUT logs
- Salary section: Monthly list + download salary slip (last 12 months)
- Auto salary slip generation trigger on 1st of month

### Security / Supervisor Mode
- Login with security/supervisor credentials
- Scan employee QR code from ID card
- Mark IN / OUT for employees who don't have a smartphone
- Works independently without employee phone

---

## \ud83d\udda5\ufe0f Admin App Features (Python Tkinter)

| Module | Features |
|---|---|
| Dashboard | Live attendance, employees inside count |
| Employees | Add/Edit/Delete, Activate/Deactivate, QR card print |
| Attendance | Date-wise logs, IN/OUT timeline, filters |
| Salary | Generate/edit, bonus/deduction/advance, payment mode |
| QR Generator | Location QRs (Gate/Office/Floor) + Employee ID cards |
| Settings | Company details, SMTP config, OT rate, working days |
| Roles | HR / CA / Manager / Admin with permission control |

---

## \ud83d\udce6 Build

### Admin App (Windows EXE)
```bash
cd admin_app/
pip install -r requirements.txt
pyinstaller --onefile --windowed --name HypeHR main.py
# Use Inno Setup to create installer from dist/HypeHR.exe
```

### Android App (APK)
```bash
cd android_app/
./gradlew assembleRelease
# APK at: app/build/outputs/apk/release/app-release.apk
```

---

## \ud83d\ude80 Future Roadmap

- [ ] Face recognition attendance
- [ ] GPS-based geo-fencing validation
- [ ] Leave management module
- [ ] Multi-branch / multi-company support
- [ ] WhatsApp salary slip delivery
- [ ] Employee self-service portal (web)

---

## \ud83d\udc68\u200d\ud83d\udcbb Developer

**David** | Nexuzy Lab  
\ud83d\udce7 nexuzylab@gmail.com  
\ud83d\udd17 [github.com/david0154](https://github.com/david0154)  
\ud83d\udcf1 Built for Indian SMBs with love from Kolkata \u2764\ufe0f

---

<p align="center">
  <sub>\u00a9 2026 Nexuzy Lab \u2014 Hype HR Management System. MIT License.</sub>
</p>
