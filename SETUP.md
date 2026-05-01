# Hype HR Management System — Complete Setup Guide

> **Version:** 1.0 | **Developed by:** David | Nexuzy Lab  
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

In Firebase Console, enable the following:

| Service | Path | Settings |
|---|---|---|
| Authentication | Build → Authentication → Sign-in method | Enable **Email/Password** |
| Firestore Database | Build → Firestore Database | Create in **Production mode**, region: `asia-south1` |
| Storage | Build → Storage | Create bucket, region: `asia-south1` |

### 1.3 Service Account (for Admin App + PHP Backend)

1. Firebase Console → ⚙️ Project Settings → **Service accounts**
2. Click **Generate new private key** → confirm → download JSON
3. Rename to `firebase-service-account.json`
4. Keep this file **private** — never commit to Git

### 1.4 Web API Key

1. Firebase Console → ⚙️ Project Settings → **General**
2. Scroll to **Your apps** → copy `Web API Key`
3. Used in PHP backend `.env` as `FIREBASE_API_KEY`

---

## 2. PHP Backend Setup

### 2.1 Requirements

- PHP >= 7.4 (PHP 8.x recommended)
- Composer (https://getcomposer.org)
- Web hosting with:
  - Cron job support
  - `allow_url_fopen = On`
  - SSL (recommended)
  - PHP `curl`, `json`, `mbstring` extensions enabled

### 2.2 Option A — One-Click Install (Recommended)

1. Upload the entire `php_backend/` folder to your hosting
2. Upload `firebase-service-account.json` to the same folder  
   ⚠️ Ideally place it **outside** the public web root
3. Visit:
   ```
   https://yoursite.com/php_backend/install.php
   ```
4. Fill the form:
   - Firebase Project ID
   - Firebase Service Account JSON path
   - Firebase Storage Bucket (e.g. `your-project.appspot.com`)
   - Firebase Web API Key
   - SMTP host, port, user, password, from name
   - SMS provider (optional)
   - API Secret (random 32-char string)
5. Click **Install**
6. ⚠️ **DELETE `install.php` immediately after!**

### 2.3 Option B — Manual Install

```bash
# SSH into your server
cd /var/www/html/
git clone https://github.com/david0154/hype-hr-management.git
cd hype-hr-management/php_backend/
composer install
cp .env.example .env
nano .env
```

### 2.4 .env Configuration

```dotenv
# ── Firebase ────────────────────────────────────────────────────
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_JSON=/var/www/html/hype-hr/firebase-service-account.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_API_KEY=your-web-api-key

# ── SMTP ────────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your@gmail.com
SMTP_FROM_NAME=Hype HR Management
SMTP_ENCRYPTION=tls

# ── SMS (optional) ──────────────────────────────────────────────
SMS_ENABLED=false
SMS_PROVIDER=fast2sms          # fast2sms | msg91 | twilio
SMS_API_KEY=your_api_key

# ── Security ────────────────────────────────────────────────────
API_SECRET=your-random-32-char-secret-here
```

### 2.5 File Permissions

```bash
chmod 755 temp/
chmod 644 .env
chmod 600 firebase-service-account.json
chown www-data:www-data -R ./
```

### 2.6 Cron Job Setup

The cron runs on the **1st of every month at 00:05 IST** to auto-generate all salary slips.

**Via SSH (crontab):**
```bash
crontab -e
# Add this line:
5 0 1 * * TZ=Asia/Kolkata php /var/www/html/hype-hr/php_backend/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
```

**Via cPanel → Cron Jobs:**
- Minute: `5`
- Hour: `0`
- Day: `1`
- Month: `*`
- Weekday: `*`
- Command: `TZ=Asia/Kolkata php /home/yourusername/public_html/php_backend/cron_job.php`

> ⚠️ The cron also handles **religion-based bonus months** — it reads the bonus schedule from Firestore `settings/bonus` and fires bonus calculation for any employee whose religion's bonus date matches today.

### 2.7 Test Manually

```bash
# Test cron via CLI
php /var/www/html/hype-hr/php_backend/cron_job.php

# Test via browser (protected by API_SECRET)
https://yoursite.com/php_backend/webhook.php?secret=your-api-secret
```

### 2.8 Gmail App Password Setup

1. Google Account → Security → Enable **2-Step Verification**
2. Google Account → Security → **App passwords**
3. Select app: Mail → device: Other → name: `HypeHR`
4. Copy the 16-char password → paste into `SMTP_PASSWORD`

### 2.9 SMS Providers

| Provider | Region | Website |
|---|---|---|
| Fast2SMS | India (cheapest) | fast2sms.com |
| MSG91 | India (OTP/bulk) | msg91.com |
| Twilio | International | twilio.com |

Set `SMS_PROVIDER` and `SMS_API_KEY` in `.env` to activate.

---

## 3. Windows Admin App Setup

### 3.1 Requirements

- Windows 10 / 11
- Python 3.10 or higher → https://python.org/downloads
- pip (bundled with Python)
- Internet connection (first run)

### 3.2 Install Steps

```bash
# 1. Clone the repo
git clone https://github.com/david0154/hype-hr-management.git
cd hype-hr-management/admin_app

# 2. (Recommended) Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

`requirements.txt` includes:
```
firebase-admin
fpdf2
qrcode[pil]
Pillow
requests
python-dateutil
```

### 3.3 Add Firebase Service Account

1. Copy `firebase-service-account.json` into `admin_app/`
2. Open `admin_app/utils/firebase_config.py` and set:

```python
SERVICE_ACCOUNT_PATH = "firebase-service-account.json"
STORAGE_BUCKET       = "your-project-id.appspot.com"
```

### 3.4 Run the App

```bash
python main.py
```

**Default Super Admin Login:**

| Field | Value |
|---|---|
| Username | `admin.hype` |
| Password | `Hype@2024#SuperAdmin` |
| Role | Super Admin |

> ⚠️ Change the password immediately: Settings → My Account → Change Password

### 3.5 First-Time Configuration

After login, configure in **Settings**:

1. **🏢 Company tab:**
   - Company Name, Address, Email, Phone
   - Username Domain (e.g. `nexuzy` → employee usernames: `rahul.nexuzy`)
   - Default Payment Mode
   - Working Days per month (default: 26)
   - OT Multiplier (default: 1.5×)

2. **📧 SMTP tab:**
   - SMTP host, port, username, password, from name
   - Used for sending salary slips by email

3. **🎁 Bonus Settings tab:**
   - Bonus month trigger: **March (default)** or **custom date**
   - Enable **Religion-based bonus** (see Section 5)

4. **💵 Advance Settings tab:**
   - Advance payment schedule (see Section 6)

### 3.6 Build Windows EXE

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist/HypeHR.exe`

Copy these files next to the EXE:
```
HypeHR.exe
firebase-service-account.json
hype_cache.db          ← auto-created on first run
```

Distribute the entire folder (not just the EXE).

### 3.7 Role Management

Add new admin users: **Settings → 👥 Admin Users → Add User**

| Role | Can Do |
|---|---|
| Super Admin | Everything including role management |
| Admin | Everything except role management |
| HR Manager | Employees, Attendance, Salary, Advance, Bonus |
| CA | Attendance, Salary, Advance, Bonus, Salary Raise |
| Manager | Dashboard, Employees (view), Attendance (view) |

> **Bonus slip amounts are visible only to HR, CA, Admin, Super Admin.**  
> Regular employees see the bonus on their slip but **not** the calculation breakdown.

### 3.8 Bonus Visibility

The bonus amount and calculation are **admin-side only**:
- Salary slip sent to employee shows: `Annual Bonus: Rs. XXXXX`
- No formula breakdown shown on employee copy
- Full calculation visible in Admin App → Salary → employee record

---

## 4. Android App Setup

### 4.1 Requirements

- Android Studio Hedgehog 2023.1 or newer
- Android SDK 26 (Android 8.0) minimum
- Same Firebase project as admin app
- JDK 17+

### 4.2 Add Firebase to Android

1. Firebase Console → Project Settings → **Your apps** → Add app → Android
2. Package name: `com.nexuzylab.hypehr`
3. App nickname: `Hype HR`
4. Download `google-services.json`
5. Place in: `android_app/app/google-services.json`

### 4.3 Open Project

```
Android Studio → File → Open → select android_app/ folder
```

Wait for Gradle sync to complete.

### 4.4 Enable Firebase Services

In Firebase Console, verify these are ON:
- ✅ Authentication → Email/Password
- ✅ Firestore Database
- ✅ Storage

### 4.5 Build APK

**Debug (for testing):**
```bash
cd android_app/
./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk
```

**Release (for production):**
```bash
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release-unsigned.apk
```

Sign the release APK:
- Android Studio → Build → Generate Signed Bundle/APK
- Create keystore if you don't have one
- Use `app-release.apk` for distribution

### 4.6 Employee First Login

1. HR creates employee in Admin App → generates username + password
2. Employee opens app → enters username + password
3. App prompts to **set a 4-digit PIN**
4. Future logins: PIN only (instant)

### 4.7 Security / Supervisor Mode

1. Open app → tap **Security Mode** (bottom tab)
2. Login with supervisor credentials (created in Admin App)
3. Tap **Scan QR**
4. Point camera at employee's ID card QR
5. Tap **IN** or **OUT**

> Supervisor must be logged in before scanning. Each scan is synced to Firestore immediately.

### 4.8 Auto Salary Generation

The app uses WorkManager to auto-generate salary slips:
- **Trigger:** 1st of every month, midnight IST
- **Action:** Fetches Firestore data → applies rules → generates slip → saves to Storage
- **Employee view:** New slip appears in Salary section automatically
- No action needed from employee

---

## 5. Bonus & Religion Settings

### 5.1 Overview

The system supports **two bonus modes**:

| Mode | Description |
|---|---|
| Standard | One bonus per year, fixed month (default: March) |
| Religion-based | Each employee gets bonus on their religion's festival date |

### 5.2 Configure in Admin App

Go to **Settings → 🎁 Bonus Settings**:

**Standard Mode:**
- Set bonus month (1–12)
- Set bonus date within that month (1–31)
- Minimum days eligibility (default: 240 days previous year)

**Religion-based Mode (enable toggle):**
- Add religion entries:
  - Religion name (e.g. `Hindu`, `Muslim`, `Christian`, `Sikh`)
  - Bonus date (DD-MM or specific date each year)
  - Example: Hindu → Diwali month (October/November, company sets date)
  - Example: Muslim → Eid month (company sets date annually)

### 5.3 Firestore Structure for Bonus Settings

The settings are stored in Firestore `settings/bonus`:

```json
{
  "mode": "religion",
  "standard_month": 3,
  "standard_date": 1,
  "min_eligibility_days": 240,
  "religion_schedules": {
    "Hindu": {
      "bonus_month": 10,
      "bonus_date": 1,
      "label": "Diwali Bonus"
    },
    "Muslim": {
      "bonus_month": 4,
      "bonus_date": 1,
      "label": "Eid Bonus"
    },
    "Christian": {
      "bonus_month": 12,
      "bonus_date": 25,
      "label": "Christmas Bonus"
    },
    "Sikh": {
      "bonus_month": 11,
      "bonus_date": 1,
      "label": "Gurpurab Bonus"
    }
  }
}
```

> Update `bonus_month` and `bonus_date` every year as festival dates change (especially for Islamic calendar).

### 5.4 Employee Religion Field

In Admin App → Employee profile → **Religion** field:
- Options: Hindu, Muslim, Christian, Sikh, Other, Not specified
- If `Other` or `Not specified` → employee uses standard bonus schedule

### 5.5 Bonus Formula (both modes)

```
Bonus = Base Salary − (Absent Days × Daily Rate)

Daily Rate   = Base Salary / Working Days
Absent Cut   = Absent Days × Daily Rate
Bonus Amount = Base Salary − Absent Cut
```

**What is included / excluded:**

| Component | In Bonus? |
|---|---|
| Base Salary | ✅ Starting point |
| Absent day deduction | ✅ Applied |
| Half-day credit | ❌ Not used |
| OT Pay | ❌ Separate |
| Advance deduction | ❌ Advance deducted from regular salary only |

### 5.6 Bonus Visibility — Who Sees What

| User | Sees Bonus on Slip? | Sees Calculation? |
|---|---|---|
| Employee (Android app) | ✅ Bonus amount | ❌ No formula |
| Manager | ❌ No access | ❌ No access |
| HR Manager | ✅ Amount | ✅ Full breakdown |
| CA | ✅ Amount | ✅ Full breakdown |
| Admin / Super Admin | ✅ Amount | ✅ Full breakdown |

### 5.7 Salary Slip — Bonus Display

**Non-bonus month slip:**
```
Base Salary     :  Rs. 15,000.00
Attendance Sal  :  Rs. 14,000.00
Overtime Pay    :  Rs.  2,163.00
Advance Deduct  :  Rs.      0.00
──────────────────────────────────
FINAL SALARY    :  Rs. 16,163.00
```
*(Bonus line completely hidden)*

**Bonus month slip (employee copy):**
```
Base Salary     :  Rs. 15,000.00
Attendance Sal  :  Rs. 14,000.00
Overtime Pay    :  Rs.    865.00
Festival Bonus  :  Rs. 13,846.00   ← amount shown, no formula
Advance Deduct  :  Rs.      0.00
──────────────────────────────────
FINAL SALARY    :  Rs. 28,711.00
```

**Bonus month slip (admin copy — includes calculation note):**
```
Festival Bonus  :  Rs. 13,846.00   (Base 15000 - Absent 2d × Rs.577 | Diwali Bonus)
```

---

## 6. Advance Payment Settings

### 6.1 Overview

Companies can pay advance on:
- **Any date** — HR enters it manually in the admin app anytime
- **Fixed date** — company sets a recurring advance date in Settings

### 6.2 Configure in Admin App

Go to **Settings → 💵 Advance Settings**:

- **Advance payment date:** day of month (e.g. `15` = 15th of every month)
- **Max advance limit:** maximum single advance amount (e.g. Rs. 5,000)
- **Allow multiple advances:** yes/no (allow accumulation before deduction)

### 6.3 Record an Advance (Admin App)

1. Salary tab → select employee
2. Click **💵 Advance Payment** (or double-click employee row)
3. Enter amount + optional note
4. Click **Save Advance**

The advance is:
- Added to employee's outstanding balance in Firestore
- Logged to `advance_logs` collection with date + note + who recorded it
- Automatically deducted from the next salary generation
- Outstanding balance reset to 0 after deduction

### 6.4 Clear Outstanding Advance

If employee repays cash directly:
1. Open Advance Payment panel
2. Click **Clear Outstanding**
3. Balance set to Rs. 0, transaction logged

### 6.5 Advance Transaction Log

All advances logged to Firestore `advance_logs/{log_id}`:

```json
{
  "employee_id": "EMP-0001",
  "amount": 3000,
  "total_outstanding": 3000,
  "note": "Medical emergency",
  "date": "2026-04-15",
  "recorded_by": "hr.hype"
}
```

---

## 7. Firestore Security Rules

Copy and paste these rules in Firebase Console → Firestore → **Rules** tab:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // ── Helpers ──────────────────────────────────────────────────
    function isAuth() {
      return request.auth != null;
    }

    function isEmployee(empId) {
      return isAuth() && request.auth.uid == empId;
    }

    // ── Employees ─────────────────────────────────────────────────
    // Employees can read their own record
    // Only admin SDK (backend) can write
    match /employees/{empId} {
      allow read:  if isAuth();
      allow write: if false;   // admin SDK only
    }

    // ── Attendance Logs ───────────────────────────────────────────
    // Authenticated users can read + write (employee scan + security scan)
    match /attendance_logs/{logId} {
      allow read, write: if isAuth();
    }

    // ── Sessions ──────────────────────────────────────────────────
    match /sessions/{sessionId} {
      allow read:  if isAuth();
      allow write: if isAuth();   // computed by app after scan
    }

    // ── Salary ────────────────────────────────────────────────────
    // Employees read only their own slips
    // PHP backend writes via admin SDK (bypasses rules)
    match /salary/{slipId} {
      allow read:  if isAuth() &&
                   slipId.matches(request.auth.token.employee_id + '_.*');
      allow write: if false;
    }

    // ── Advance Logs ──────────────────────────────────────────────
    match /advance_logs/{logId} {
      allow read:  if isAuth();
      allow write: if false;   // admin SDK only
    }

    // ── Admin Users ───────────────────────────────────────────────
    match /admin_users/{userId} {
      allow read, write: if false;   // admin SDK only
    }

    // ── Settings ──────────────────────────────────────────────────
    match /settings/{doc} {
      allow read:  if isAuth();
      allow write: if false;   // admin SDK only
    }
  }
}
```

> **Note:** The PHP backend and Python admin app use the Firebase Admin SDK with the service account, which bypasses all Firestore security rules. The rules above apply only to client SDK (Android app).

---

## 8. Firebase Storage Rules

Firebase Console → Storage → **Rules** tab:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {

    // ── Salary Slips ──────────────────────────────────────────────
    // Pattern: salary_slips/{employee_id}/{filename}
    // Employee can only read their own slips
    match /salary_slips/{empId}/{fileName} {
      allow read:  if request.auth != null
                   && request.auth.token.employee_id == empId;
      allow write: if false;   // PHP backend (admin SDK) only
      allow delete: if false;  // auto-cleanup by PHP cron only
    }

    // ── Employee Photos ───────────────────────────────────────────
    match /employee_photos/{empId}/{fileName} {
      allow read:  if request.auth != null;
      allow write: if request.auth != null
                   && request.auth.token.employee_id == empId;
    }

    // ── QR Codes ──────────────────────────────────────────────────
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
| `firebase_admin` import error | Run `pip install firebase-admin` |
| `hype_cache.db` permission error | Run app as administrator once to create the file |
| Salary PDF not generating | Check `fpdf2` installed: `pip install fpdf2` |
| Firebase connection timeout | Check `firebase-service-account.json` path in `firebase_config.py` |
| App crashes on start | Delete `hype_cache.db` and restart (cache rebuild) |

### PHP Backend

| Issue | Fix |
|---|---|
| `composer install` fails | Check PHP version: `php --version` (needs 7.4+) |
| Cron not running | Check cron log: `tail -f /var/log/hype_hr_cron.log` |
| Email not sending | Test SMTP: `php webhook.php?secret=xxx&action=test_email` |
| Firebase REST 401 error | Regenerate service account key, update JSON file |
| PDF not generating | Check `temp/` directory exists and is writable: `chmod 755 temp/` |
| `allow_url_fopen` error | Enable in php.ini: `allow_url_fopen = On` then restart PHP-FPM |

### Android App

| Issue | Fix |
|---|---|
| `google-services.json` not found | Ensure file is in `android_app/app/` (not project root) |
| Gradle sync fails | File → Invalidate Caches → Restart |
| QR scanner not working | Check camera permission in app settings |
| WorkManager not triggering | Check battery optimization — exclude Hype HR app |
| Login fails with valid credentials | Check Firebase Authentication is enabled (Email/Password) |
| Salary slip not loading | Check Storage rules — ensure employee token has `employee_id` claim |

### Firebase

| Issue | Fix |
|---|---|
| Firestore permission denied | Check security rules — ensure `isAuth()` functions correctly |
| Storage 403 on salary slip | Verify Storage rules path matches `salary_slips/{empId}/` |
| Auth token missing `employee_id` | Set custom claims via Admin SDK after employee creation |
| Quota exceeded | Upgrade Firebase plan or optimize read counts |

---

*© 2026 Nexuzy Lab — Hype HR Management System | MIT License*  
*Developer: David | nexuzylab@gmail.com | github.com/david0154*
