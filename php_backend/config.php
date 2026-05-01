<?php
/**
 * Hype HR Management — PHP Backend Configuration
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

// ── Firebase ─────────────────────────────────────────────────────────────────
define('FIREBASE_PROJECT_ID',    getenv('FIREBASE_PROJECT_ID')    ?: 'hype-hr-management');
define('FIREBASE_STORAGE_BUCKET',getenv('FIREBASE_STORAGE_BUCKET') ?: 'hype-hr-management.appspot.com');
define('SERVICE_ACCOUNT_PATH',   getenv('FIREBASE_SERVICE_JSON')  ?: __DIR__ . '/firebase-service-account.json');

// ── PDF & Storage ─────────────────────────────────────────────────────────────
define('PDF_TEMP_DIR',         __DIR__ . '/temp/');
define('SLIP_RETENTION_MONTHS', 12);   // Slips older than 12 months auto-deleted

// ── Salary Rules (12-hour working day) ───────────────────────────────────────
define('WORKING_HOURS_PER_DAY',  12);  // Full shift = 12 hrs
define('DUTY_HALF_MIN_HOURS',     4);  // >= 4h and < 7h = Half Day
define('DUTY_FULL_MIN_HOURS',     7);  // >= 7h = Full Day (< 4h = Absent)
define('OT_HALF_MIN_HOURS',       4);  // >= 4h and < 7h = Half OT
define('OT_FULL_MIN_HOURS',       7);  // >= 7h = Full OT  (< 4h = No OT)
define('DEFAULT_OT_MULTIPLIER',  1.5); // OT pay = hours × (base/workdays/12) × 1.5
define('DEFAULT_WORKING_DAYS',   26);  // Standard working days/month

// ── SMTP defaults (overridden at runtime from Firestore settings/smtp) ────────
define('SMTP_DEFAULT_HOST',      getenv('SMTP_HOST')  ?: 'smtp.gmail.com');
define('SMTP_DEFAULT_PORT',      (int)(getenv('SMTP_PORT') ?: 587));
define('SMTP_DEFAULT_USER',      getenv('SMTP_USER')  ?: '');
define('SMTP_DEFAULT_PASS',      getenv('SMTP_PASS')  ?: '');
define('SMTP_DEFAULT_FROM',      getenv('SMTP_FROM')  ?: '');
define('SMTP_DEFAULT_FROM_NAME', getenv('SMTP_FROM_NAME') ?: 'Hype HR Management');

// ── SMS (optional — Twilio) ───────────────────────────────────────────────────
define('SMS_ENABLED',  (bool)(getenv('SMS_ENABLED')  ?: false));
define('SMS_PROVIDER', getenv('SMS_PROVIDER') ?: 'twilio');
define('TWILIO_SID',   getenv('TWILIO_SID')   ?: '');
define('TWILIO_TOKEN', getenv('TWILIO_TOKEN') ?: '');
define('TWILIO_FROM',  getenv('TWILIO_FROM')  ?: '');

// ── Branding ──────────────────────────────────────────────────────────────────
define('DEV_GITHUB',    'github.com/david0154');
define('SUPPORT_MAIL',  'nexuzylab@gmail.com');

// ── Cron lock ─────────────────────────────────────────────────────────────────
define('CRON_LOCK_FILE', sys_get_temp_dir() . '/hype_hr_cron.lock');

// ── Ensure temp dir exists ────────────────────────────────────────────────────
if (!is_dir(PDF_TEMP_DIR)) mkdir(PDF_TEMP_DIR, 0755, true);
