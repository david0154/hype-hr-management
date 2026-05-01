<?php
/**
 * Hype HR Management — PHP Backend Configuration
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

define('FIREBASE_PROJECT_ID',   getenv('FIREBASE_PROJECT_ID')   ?: 'hype-hr-management');
define('FIREBASE_API_KEY',      getenv('FIREBASE_API_KEY')       ?: '');
define('FIREBASE_DB_URL',       getenv('FIREBASE_DB_URL')        ?: 'https://hype-hr-management-default-rtdb.firebaseio.com');
define('FIREBASE_SERVICE_JSON', getenv('FIREBASE_SERVICE_JSON')  ?: __DIR__ . '/firebase-service-account.json');

// Salary PDF settings
define('PDF_OUTPUT_DIR',  __DIR__ . '/salary_slips/');
define('SLIP_RETAIN_MONTHS', 12);   // Auto-delete slips older than 12 months

// SMTP (overridden from Firestore settings/smtp at runtime)
define('SMTP_DEFAULT_HOST',     getenv('SMTP_HOST')  ?: 'smtp.gmail.com');
define('SMTP_DEFAULT_PORT',     getenv('SMTP_PORT')  ?: 587);
define('SMTP_DEFAULT_USER',     getenv('SMTP_USER')  ?: '');
define('SMTP_DEFAULT_PASS',     getenv('SMTP_PASS')  ?: '');
define('SMTP_DEFAULT_FROM',     getenv('SMTP_FROM')  ?: '');
define('SMTP_DEFAULT_FROM_NAME', 'Hype HR Management');

// SMS (optional — Twilio)
define('SMS_ENABLED',          getenv('SMS_ENABLED')  ?: false);
define('TWILIO_SID',           getenv('TWILIO_SID')   ?: '');
define('TWILIO_TOKEN',         getenv('TWILIO_TOKEN') ?: '');
define('TWILIO_FROM',          getenv('TWILIO_FROM')  ?: '');

// Working hours per day (12-hour shift)
define('WORKING_HOURS_PER_DAY', 12);

// Cron lock
define('CRON_LOCK_FILE', sys_get_temp_dir() . '/hype_hr_cron.lock');

if (!is_dir(PDF_OUTPUT_DIR)) mkdir(PDF_OUTPUT_DIR, 0755, true);
