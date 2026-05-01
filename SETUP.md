# Hype HR Management System — Complete Setup Guide

> **Version:** 1.1 | **Developed by:** David | Nexuzy Lab  
> **Repo:** https://github.com/david0154/hype-hr-management

---

## Table of Contents

1. [Firebase Setup](#1-firebase-setup)
2. [PHP Backend Setup](#2-php-backend-setup)
3. [Windows Admin App Setup](#3-windows-admin-app-setup)
4. [Android App Setup](#4-android-app-setup)
5. [Bonus & Religion Settings](#5-bonus--religion-settings)
6. [Advance Payment Settings](#6-advance-payment-settings)
7. [Firestore Security Rules](#7-firestore-security-rules)
8. [Firebase Storage Rules](#8-firebase-storage-rules)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Firebase Setup

### 1.1 Create Firebase Project

1. Go to https://console.firebase.google.com
2. Click **Add project** → name it (e.g. `hype-hr`)
3. Disable Google Analytics (optional) → **Create project**

### 1.2 Enable Services

| Service | Path | Settings |
|---|---|---|
| Authentication | Build → Authentication → Sign-in method | Enable **Email/Password** |
| Firestore | Build → Firestore Database | Create in **Production mode**, region `asia-south1` |
| Storage | Build → Storage | Create bucket, region `asia-south1` |

### 1.3 Service Account (Admin App + PHP Backend)

1. Firebase Console → ⚙️ Project Settings → **Service accounts**
2. Click **Generate new private key** → download JSON
3. Rename to `firebase-service-account.json`
4. ⚠️ Never commit this file to Git — add to `.gitignore`

### 1.4 Web API Key

1. Firebase Console → ⚙️ Project Settings → **General**
2. Scroll to **Your apps** → copy **Web API Key**
3. Used as `FIREBASE_API_KEY` in PHP `.env`

---

## 2. PHP Backend Setup

### 2.1 Requirements

- PHP >= 7.4 (PHP 8.x recommended)
- Composer (https://getcomposer.org)
- Hosting with cron support, SSL, `allow_url_fopen = On`
- PHP extensions: `curl`, `json`, `mbstring`, `openssl`

### 2.2 Option A — One-Click Install (Recommended)

1. Upload entire `php_backend/` folder to your hosting
2. Upload `firebase-service-account.json` (ideally outside public web root)
3. Visit: `https://yoursite.com/php_backend/install.php`
4. Fill the form and click **Install**
5. ⚠️ **DELETE `install.php` immediately after!**

### 2.3 Option B — Manual Install

```bash
cd /var/www/html/hype-hr/php_backend/
composer install
cp .env.example .env
nano .env
```

### 2.4 .env Configuration

```dotenv
# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_JSON=/path/to/firebase-service-account.json
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
SMS_PROVIDER=fast2sms       # fast2sms | msg91 | twilio
SMS_API_KEY=your_sms_api_key

# Security
API_SECRET=your-random-32-char-secret
```

### 2.5 File Permissions

```bash
chmod 755 temp/
chmod 600 firebase-service-account.json
chmod 644 .env
chown www-data:www-data -R ./
```

### 2.6 Cron Job Setup

The cron handles:
- **1st of month** — monthly salary slip generation for all employees
- **Daily** — religion-based bonus trigger (checks if today is any employee's bonus date)
- **1st of month** — cleanup expired salary slips (>12 months old)

**Via SSH (crontab):**
```bash
crontab -e
# Add:
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/hype-hr/php_backend/cron_job.php >> /var/log/hype_hr.log 2>&1
5 0 * * * TZ=Asia/Kolkata php /var/www/html/hype-hr/php_backend/cron_job.php >> /var/log/hype_hr.log 2>&1
```

**Via cPanel → Cron Jobs:**
- **Monthly** (1st): Minute `5`, Hour `0`, Day `1`, Month `*`, Weekday `*`
- **Daily**: Minute `5`, Hour `0`, Day `*`, Month `*`, Weekday `*`

### 2.7 Gmail App Password

1. Google Account → Security → Enable **2-Step Verification**
2. Google Account → Security → **App passwords** → name: `HypeHR`
3. Copy 16-char password → paste into `SMTP_PASSWORD`

### 2.8 SMS Providers

| Provider | Best For | Website |
|---|---|---|
| Fast2SMS | India (cheapest) | fast2sms.com |
| MSG91 | India (OTP/bulk) | msg91.com |
| Twilio | International | twilio.com |

---

## 3. Windows Admin App Setup

### 3.1 Requirements

- Windows 10 / 11
- Python 3.10+ → https://python.org/downloads
- Internet connection (first run)

### 3.2 Install

```bash
git clone https://github.com/david0154/hype-hr-management.git
cd hype-hr-management/admin_app
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` includes: `firebase-admin`, `fpdf2`, `qrcode[pil]`, `Pillow`, `requests`, `python-dateutil`

### 3.3 Add Firebase Service Account

1. Copy `firebase-service-account.json` into `admin_app/`
2. Open `admin_app/utils/firebase_config.py` and set:

```python
SERVICE_ACCOUNT_PATH = "firebase-service-account.json"
STORAGE_BUCKET       = "your-project-id.appspot.com"
```

### 3.4 Run

```bash
python main.py
```

**Default Super Admin Login:**

| Field | Value |
|---|---|
| Username | `admin.hype` |
| Password | `Hype@2024#SuperAdmin` |
| Role | Super Admin |

> ⚠️ Change password immediately after first login.

### 3.5 Settings Configuration (First Run)

| Tab | What to Configure |
|---|---|
| **Company Info** | Name, Address, Email, Phone, City, GST |
| **SMTP / Email** | SMTP host, port, credentials, from name |
| **Salary Rules** | Working hours (12), working days (26), OT rate (1.5x), payment mode |
| **Bonus Settings** | Standard or religion-based mode, bonus month/date per religion |
| **Advance Settings** | Fixed advance date, max amount, religion-specific advance dates |

### 3.6 Role Management

Settings → 👥 Admin Users → Add User

| Role | Permissions |
|---|---|
| Super Admin | Everything incl. role management |
| Admin | Everything except role management |
| HR Manager | Employees, Attendance, Salary, Advance, Bonus |
| CA | Attendance, Salary, Advance, Bonus, Salary Raise |
| Manager | Dashboard, Employees (view), Attendance (view) |

**Bonus visibility:**  
- HR / CA / Admin → see bonus amount + calculation details  
- Manager / Employee → see bonus label + amount only, **no formula**

### 3.7 Build Windows EXE

```bash
pip install pyinstaller
pyinstaller build.spec
# Output: dist/HypeHR.exe
```

Distribute the entire `dist/` folder (not just the EXE) with `firebase-service-account.json` alongside.

---

## 4. Android App Setup

### 4.1 Requirements

- Android Studio Hedgehog 2023.1+
- Android SDK 26 (Android 8.0) minimum
- JDK 17+

### 4.2 Add Firebase

1. Firebase Console → Project Settings → **Your apps** → Add Android app
2. Package name: `com.nexuzylab.hypehr`
3. Download `google-services.json`
4. Place in: `android_app/app/google-services.json`

### 4.3 Open & Build

```
Android Studio → File → Open → android_app/
```

Wait for Gradle sync, then:

```bash
# Debug
./gradlew assembleDebug

# Release
./gradlew assembleRelease
```

### 4.4 Employee First Login

1. HR creates employee in Admin App → generates username + password
2. Employee opens app → enters username + password
3. App prompts to **set 4-digit PIN**
4. Future logins: PIN only

### 4.5 Security / Supervisor Mode

1. Open app → tap **Security Mode**
2. Login with supervisor credentials
3. Tap **Scan QR** → scan employee ID card QR
4. Tap **IN** or **OUT**

### 4.6 Auto Salary Generation

- WorkManager triggers on **1st of every month at midnight IST**
- Fetches Firestore data → applies rules → generates slip → saves to Storage
- Employee sees new slip in Salary section automatically
- **Salary slips available for 12 months only**

### 4.7 Bonus on Employee App

- Employee sees: bonus label (e.g. "Diwali Bonus") + amount
- Employee does **NOT** see the calculation formula
- Bonus is included in Final Salary on the slip

---

## 5. Bonus & Religion Settings

### 5.1 Overview

| Mode | Description |
|---|---|
| Standard | All employees share one bonus month + date |
| Religion-based | Each religion has its own bonus month, day, and label |

### 5.2 Configure in Admin App

Settings → **Bonus Settings** tab:

- Select mode: **Standard** or **Religion-based**
- **Standard mode**: set bonus month + day + min eligibility days
- **Religion mode**: set month + day + festival label per religion
  - Example: Hindu → October 1 → "Diwali Bonus"
  - Example: Muslim → April 1 → "Eid Bonus" (update each year)
  - Example: Christian → December 25 → "Christmas Bonus"

### 5.3 Firestore Structure — `settings/bonus`

```json
{
  "mode": "religion",
  "standard_month": "March",
  "standard_day": 1,
  "bonus_min_days": 240,
  "religion_dates": {
    "hindu":     { "month": "October",  "day": 1,  "label": "Diwali Bonus",    "enabled": true },
    "muslim":    { "month": "April",    "day": 1,  "label": "Eid Bonus",       "enabled": true },
    "christian": { "month": "December", "day": 25, "label": "Christmas Bonus", "enabled": true },
    "sikh":      { "month": "November", "day": 1,  "label": "Gurpurab Bonus",  "enabled": true },
    "other":     { "month": "March",    "day": 1,  "label": "Annual Bonus",    "enabled": true }
  }
}
```

> Update `month` and `day` annually (especially Muslim/Islamic festivals).

### 5.4 Bonus Formula

```
Bonus = Base Salary − (Absent Days × Daily Rate)
Daily Rate = Base Salary / Working Days
```

Includes: Base Salary  
Deducts: Absent days only  
Excludes: OT pay, advance, half-day bonus

### 5.5 Bonus Visibility

| Role | Sees Amount | Sees Formula |
|---|---|---|
| Employee (Android) | ✅ Yes | ❌ No |
| Manager | ✅ Yes | ❌ No |
| HR Manager | ✅ Yes | ✅ Yes |
| CA | ✅ Yes | ✅ Yes |
| Admin / Super Admin | ✅ Yes | ✅ Yes |

---

## 6. Advance Payment Settings

### 6.1 Configure in Admin App

Settings → **Advance Settings** tab:

| Setting | Description |
|---|---|
| Fixed Advance Day | Day of month (0 = disabled, HR enters manually) |
| Max Advance Amount | Maximum single advance (Rs.) |
| Allow Multi-Advance | Accumulate before deduction |
| Deduction Timing | next_month / same_month / manual |
| Religion-based Date | Per-religion advance date (e.g. before festival) |

### 6.2 Religion-Based Advance

Each religion can have its own advance payment date (e.g. advance before Eid, Diwali).  
Set day = 0 to disable for that religion.

### 6.3 Firestore Structure — `settings/advance`

```json
{
  "fixed_advance_day": 0,
  "max_advance_amount": 5000,
  "allow_multi_advance": true,
  "deduction_timing": "next_month",
  "religion_dates": {
    "muslim": { "month": "March", "day": 28 },
    "hindu":  { "month": "October", "day": 20 }
  }
}
```

### 6.4 Recording an Advance (Admin App)

1. Salary tab → select employee → click **💵 Advance Payment**
2. Enter amount + note → **Save Advance**
3. Outstanding balance accumulates until salary generation
4. Auto-reset to 0 after salary deduction
5. Manual repayment → **Clear Outstanding**

---

## 7. Firestore Security Rules

Firebase Console → Firestore → **Rules** tab — paste:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function isAuth() {
      return request.auth != null;
    }

    // Employees: all authenticated users read, admin SDK writes
    match /employees/{empId} {
      allow read:  if isAuth();
      allow write: if false;
    }

    // Attendance logs: authenticated read+write (employee scan + security scan)
    match /attendance_logs/{logId} {
      allow read, write: if isAuth();
    }

    // Sessions: computed by app after scan
    match /sessions/{sessionId} {
      allow read, write: if isAuth();
    }

    // Salary: employee reads own slips only
    match /salary/{slipId} {
      allow read: if isAuth() &&
                  slipId.matches(request.auth.token.employee_id + '_.*');
      allow write: if false;
    }

    // Advance logs: read-only for authenticated users
    match /advance_logs/{logId} {
      allow read:  if isAuth();
      allow write: if false;
    }

    // Admin users: admin SDK only
    match /admin_users/{userId} {
      allow read, write: if false;
    }

    // Settings (including bonus + advance config): read-only for authenticated
    match /settings/{doc} {
      allow read:  if isAuth();
      allow write: if false;
    }
  }
}
```

> PHP backend + Python admin app use the Firebase Admin SDK (bypasses all rules above).

---

## 8. Firebase Storage Rules

Firebase Console → Storage → **Rules** tab — paste:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {

    // Salary slips: employee reads own slips only
    match /salary_slips/{empId}/{fileName} {
      allow read:   if request.auth != null
                    && request.auth.token.employee_id == empId;
      allow write:  if false;
      allow delete: if false;
    }

    // Employee photos: any authenticated user reads, owner writes
    match /employee_photos/{empId}/{fileName} {
      allow read:  if request.auth != null;
      allow write: if request.auth != null
                   && request.auth.token.employee_id == empId;
    }

    // QR codes: read-only for authenticated
    match /qr_codes/{fileName} {
      allow read:  if request.auth != null;
      allow write: if false;
    }
  }
}
```

---

## 9. Troubleshooting

### Admin App

| Issue | Fix |
|---|---|
| `firebase_admin` import error | `pip install firebase-admin` |
| `hype_cache.db` permission error | Run as administrator once |
| Salary PDF not generating | `pip install fpdf2` |
| Bonus tab not saving | Check `settings/bonus` Firestore document exists (created on first save) |
| Advance tab not showing religion rows | All religions shown by default — day=0 means disabled |

### PHP Backend

| Issue | Fix |
|---|---|
| Cron not triggering bonus | Ensure **daily** cron is set (not just monthly) |
| Wrong religion gets bonus | Check employee `religion` field matches key in `settings/bonus.religion_dates` (case-insensitive) |
| Bonus amount = 0 | Employee may not meet `bonus_min_days` eligibility in previous year |
| Email not sending | Test: `php webhook.php?secret=xxx&action=test_email` |
| PDF blank | Check `temp/` writable: `chmod 755 temp/` |

### Android App

| Issue | Fix |
|---|---|
| Bonus not showing | Check `bonus_paid` field in Firestore salary record |
| Formula visible to employee | Never — formula hidden by design. Only `bonus_label` + amount shown |
| WorkManager not triggering | Disable battery optimization for Hype HR app |
| Salary slip not loading | Check Storage rules path: `salary_slips/{empId}/` |

---

*© 2026 Nexuzy Lab — Hype HR Management System | MIT License*  
*Developer: David | github.com/david0154*
