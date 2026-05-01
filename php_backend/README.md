# Hype HR PHP Backend

This PHP backend already includes salary PDF generation, cron automation, email sending, SMS alerts, Firebase upload, and one-click hosting installer.

## Included

- `cron_job.php` — automatic monthly salary generation on every 1st day.
- `salary_generator.php` — salary slip PDF with company name, address, attendance summary, OT, bonus, deduction, advance, final salary.
- `mailer.php` — sends salary slip PDF to employee email through company SMTP.
- `sms_service.php` — optional Twilio / Fast2SMS / MSG91 support.
- `firebase_api.php` — Firebase Firestore + Storage integration.
- `webhook.php` — manual API trigger for generating salary slips.
- `install.php` — one-click hosting installer.

## Hosting Setup

1. Upload `php_backend` folder to hosting.
2. Open `install.php` in browser.
3. Paste Firebase details and service account JSON.
4. Run:
   `composer install`
5. Add cron:
   `5 0 1 * * php /path/to/php_backend/cron_job.php`

## Android / Windows usage

- Android app or Tkinter app can call:
  - `webhook.php?action=health`
  - `webhook.php?action=generate_salary&month_key=2026-04`
  - `webhook.php?action=generate_salary&employee_id=EMP-0001&month_key=2026-04`

## Important

- Salary slips are stored in Firebase Storage.
- App should show only last 12 months salary records.
- SMTP config should be stored in Firebase settings.
- Management roles such as HR, CA, Manager should be stored in `management_users` collection.
