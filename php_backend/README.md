# Hype HR Management — PHP Backend

Automated salary slip generation, PDF creation, Firebase Storage upload, and SMTP email dispatch.

## Features

- Auto-runs on 1st of every month via cron job
- Generates PDF salary slips with company logo + full format
- Uploads to Firebase Storage (1-year retention, auto-cleanup)
- Emails employees if email + SMTP are configured
- Sunday Rule applied automatically
- REST endpoint for manual trigger

## Files

| File | Purpose |
|------|---------|
| `config.php` | App constants, Firebase config |
| `firebase_api.php` | Firestore + Storage REST API (Service Account JWT) |
| `salary_generator.php` | FPDF salary slip PDF + salary formula |
| `mailer.php` | PHPMailer SMTP wrapper + HTML email template |
| `cron_job.php` | Monthly automation script |
| `index.php` | Health check + manual trigger endpoint |
| `composer.json` | PHPMailer + FPDF dependencies |

## Setup

### 1. Install dependencies
```bash
cd php_backend
composer install
```

### 2. Add Firebase service account
Download `serviceAccountKey.json` from Firebase Console → Project Settings → Service Accounts and place it in `php_backend/`.

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your Firebase Project ID, Storage Bucket, etc.
```

### 4. Set cron job
```bash
# Edit crontab: crontab -e
# Run on 1st of every month at 00:05 IST
5 0 1 * * php /var/www/hype-hr/php_backend/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
```

### 5. Manual trigger
```
POST /index.php?action=trigger_salary
Body: secret=your_cron_secret
```

## Salary Formula

```
Final Salary =
  (Base Salary x Attendance Ratio)
  + OT Pay
  + Bonus
  - Deduction
  - Advance

Attendance Ratio = Effective Days / Monthly Working Days
Effective Days   = Full Days + (Half Days x 0.5) + Paid Holidays
OT Pay           = OT Hours x (Daily Rate / 8) x OT Multiplier (default 1.5x)
```

## Attendance Rules

| Hours Worked | Duty Status |
|---|---|
| < 4 hours | Absent |
| 4 - 7 hours | Half Day |
| >= 7 hours | Full Day |

| OT Session Hours | OT Status |
|---|---|
| < 4 hours | No OT |
| 4 - 7 hours | Half OT |
| >= 7 hours | Full OT |

## Sunday Rule

| Saturday | Monday | Sunday Pay |
|----------|--------|-----------|
| Present | Present | Full Pay |
| Present | Absent | Half Pay |
| Absent | Any | No Pay |

## Salary Slip Format

Every slip includes:
- Company name, address, email, phone
- Employee name, ID, designation
- Month/Year, Payment mode
- Full attendance summary
- Full salary breakdown
- Authorized signature line
- Company logo

Slips are available for **1 year** from generation date via Firebase Storage download link.

---

Developed by **David** | Managed by **Nexuzy Lab**  
Support: [nexuzylab@gmail.com](mailto:nexuzylab@gmail.com)  
GitHub: [github.com/david0154](https://github.com/david0154)
