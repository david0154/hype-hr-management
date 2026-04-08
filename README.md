# 🏢 Hype HR Management System

<p align="center">
  <img src="logo.png" alt="Hype HR Management Logo" width="180"/>
</p>

<p align="center">
  <b>QR-based Attendance + HR + Payroll System</b><br/>
  Python Tkinter · Android Kotlin · Firebase · PHP
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

**Hype HR Management** is a complete HR + Attendance + Payroll SaaS system:

| Layer | Technology |
|---|---|
| 🖥️ Windows Admin App | Python 3.x, Tkinter, Firebase Admin SDK |
| 📱 Android App | Kotlin, Firebase SDK, ML Kit QR Scanner |
| ☁️ Cloud Backend | Firebase Auth, Firestore, Storage, Cloud Functions |
| 🐘 Automation Server | PHP 8.x, PHPMailer, FPDF |

---

## 🧱 Architecture

```
Admin Tkinter App (Role-Based Login)
   │
   ▼
Firebase Backend
   ├── Authentication
   ├── Firestore Database
   ├── Cloud Functions
   └── Storage (Salary Slip PDFs — 1yr retention)
          │
          ▼
Android App               PHP Cron (1st of month)
   ├── Employee Mode    ←── Generate salary slip PDF
   └── Security Mode         ├── Upload to Firebase Storage
                              └── Email employee if mail available
```

---

## 📁 Project Structure

```
hype-hr-management/
├── admin_app/                    # Python Tkinter Windows App
│   ├── main.py                   # Entry point + sidebar nav
│   ├── modules/
│   │   ├── auth.py               # Login + role management
│   │   ├── dashboard.py          # Live attendance dashboard
│   │   ├── employees.py          # Employee CRUD
│   │   ├── attendance.py         # Logs + rules engine
│   │   ├── salary.py             # Salary calc + PDF + email
│   │   ├── qr_generator.py       # Location + Employee QR
│   │   ├── settings.py           # Company + SMTP + OT rate
│   │   └── roles.py              # RBAC definitions
│   ├── utils/
│   │   ├── firebase_config.py
│   │   ├── pdf_generator.py      # Salary slip FPDF
│   │   └── validators.py         # Aadhaar/PAN/mobile
│   ├── requirements.txt
│   └── build.spec
│
├── android_app/                  # Kotlin Android App
│   └── app/src/main/java/com/nexuzylab/hypehr/
│       ├── MainActivity.kt
│       ├── auth/LoginActivity.kt
│       ├── auth/PinActivity.kt
│       ├── employee/DashboardActivity.kt
│       ├── employee/AttendanceActivity.kt
│       ├── employee/SalaryActivity.kt
│       ├── security/SecurityScanActivity.kt
│       └── utils/FirebaseHelper.kt
│
├── php_backend/                  # PHP Automation Server
│   ├── config.php
│   ├── salary_generator.php
│   ├── mailer.php
│   ├── cron_job.php
│   └── index.php
│
├── firebase/
│   ├── firestore.rules
│   ├── storage.rules
│   └── functions/index.js
│
├── assets/
│   └── logo.png
│
└── docs/
    ├── SETUP.md
    ├── FIREBASE_SETUP.md
    └── API_DOCS.md
```

---

## 👨‍💼 Employee Management

### Fields
| Field | Required |
|---|---|
| Name | ✅ |
| Mobile | ✅ |
| Address | ✅ |
| Aadhaar | ✅ |
| Salary | ✅ |
| Username (auto: `name.company`) | ✅ |
| Password | ✅ |
| PAN | ❌ Optional |
| Email | ❌ Optional |

**Username Rule:** `rahul` + company `hype` → `rahul.hype`  
**Employee ID:** Auto-incremented → `EMP-0001`, `EMP-0002`...

---

## ⏱️ Attendance Rules

### Duty Session (First IN→OUT)
| Hours | Status |
|---|---|
| < 4 hrs | Absent |
| 4–7 hrs | Half Day |
| ≥ 7 hrs | Full Day |

### OT Session (Second IN→OUT)
| Hours | Status |
|---|---|
| < 4 hrs | No OT |
| 4–7 hrs | Half OT |
| ≥ 7 hrs | Full OT |

### Sunday Rule
| Saturday Present | Monday Present | Sunday Pay |
|---|---|---|
| ✔ | ✔ | Full Pay |
| ✔ | ❌ | Half Pay |
| ❌ | ❌ | No Pay |

---

## 💰 Salary Formula

```
Final Salary = (Base Salary × Attendance Ratio)
             + OT Pay
             + Bonus
             - Deduction
             - Advance
```

---

## 🏢 Admin Roles

| Role | Access |
|---|---|
| Admin | Full — all modules |
| HR | Employees, Attendance, Salary view |
| CA | Salary generation, Reports |
| Manager | Attendance view, Employee view |
| Security | QR Scanner only (Android) |

---

## 🧾 Salary Slip Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          HYPE PVT LTD
    123, Business Park, Kolkata
    support: nexuzylab@gmail.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Employee Name : Rahul Das
Employee ID   : EMP-0001
Month         : April 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Present Days : 22
Half Days          : 2
Absent Days        : 4
Paid Holidays      : 4
Overtime Hours     : 18 hrs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Base Salary        : Rs.15,000
Attendance Salary  : Rs.14,000
Overtime Pay       : Rs.3,000
Bonus              : Rs.1,000
Deduction          : Rs.500
Advance            : Rs.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL SALARY       : Rs.17,500
Payment Mode       : CASH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      Authorized Signature
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🗄️ Firebase Schema

### `employees`
```json
{
  "employee_id": "EMP-0001",
  "name": "Rahul Das",
  "mobile": "9876543210",
  "address": "Kolkata, WB",
  "aadhaar": "XXXX-XXXX-XXXX",
  "pan": "ABCDE1234F",
  "email": "rahul@example.com",
  "username": "rahul.hype",
  "salary": 15000,
  "status": "active",
  "company": "hype"
}
```

### `attendance_logs`
```json
{
  "employee_id": "EMP-0001",
  "timestamp": "2026-04-07T09:00:00",
  "location": "Gate",
  "action": "IN",
  "session": 1
}
```

### `sessions`
```json
{
  "employee_id": "EMP-0001",
  "date": "2026-04-07",
  "duty_hours": 8.0,
  "ot_hours": 4.0,
  "status": "Full Day",
  "ot_status": "Half OT"
}
```

### `salary`
```json
{
  "employee_id": "EMP-0001",
  "month": "April",
  "year": 2026,
  "final_salary": 17500,
  "slip_url": "https://storage.firebase.../slip.pdf",
  "slip_expires_at": "2027-05-01"
}
```

---

## 📦 Build

### Windows EXE
```bash
cd admin_app
pip install -r requirements.txt
pyinstaller --onefile --windowed --icon=../assets/logo.ico main.py
```
Package with **Inno Setup** for installer.

### PHP Cron (1st of every month)
```bash
0 0 1 * * php /var/www/html/hype-hr/php_backend/cron_job.php
```

---

## 🚀 Setup

See [docs/SETUP.md](docs/SETUP.md)

---

## 🔮 Future Features
- Face recognition attendance
- GPS location validation
- Leave management system
- Multi-branch support

---

## 👨‍💻 Developer

**Developed by David**  
GitHub: [github.com/david0154](https://github.com/david0154)  
Company: **Nexuzy Lab**  
Support: [nexuzylab@gmail.com](mailto:nexuzylab@gmail.com)  
Policy: [github.com/david0154](https://github.com/david0154)

---

## 📄 License

MIT License — Copyright © 2026 David / Nexuzy Lab

---

<p align="center">🔧 Managed by <b>Nexuzy Lab</b> &nbsp;|&nbsp; 📧 <a href="mailto:nexuzylab@gmail.com">nexuzylab@gmail.com</a></p>
