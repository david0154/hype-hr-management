<?php
/**
 * Hype HR Management — Monthly Salary Cron Job
 *
 * Crontab (runs 1st of each month at 00:05 IST / UTC+5:30 = 18:35 UTC prev day):
 *   35 18 28-31 * * [ "$(date +\%d -d tomorrow)" = "01" ] && php /path/to/cron_job.php
 * OR simpler:
 *   5 0 1 * * TZ=Asia/Kolkata php /var/www/html/php_backend/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
 *
 * Process:
 *  1. Fetch active employees from Firestore
 *  2. Calculate previous-month attendance (sessions collection)
 *  3. Apply exact Duty/OT/Sunday rules (12-hour workday)
 *  4. Calculate salary: (Base × AttRatio) + OT + Bonus − Deduction − Advance
 *  5. Generate branded PDF (company name + address + logo)
 *  6. Upload PDF to Firebase Storage (1-year signed URL)
 *  7. Save salary record to Firestore
 *  8. Email PDF to employee (if SMTP configured + employee has email)
 *  9. SMS alert (optional Twilio)
 * 10. Cleanup slips older than 12 months
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/salary_generator.php';
require_once __DIR__ . '/mailer.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/sms_service.php';

// ── Cron lock (prevent double-run) ───────────────────────────────────────────
if (file_exists(CRON_LOCK_FILE)) {
    $age = time() - filemtime(CRON_LOCK_FILE);
    if ($age < 3600) { log_cron('SKIP: Cron already running (lock age ' . $age . 's)'); exit; }
    unlink(CRON_LOCK_FILE);
}
file_put_contents(CRON_LOCK_FILE, getmypid());
register_shutdown_function(fn() => file_exists(CRON_LOCK_FILE) && unlink(CRON_LOCK_FILE));

// ── Date context — previous month ─────────────────────────────────────────────
$now       = new DateTime('now', new DateTimeZone('Asia/Kolkata'));
$prev      = clone $now;
$prev->modify('first day of last month');

$targetMonth    = (int)$prev->format('n');
$targetYear     = (int)$prev->format('Y');
$targetMonthStr = $prev->format('F');       // "April"
$targetKey      = $prev->format('Y-m');     // "2026-04"

log_cron('=== Hype HR Salary Cron Started: ' . $now->format('Y-m-d H:i:s') . ' IST ===');
log_cron("Target month: {$targetMonthStr} {$targetYear} ({$targetKey})");

// ── Load Firestore config ─────────────────────────────────────────────────────
$fb      = new HypeFirebaseAPI();
$settings = $fb->getSettings();
$company  = $fb->getCompanyDetails();
$smtpCfg  = $fb->getSmtpConfig();
$sms      = new HypeSmsService();

log_cron('Company: ' . ($company['name'] ?? 'N/A') . ' | ' . ($company['address'] ?? ''));
log_cron('SMTP: ' . (!empty($smtpCfg['enabled']) ? 'configured (' . ($smtpCfg['host'] ?? '') . ')' : 'not set'));
log_cron('SMS : ' . ($sms->isEnabled() ? SMS_PROVIDER . ' enabled' : 'disabled'));

$employees    = $fb->getActiveEmployees();
$successCount = $failCount = 0;
log_cron('Active employees: ' . count($employees));

foreach ($employees as $employee) {
    $empId   = $employee['employee_id'] ?? null;
    $empName = $employee['name']        ?? 'Unknown';
    if (!$empId) { log_cron('SKIP: missing employee_id'); continue; }

    log_cron("── Processing: {$empId} — {$empName}");

    try {
        // 1. Skip if already generated
        if ($fb->salarySlipExists($empId, $targetKey)) {
            log_cron('  SKIP: slip already exists for ' . $targetKey);
            continue;
        }

        // 2. Attendance summary (exact rules)
        $summary = $fb->getAttendanceSummary($empId, $targetYear, $targetMonth);
        log_cron(sprintf(
            '  Att → Present:%.1f  Half:%.1f  Absent:%.1f  PaidHol:%.1f  OT:%.1fh',
            $summary['total_present'], $summary['half_days'],
            $summary['absent_days'],   $summary['paid_holidays'],
            $summary['ot_hours']
        ));

        // 3. Adjustments
        $adj     = $fb->getSalaryAdjustments($empId, $targetKey);
        $summary = array_merge($summary, $adj);

        // 4. Calculate salary
        $salaryData = calculateSalary($employee, $summary, $settings);
        $salaryData['month']        = $targetMonthStr;
        $salaryData['month_num']    = $targetMonth;
        $salaryData['year']         = $targetYear;
        $salaryData['payment_mode'] = $employee['payment_mode'] ?? 'CASH';
        log_cron('  Salary → Rs. ' . number_format($salaryData['final_salary'], 2));

        // 5. Generate PDF
        $pdfFile = "salary_{$empId}_{$targetKey}.pdf";
        $pdfPath = PDF_TEMP_DIR . $pdfFile;
        generateSalarySlipPDF($employee, $salaryData, $company, $pdfPath);
        log_cron('  PDF generated: ' . $pdfFile);

        // 6. Upload to Firebase Storage
        $storagePath = "salary_slips/{$targetYear}/{$targetMonth}/{$pdfFile}";
        $slipUrl     = $fb->uploadPdfToStorage($pdfPath, $storagePath);
        $salaryData['slip_url'] = $slipUrl;
        log_cron('  Uploaded → ' . $storagePath);

        // 7. Save to Firestore
        $expiresAt = date('c', strtotime('+' . SLIP_RETENTION_MONTHS . ' months'));
        $fb->saveSalaryRecord($empId, $targetKey, array_merge($salaryData, [
            'employee_id'  => $empId,
            'month_key'    => $targetKey,
            'generated_at' => date('c'),
            'expires_at'   => $expiresAt,
            'source'       => 'php_cron',
        ]));
        log_cron('  Saved to Firestore (expires: ' . $expiresAt . ')');

        // 8. Email (if employee has email + SMTP configured)
        if (!empty($employee['email']) && !empty($smtpCfg['enabled'])) {
            $sent = send_salary_slip_email(
                $employee['email'],
                $empName,
                $targetMonthStr . ' ' . $targetYear,
                $pdfPath,
                (float)$salaryData['final_salary'],
                $company['name'] ?? 'Hype Pvt Ltd'
            );
            log_cron('  Email ' . ($sent ? 'sent → ' . $employee['email'] : 'FAILED (check SMTP)'));
        } else {
            log_cron('  Email skipped (no email or SMTP not enabled)');
        }

        // 9. SMS (optional)
        if ($sms->isEnabled() && !empty($employee['mobile'])) {
            $smsOk = $sms->sendSalaryAlert($employee, $salaryData, $company);
            log_cron('  SMS ' . ($smsOk ? 'sent → ' : 'FAILED → ') . $employee['mobile']);
        }

        // 10. Cleanup local PDF
        if (file_exists($pdfPath)) unlink($pdfPath);

        $successCount++;

    } catch (Throwable $e) {
        log_cron('  ERROR [' . $empId . ']: ' . $e->getMessage());
        log_cron('  ' . $e->getTraceAsString());
        $failCount++;
    }
}

// ── Cleanup expired slips ────────────────────────────────────────────────────
try {
    $deleted = $fb->cleanupExpiredSlips();
    log_cron("Cleaned {$deleted} expired slip(s) from Storage");
} catch (Throwable $e) {
    log_cron('Cleanup error: ' . $e->getMessage());
}

log_cron('=== DONE — Success: ' . $successCount . ' | Failed: ' . $failCount . " ===\n");

function log_cron(string $msg): void {
    echo '[' . date('H:i:s') . '] ' . $msg . PHP_EOL;
}
