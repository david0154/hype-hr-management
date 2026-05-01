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
|   |   |-- salary.py            # Salary calc + Advance Payment panel + Bonus
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
|   |-- salary_calculator.php    # Bonus = 1 month - absent cuts only
|   |-- salary_generator.php     # PDF builder (bonus line hidden if not March)
|   |-- mailer.php
|   |-- sms_service.php
|   |-- cron_job.php
|   |-- webhook.php
|   |-- install.php
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

### ⚠️ Sunday Rule

| Saturday Present | Monday Present | Sunday Pay |
|---|---|---|
| ✔️ Yes | ✔️ Yes | Full Pay (1.0 day) |
| ✔️ Yes | ❌ No | Half Pay (0.5 day) |
| ❌ No | any | No Pay |

---

## 💰 Salary Formula

```
Final Salary = Attendance Salary + OT Pay + Annual Bonus (March only) - Advance

Attendance Ratio   = (Full Days + Half Days x 0.5 + Paid Sundays) / Working Days
Attendance Salary  = Base Salary x Attendance Ratio
OT Pay             = OT Day Units x (Base Salary / Working Days) x OT Multiplier (1.5x)
```

---

## 🎁 Annual Bonus Rule

> Bonus is paid **once per year** in the **March salary slip only**.

### Bonus Formula

```
Bonus = Base Salary - (Absent Days x Daily Rate)
      = 1 full month salary  WITH ONLY absent-day cuts applied

Daily Rate = Base Salary / Working Days
```

### What is included / excluded in bonus:

| Component | In Bonus Calc? | Reason |
|---|---|---|
| Base Salary | ✅ Yes (starting point) | Full month as base |
| Absent day cuts | ✅ Yes (deducted) | Fair — absent days are not paid |
| Half-day credit | ❌ Not included | Bonus is flat 1-month less absents |
| OT Pay | ❌ Not included | OT is separate |
| Advance deduction | ❌ Not included | Advance deducted from regular salary |
| Deductions | ❌ Not included | Bonus is gross |

### Eligibility

| Condition | Result |
|---|---|
| Month = March **AND** previous year ≥ 240 working days | Bonus added to March slip |
| Any other month | **Bonus = Rs. 0, line hidden from slip** |
| March but < 240 days previous year | Not eligible, line hidden |

### Advance Payment

- HR / Admin can enter advance given to an employee **anytime** via Salary → 💵 Advance Payment
- New advance is **added** to any existing outstanding balance
- Full outstanding advance is **deducted from next salary**
- After salary generation, outstanding advance is **automatically reset to 0**
- HR can also mark advance as **fully repaid** without generating salary
- All advance transactions are logged to `advance_logs` in Firestore

---

## 🮾 Salary Slip Format

### Regular Month (any month except March)

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
OT              : 2 Full + 1 Half (2.5 units)
------------------------------------------------------------
Base Salary     :  Rs. 15,000.00
Attendance Sal  :  Rs. 14,000.00
Overtime Pay    :  Rs.  2,163.00
------------------------------------------------------------
Advance Deduct  :  Rs.      0.00
------------------------------------------------------------
FINAL SALARY    :  Rs. 16,163.00
Payment Mode    : CASH
------------------------------------------------------------
                   Authorized Signature
============================================================
```

### March Slip (when bonus eligible)

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
OT              : 1 Full (1.0 unit)
------------------------------------------------------------
Base Salary     :  Rs. 15,000.00
Attendance Sal  :  Rs. 14,423.00
Overtime Pay    :  Rs.    865.00
Annual Bonus    :  Rs. 14,154.00  (1 month salary - absent cuts | eligible 2025)
------------------------------------------------------------
Advance Deduct  :  Rs.      0.00
------------------------------------------------------------
FINAL SALARY    :  Rs. 29,442.00
Payment Mode    : CASH
------------------------------------------------------------
                   Authorized Signature
============================================================
```

> **Bonus example:** Base = Rs. 15,000 | Absent = 2 days | Daily rate = Rs. 577  
> Bonus = 15,000 - (2 x 577) = **Rs. 13,846**

---

## 🔐 Admin App — Default Super Admin Login

| Field | Value |
|---|---|
| **Username** | `admin.hype` |
| **Password** | `Hype@2024#SuperAdmin` |
| **Role** | Super Admin |

> ⚠️ Change the password immediately after first login.

---

## 👥 Role-Based Access

| Role | Dashboard | Employees | Attendance | Salary | Advance | Bonus | Salary Raise | QR | ID Card | Settings |
|---|---|---|---|---|---|---|---|---|---|---|
| Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HR Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| CA | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manager | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 🛠️ Setup Guides

---

### 🖥️ Windows Admin App Setup

#### Requirements
- Windows 10 / 11 | Python 3.10+

```bash
git clone https://github.com/david0154/hype-hr-management.git
cd hype-hr-management/admin_app
pip install -r requirements.txt
```

Add `firebase-service-account.json` to `admin_app/` then:
```bash
python main.py
```
Login: `admin.hype` / `Hype@2024#SuperAdmin`

Build EXE:
```bash
pyinstaller build.spec
```

---

### 📱 Android App Setup

1. Add Firebase Android app (package: `com.nexuzylab.hypehr`)
2. Download `google-services.json` → place in `android_app/app/`
3. Open `android_app/` in Android Studio → sync Gradle
4. Enable Auth, Firestore, Storage in Firebase Console
5. Build: `./gradlew assembleRelease`

---

### 🐘 PHP Backend Setup

**One-click:** Upload `php_backend/` → visit `install.php` → fill form → delete `install.php`

**Manual:**
```bash
composer install
cp .env.example .env && nano .env
chmod 755 temp/ && chmod 600 firebase-service-account.json
```

Cron job:
```bash
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/hype-hr/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
```

---

## 🗄️ Firebase Structure

```
Firestore
|-- employees/{emp_id}         salary, advance (outstanding), status
|-- attendance_logs/{log_id}   IN/OUT records
|-- sessions/{session_id}      duty_hours, ot_hours, duty_status, ot_status
|-- salary/{emp_id}_{YYYY_MM}  all salary components + slip_url + expires_at
|-- advance_logs/{log_id}      advance transaction history
|-- admin_users/{username}     role, password_hash
+-- settings/company           name, address, smtp, ot_multiplier
```

---

## ⚡ Performance

| Operation | Without Cache | With SQLite Cache |
|---|---|---|
| Load employee list | ~1–3 sec | < 5ms |
| Load salary records | ~1–2 sec | < 5ms |
| Write | ~300–800ms | ~300ms (write-through) |
| Background sync | — | Every 2 min |

---

## 🚀 Roadmap

- [ ] Face recognition | GPS geo-fencing | Leave management
- [ ] Multi-branch | WhatsApp delivery | Employee web portal
- [ ] Migrate usernames (bulk domain rename)
- [ ] Android Room DB cache

---

## 👨‍💻 Developer

**David** | Nexuzy Lab  
📧 [nexuzylab@gmail.com](mailto:nexuzylab@gmail.com) | 🔗 [github.com/david0154](https://github.com/david0154)  
📱 Built for Indian SMBs with love from Kolkata ❤️

---

<p align="center">
  <sub>© 2026 Nexuzy Lab — Hype HR Management System. MIT License.</sub>
</p>
