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
|-- admin_app/                   # Python Tkinter Windows App
|   |-- main.py                  # Entry point + tab router
|   |-- modules/
|   |   |-- auth.py              # Login + role management + super admin seed
|   |   |-- dashboard.py         # Live attendance dashboard
|   |   |-- employees.py         # Employee CRUD + QR
|   |   |-- attendance.py        # Logs + duty/OT/Sunday rules
|   |   |-- salary.py            # Salary calc + bonus panel + salary raise
|   |   |-- id_card.py           # Employee ID card generator (PNG)
|   |   |-- qr_generator.py      # Location QR codes
|   |   |-- settings.py          # Company + SMTP + OT rate + user mgmt
|   |   +-- roles.py             # RBAC definitions
|   |-- utils/
|   |   |-- firebase_config.py   # Firebase Admin SDK init
|   |   |-- local_cache.py       # SQLite cache engine + background sync
|   |   |-- db.py                # Unified read/write helper (cache + Firebase)
|   |   |-- pdf_generator.py     # Salary slip PDF (FPDF)
|   |   +-- validators.py
|   |-- requirements.txt
|   +-- build.spec               # PyInstaller spec
|
|-- android_app/
|   +-- app/src/main/java/com/nexuzylab/hypehr/
|       |-- ui/auth/             # Login + PIN setup
|       |-- ui/employee/         # Dashboard, attendance, salary
|       |-- ui/security/         # Security/Supervisor scan mode
|       |-- data/firebase/       # Firestore repositories
|       |-- utils/               # SalaryCalculator (canonical), SessionManager
|       |-- util/                # PdfUploader (legacy, kept for upload logic)
|       +-- workers/             # SalarySlipAutoGenerateWorker (WorkManager)
|
|-- php_backend/
|   |-- config.php               # All env + constants
|   |-- firebase_api.php         # Firestore + Storage REST wrapper
|   |-- salary_calculator.php    # Pure salary logic (duty/OT/Sunday rules)
|   |-- salary_generator.php     # FPDF PDF builder
|   |-- mailer.php               # PHPMailer SMTP
|   |-- sms_service.php          # Fast2SMS / MSG91 / Twilio (optional)
|   |-- cron_job.php             # Monthly entry point (runs on 1st)
|   |-- webhook.php              # Manual trigger via HTTP
|   |-- install.php              # One-click installer (DELETE after use!)
|   |-- composer.json
|   |-- .env.example
|   +-- temp/                    # Temp PDF files (auto-cleaned)
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
             + Annual Bonus   ← March only, if ≥ 240 days previous year
             − Advance

Attendance Ratio = (Full Days + Half Days×0.5 + Paid Sundays) ÷ Monthly Working Days

OT Pay = OT Day Units × (Base Salary ÷ Working Days) × OT Multiplier (default 1.5×)
         └─ OT Day Units = 0 / 0.5 / 1.0 per OT session (flat tier, not hourly)
```

**Example:**
- Employee OT session = 9 hrs → counts as **1.0 OT day**
- OT Pay = 1.0 × (₹15,000 ÷ 26) × 1.5 = **₹865.38**

### Bonus Rule
- Paid **once per year** in **March salary only**
- Eligible if employee had **≥ 240 working days** in the previous calendar year
- HR / CA / Admin set the bonus amount per employee in **Salary → 🎁 Pay Bonus** panel

---

## 🯧 Salary Slip Format

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
Overtime Pay    :  Rs.  2,163   (2.5 units × Rs.577 × 1.5x)
Annual Bonus    :  Rs.  5,000   (March only, if eligible)
Advance Deduct  :  Rs.      0
------------------------------------------------------------
FINAL SALARY    :  Rs. 21,163
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
- pip
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

`requirements.txt` includes:
```
firebase-admin
fpdf2
qrcode[pil]
Pillow
requests
```

#### Step 3 — Add Firebase service account
1. Go to [Firebase Console](https://console.firebase.google.com) → Project Settings → Service Accounts
2. Click **Generate new private key** → download JSON
3. Save it as `admin_app/firebase-service-account.json`
4. Open `admin_app/utils/firebase_config.py` and set the path:
```python
SERVICE_ACCOUNT_PATH = "firebase-service-account.json"
STORAGE_BUCKET       = "your-project-id.appspot.com"
```

#### Step 4 — Run the app
```bash
python main.py
```
Login with default super admin:
- **Username:** `admin.hype`
- **Password:** `Hype@2024#SuperAdmin`

> On first run, the super admin is automatically seeded to Firestore.

#### Step 5 — Configure company details
1. Go to **Settings → 🏢 Company**
2. Fill company name, address, email, phone, and **username domain** (e.g. `nexuzy`)
3. Go to **Settings → 📧 Email / SMTP** and add your SMTP credentials
4. Save both

#### Step 6 — Build Windows EXE (optional)
```bash
pip install pyinstaller
pyinstaller build.spec
```
Output EXE will be in `dist/HypeHR.exe`. Copy `firebase-service-account.json` next to the EXE.

---

### 📱 Android App Setup

#### Requirements
- Android Studio Hedgehog or newer
- Android SDK 26+
- Firebase project (same project as admin app)
- `google-services.json`

#### Step 1 — Add Firebase to Android
1. Go to [Firebase Console](https://console.firebase.google.com) → Project Settings → Your Apps
2. Add an Android app with package name `com.nexuzylab.hypehr`
3. Download `google-services.json`
4. Place it in `android_app/app/google-services.json`

#### Step 2 — Open in Android Studio
```
File → Open → select android_app/ folder
```
Let Gradle sync complete.

#### Step 3 — Enable Firebase services
In Firebase Console, enable:
- ✅ Authentication (Email/Password)
- ✅ Firestore Database
- ✅ Storage

#### Step 4 — Configure Firestore rules
In Firestore → Rules:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /employees/{id} {
      allow read: if request.auth != null;
      allow write: if false; // admin app only
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

#### Step 5 — Build and install
```bash
cd android_app/
./gradlew assembleDebug          # for testing
./gradlew assembleRelease        # for production
```
Sign the release APK using Android Studio → Build → Generate Signed APK.

#### Step 6 — First employee login
1. HR creates employee in Admin App (sets username + password)
2. Employee opens app → enters username + password
3. Sets a 4-digit PIN for future quick login
4. Dashboard opens

#### Auto Salary Generation (WorkManager)
The app automatically generates salary slips on the **1st of every month at midnight IST** using WorkManager. No manual action needed. The employee sees the new slip in their **Salary** section.

#### Security / Supervisor Mode
1. Supervisor opens app → taps **Security Mode**
2. Logs in with supervisor credentials
3. Scans employee ID card QR code
4. Taps **IN** or **OUT** to mark attendance

---

### 🐘 PHP Backend Setup

#### Requirements
- PHP ≥ 7.4 (PHP 8.x recommended)
- Composer
- Web hosting with:
  - Cron job support
  - `allow_url_fopen = On` (for Firebase REST API)
  - SSL (recommended)

#### Option A — One-Click Install (Recommended)

1. Upload the entire `php_backend/` folder to your hosting public folder
2. Visit:
```
https://yoursite.com/php_backend/install.php
```
3. Fill in the form:
   - Firebase Project ID
   - Firebase Service Account JSON (paste contents)
   - SMTP details
   - SMS provider (optional)
4. Click **Install**
5. ⚠️ **Delete `install.php` immediately after!**

#### Option B — Manual Install

**Step 1 — Upload files**
```bash
# Via FTP/SFTP or SSH
scp -r php_backend/ user@yourhost:/var/www/html/hype-hr/
```

**Step 2 — Install Composer dependencies**
```bash
cd /var/www/html/hype-hr/
composer install
```

**Step 3 — Configure environment**
```bash
cp .env.example .env
nano .env
```

Fill in your `.env`:
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

**Step 4 — Upload Firebase service account**
1. Firebase Console → Project Settings → Service Accounts → Generate new private key
2. Upload JSON to server (outside public web root is best)
3. Set path in `.env` as `FIREBASE_SERVICE_ACCOUNT_JSON`

**Step 5 — Set permissions**
```bash
chmod 755 temp/
chmod 644 .env
chmod 600 firebase-service-account.json
```

**Step 6 — Set up cron job**

In cPanel → Cron Jobs, or via SSH:
```bash
crontab -e
```
Add:
```bash
# Runs at 00:05 IST on the 1st of every month
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/hype-hr/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
```

**Step 7 — Test manually**
```bash
php /var/www/html/hype-hr/cron_job.php
```
Or via browser (protected by API_SECRET):
```
https://yoursite.com/hype-hr/webhook.php?secret=your-random-32-char-secret
```

#### SMTP Config

For Gmail, use an **App Password** (not your regular password):
1. Google Account → Security → 2-Step Verification (enable)
2. Google Account → Security → App passwords → create one
3. Use that 16-char password in SMTP config

Or configure directly in Firestore `settings/company`:
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": "587",
  "smtp_user": "your@gmail.com",
  "smtp_pass": "your-app-password",
  "smtp_from_name": "Hype HR"
}
```

#### SMS Setup (Optional)

| Provider | Best For | Website |
|---|---|---|
| **Fast2SMS** | India (cheapest) | fast2sms.com |
| **MSG91** | India (OTP/bulk) | msg91.com |
| **Twilio** | International | twilio.com |

In `.env`:
```dotenv
SMS_ENABLED=true
SMS_PROVIDER=fast2sms       # or msg91 or twilio
SMS_API_KEY=your_api_key
```

---

## 📧 Email + 📱 SMS Flow

```
Cron runs (1st of month, 00:05 IST)
  └── For each active employee:
       1. Fetch attendance from Firestore
       2. Apply duty / OT / Sunday rules
       3. Calculate salary (incl. yearly bonus if March)
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
|   |-- base_salary, attendance_salary, ot_pay, bonus, advance
|   |-- final_salary, payment_mode, slip_url
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

- Unique username format: `name.company` (e.g. `rahul.nexuzy`)
- Aadhaar validation on employee creation
- Admin passwords hashed with SHA-256
- 15-minute QR scan cooldown (prevents double scan)
- RBAC: Super Admin / Admin / HR / CA / Manager
- PHP API endpoints protected by `API_SECRET`
- Salary slips auto-expire after 12 months from Firestore + Storage
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
| 💰 Salary | Generate all, Bonus panel, Salary Raise panel |
| 🔳 QR Generator | Location QR codes for gates/floors |
| 🪪 ID Cards | PNG ID card generator with QR (single or bulk) |
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

The admin app uses a **local SQLite cache** (`hype_cache.db`) to make all reads instant:

| Operation | Without Cache | With Cache |
|---|---|---|
| Load employee list | ~1–3 sec (Firebase) | < 5ms (SQLite) |
| Load salary records | ~1–2 sec | < 5ms |
| Write (save employee) | ~300–800ms | ~300ms (Firebase) + instant cache |
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
