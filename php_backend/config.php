<?php
/**
 * Hype HR Management — PHP Backend Configuration
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

define('FIREBASE_PROJECT_ID', getenv('FIREBASE_PROJECT_ID') ?: 'hype-hr-default');
define('FIREBASE_API_KEY',    getenv('FIREBASE_API_KEY')    ?: 'YOUR_FIREBASE_API_KEY');
define('FIREBASE_STORAGE_BUCKET', getenv('FIREBASE_STORAGE_BUCKET') ?: 'hype-hr-default.appspot.com');

// Path to Firebase service account JSON
define('SERVICE_ACCOUNT_PATH', __DIR__ . '/serviceAccountKey.json');

// PDF output temp dir
define('PDF_TEMP_DIR', __DIR__ . '/temp/');

// Salary slips expire after 1 year
define('SLIP_RETENTION_MONTHS', 12);

// App info
define('APP_NAME',    'Hype HR Management');
define('SUPPORT_MAIL','nexuzylab@gmail.com');
define('DEV_NAME',    'David');
define('DEV_GITHUB',  'https://github.com/david0154');

if (!is_dir(PDF_TEMP_DIR)) {
    mkdir(PDF_TEMP_DIR, 0755, true);
}
