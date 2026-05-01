<?php
/**
 * cron_job.php
 *
 * Run on the 1st of every month (midnight IST) via crontab:
 *   5 0 1 * * TZ=Asia/Kolkata php /path/to/cron_job.php
 *
 * Also run daily for religion-based bonus + advance date triggers.
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

define('HYPE_CRON', true);
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/salary_calculator.php';
require_once __DIR__ . '/salary_generator.php';

date_default_timezone_set('Asia/Kolkata');

$today_day   = (int)date('j');
$today_month = (int)date('n');
$today_year  = (int)date('Y');
$today_date  = date('Y-m-d');

log_cron("=== Hype HR Cron Start: {$today_date} ===");

try {
    $api      = new HypeFirebaseAPI();
    $settings = $api->getAllSettings();
    $employees = $api->getActiveEmployees();

    log_cron('Active employees: ' . count($employees));

    // ── 1. Monthly salary slip (1st of month) ─────────────────────────────────
    if ($today_day === 1) {
        log_cron('--- Monthly Salary Slip Generation ---');
        // Generate for PREVIOUS month
        $slip_month = $today_month === 1 ? 12 : $today_month - 1;
        $slip_year  = $today_month === 1 ? $today_year - 1 : $today_year;
        $results    = ['ok'=>0, 'skip'=>0, 'fail'=>0];

        foreach ($employees as $emp) {
            $res = processEmployeeSalary(
                $emp['employee_id'], $slip_month, $slip_year, $api
            );
            if ($res['success'])                      $results['ok']++;
            elseif ($res['message'] === 'Slip already exists') $results['skip']++;
            else { $results['fail']++; log_cron('FAIL ' . $emp['employee_id'] . ': ' . $res['message']); }
        }
        log_cron("Salary slips → OK:{$results['ok']} SKIP:{$results['skip']} FAIL:{$results['fail']}");
    }

    // ── 2. Religion-based bonus trigger (any day) ─────────────────────────────
    // Process bonus for employees whose religion bonus date = today
    $bonus_cfg = $settings['bonus'] ?? [];
    if (!empty($bonus_cfg)) {
        $bonus_month = $today_month;
        $bonus_day   = $today_day;
        $bonus_count = 0;
        foreach ($employees as $emp) {
            $religion = trim($emp['religion'] ?? 'Other');
            if (isBonusDateToday($religion, $bonus_month, $bonus_day, $bonus_cfg)) {
                // Re-generate / update salary record for current month with bonus
                $res = processEmployeeSalary(
                    $emp['employee_id'], $today_month, $today_year, $api
                );
                if ($res['success']) $bonus_count++;
            }
        }
        if ($bonus_count > 0)
            log_cron("Religion bonus triggered for {$bonus_count} employee(s)");
    }

    // ── 3. Cleanup expired salary slips (>12 months) ─────────────────────────
    if ($today_day === 1) {
        $deleted = $api->cleanupExpiredSlips();
        log_cron("Cleaned up {$deleted} expired slip(s)");
    }

    log_cron('=== Hype HR Cron End ===');

} catch (Throwable $e) {
    log_cron('FATAL: ' . $e->getMessage());
    exit(1);
}


function log_cron(string $msg): void {
    $line = '[' . date('Y-m-d H:i:s') . '] ' . $msg . PHP_EOL;
    echo $line;
    $logFile = __DIR__ . '/temp/cron.log';
    if (is_writable(dirname($logFile))) {
        file_put_contents($logFile, $line, FILE_APPEND);
    }
}
