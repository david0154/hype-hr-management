# Hype HR Management System

> QR-based Attendance + HR + Payroll System  
> Developed by **David** | **Nexuzy Lab** | nexuzylab@gmail.com

---

## 🧱 Architecture

```
Admin App (Python Tkinter)
   │
   ▼
Firebase Backend
   ├── Authentication
   ├── Firestore Database
   ├── Cloud Functions (Auto Salary + Attendance)
   └── Storage (Salary Slip PDF)
   │
   ▼
Android App (Employee + Security Mode)
   │
   ▼
PHP Backend (Auto salary generation + Email delivery)
```

---

## 🔐 Admin App — Default Super Admin Login

| Field    | Value                    |
|----------|--------------------------|
| Username | `admin.hype`             |
| Password | `Hype@2024#SuperAdmin`   |
| Role     | Super Admin              |

> ⚠️ **Change the password immediately after first login** via Settings → My Account.

---

## 👥 Role-Based Access

| Role        | Dashboard | Employees | Attendance | Salary | Bonus | Salary Raise | QR | ID Card | Settings |
|-------------|-----------|-----------|------------|--------|-------|--------------|-----|---------|----------|
| Super Admin | ✅        | ✅        | ✅         | ✅     | ✅    | ✅           | ✅  | ✅      | ✅       |
| Admin       | ✅        | ✅        | ✅         | ✅     | ✅    | ✅           | ✅  | ✅      | ✅       |
| HR Manager  | ✅        | ✅        | ✅         | ✅     | ✅    | ❌           | ❌  | ✅      | ❌       |
| CA          | ✅        | ❌        | ✅         | ✅     | ✅    | ✅           | ❌  | ❌      | ❌       |
| Manager     | ✅        | ✅        | ✅         | ❌     | ❌    | ❌           | ❌  | ❌      | ❌       |

---

## 💰 Salary Formula

```
Final Salary = (Base × Attendance Ratio) + OT Pay + Annual Bonus − Advance
```

- **No deduction field** (removed by design)
- **Bonus**: Yearly only, paid in **March** salary

### Bonus Eligibility
- Employee must have **≥ 240 working days** in the previous year
- Counted as: Present Days + (Half Days × 0.5) + Paid Holidays
- HR / CA / Admin can set each employee's annual bonus amount in the **Bonus Panel**

### Salary Raise
- **CA** and **Admin** can increase salary per employee from the **Salary Raise panel**
- Change is logged with who made the raise and the date
- Takes effect from next payroll generation

---

## ⏱️ Attendance Rules

### Duty Session (First IN → OUT)

| Hours  | Status   |
|--------|----------|
| < 4    | Absent   |
| 4–7    | Half Day |
| ≥ 7    | Full Day |

### OT Session (Second IN → OUT)

| Hours  | OT Status |
|--------|----------|
| < 4    | No OT    |
| 4–7    | Half OT  |
| ≥ 7    | Full OT  |

**OT Pay = OT Day Units × Daily Rate × 1.5x**  
(Flat day-rate, not hourly. 1 Full OT = 1.0 day, 1 Half OT = 0.5 day)

**Working hours per day = 12 hrs**

---

## 📅 Sunday Rule

| Saturday Present | Monday Present | Sunday Pay     |
|-----------------|----------------|----------------|
| ✅              | ✅             | Full Pay (1.0) |
| ✅              | ❌             | Half Pay (0.5) |
| ❌              | any            | No Pay (0)     |

> **Only Saturday attendance triggers Sunday bonus. Monday alone does NOT.**

---

## 🪪 Employee ID Card

Generate printable PNG ID cards with:
- Company name + address header
- Employee photo (from Firebase Storage)
- Name, Employee ID, Designation, Department, Mobile
- QR code encoding Employee ID (for Security scan)
- Scannable by Security Mode in Android app

---

## 📄 Salary Slip Format

```
============================================================
               HYPE PVT LTD
        123 Business Park, Kolkata, West Bengal
        Email: hr@hype.com  |  Ph: +91 XXXXXXXXXX
============================================================
                    SALARY SLIP
Employee : Rahul Das                ID: EMP-0001
Month    : March 2026
------------------------------------------------------------
Present Days    : 22
Half Days       :  2
Absent Days     :  4
Paid Holidays   :  4
------------------------------------------------------------
Overtime        : 2 Full OT Days + 1 Half OT Day
------------------------------------------------------------
Base Salary     :  Rs. 15,000
Attendance Sal  :  Rs. 14,000
Overtime Pay    :  Rs.  1,730
Annual Bonus    :  Rs.  5,000   ← March only, if eligible
Advance Deduct  :  Rs.      0
------------------------------------------------------------
FINAL SALARY    :  Rs. 20,730
Payment Mode    : CASH
------------------------------------------------------------
                   Authorized Signature
============================================================
```

---

## 📱 Android App

- Employee login with PIN
- QR scan for attendance (IN/OUT)
- Auto salary slip generation on 1st of every month (IST)
- Download last 12 months salary slips
- Security/Supervisor mode — scan employee ID card QR to mark attendance

---

## ☁️ PHP Backend

- Auto-runs on 1st of month via cron
- Generates salary slips, uploads to Firebase Storage
- Emails PDF to employees with email on record
- Optional SMS via Twilio / Fast2SMS / MSG91
- One-click install wizard at `/php_backend/install.php`

### Cron setup
```bash
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/php_backend/cron_job.php
```

---

## 🛠️ Tech Stack

| Layer   | Technology |
|---------|------------|
| Desktop | Python 3.11 + Tkinter + Firebase Admin SDK |
| Android | Kotlin + Firebase SDK + ML Kit QR + WorkManager |
| Backend | PHP 8.x + FPDF + PHPMailer + Firebase REST API |
| DB      | Firebase Firestore + Storage |

---

## 🏗️ Build

```bash
# Admin App EXE
pip install -r admin_app/requirements.txt
pyinstaller admin_app/build.spec
```

---

*Developed by David | Nexuzy Lab*
