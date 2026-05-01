<?php
/**
 * Hype HR Management — PHP Backend Configuration
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 *
 * Load from .env automatically, or set environment variables on your server.
 */

// ── Auto-load .env if php-dotenv not available ────────────────────────────────
$envFile = __DIR__ . '/.env';
if (file_exists($envFile)) {
    foreach (file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        if (strpos(trim($line), '#') === 0) continue;
        if (strpos($line, '=') === false) continue;
        [$key, $val] = explode('=', $line, 2);
        $key = trim($key); $val = trim($val, " \t\n\r\0\x0B\"'");
        if (!empty($key) && getenv($key) === false) putenv("$key=$val");
    }
}

// ── Firebase ──────────────────────────────────────────────────────────────────
define('FIREBASE_PROJECT_ID',      getenv('FIREBASE_PROJECT_ID')      ?: 'hype-hr-default');
define('FIREBASE_API_KEY',         getenv('FIREBASE_API_KEY')         ?: '');
define('FIREBASE_STORAGE_BUCKET',  getenv('FIREBASE_STORAGE_BUCKET')  ?: 'hype-hr-default.appspot.com');
define('SERVICE_ACCOUNT_PATH',     __DIR__ . '/serviceAccountKey.json');

// ── Paths ─────────────────────────────────────────────────────────────────────
define('PDF_TEMP_DIR',    __DIR__ . '/temp/');
define('ASSETS_DIR',      __DIR__ . '/../assets/');

// ── Salary slip retention (months) ───────────────────────────────────────────
define('SLIP_RETENTION_MONTHS', 12);

// ── App meta ──────────────────────────────────────────────────────────────────
define('APP_NAME',    'Hype HR Management');
define('SUPPORT_MAIL','nexuzylab@gmail.com');
define('DEV_NAME',    'David');
define('DEV_GITHUB',  'https://github.com/david0154');

// ── SMS Provider (optional) ───────────────────────────────────────────────────
// Supported: 'twilio' | 'fast2sms' | 'msg91' | '' (disabled)
define('SMS_PROVIDER',   getenv('SMS_PROVIDER')   ?: '');
define('SMS_API_KEY',    getenv('SMS_API_KEY')    ?: '');
define('SMS_AUTH_TOKEN', getenv('SMS_AUTH_TOKEN') ?: '');     // Twilio only
define('SMS_ACCOUNT_SID',getenv('SMS_ACCOUNT_SID')?: '');    // Twilio only
define('SMS_FROM_NUMBER',getenv('SMS_FROM_NUMBER')?: '');     // Twilio only
define('SMS_SENDER_ID',  getenv('SMS_SENDER_ID')  ?: 'HYPEHR'); // Fast2SMS / MSG91

// ── Ensure temp dir ───────────────────────────────────────────────────────────
if (!is_dir(PDF_TEMP_DIR)) mkdir(PDF_TEMP_DIR, 0755, true);
