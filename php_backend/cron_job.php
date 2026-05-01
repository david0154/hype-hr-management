<?php
/**
 * Hype HR Management — Monthly Salary Cron Job
 *
 * Schedule (crontab — run 1st of each month at 00:05 IST):
 *   5 0 1 * * php /var/www/html/hype-hr/php_backend/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
 *
 * What it does:
 *  1. Fetch all active employees from Firestore
 *  2. Calculate attendance summary for previous month (attendance_logs + sessions)
 *  3. Apply attendance rules (Duty/OT/Sunday)
 *  4. Calculate salary using full formula
 *  5. Generate branded PDF salary slip (company name + address included)
 *  6. Upload PDF to Firebase Storage (1-year expiry signed URL)
 *  7. Save salary record to Firestore collection
 *  8. Send email with PDF attachment if employee email + SMTP configured
 *  9. Send SMS alert if SMS service configured (optional)
 * 10. Cleanup expired slips older than 1 year from Firebase Storage
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/salary_generator.php';
require_once __DIR__ . '/mailer.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/sms_service.php';

// ── Date context ──────────────────────────────────────────────────────────────────
$now      = new DateTime('now', new DateTimeZone('Asia/Kolkata'));
$prevMonth= clone $now;
$prevMonth->modify('first day of last month');

$targetMonth    = (int)$prevMonth->format('n');
$targetYear     = (int)$prevMonth->format('Y');
$targetMonthStr = $prevMonth->format('F');
$targetKey      = $prevMonth->format('Y-m');

log_cron("=== Hype HR Salary Cron Started: " . $now->format('Y-m-d H:i:s') . " ===");
log_cron("Processing month: $targetMonthStr $targetYear");

// ── Load Firestore data ────────────────────────────────────────────────────────
$fb       = new HypeFirebaseAPI();
$settings = $fb->getSettings();
$company  = $fb->getCompanyDetails();
$smtpCfg  = $fb->getSmtpConfig();
$sms      = new HypeSmsService();

log_cron("Company: " . ($company['name'] ?? 'N/A') . " | SMTP: " . ($smtpCfg ? 'configured' : 'not set'));
log_cron("SMS: " . ($sms->isEnabled() ? SMS_PROVIDER . ' enabled' : 'disabled'));

$employees = $fb->getActiveEmployees();
log_cron("Active employees: " . count($employees));

$successCount = 0;
$failCount    = 0;

foreach ($employees as $employee) {
    $empId   = $employee['employee_id'] ?? null;
    $empName = $employee['name']        ?? 'Unknown';
    if (!$empId) { log_cron("SKIP: Missing employee_id"); continue; }

    log_cron("Processing: $empId — $empName");

    try {
        // ── 1. Check if already generated ─────────────────────────────────────────
        if ($fb->salarySlipExists($empId, $targetKey)) {
            log_cron("  SKIP: Slip already exists for $targetKey");
            continue;
        }

        // ── 2. Get attendance summary ──────────────────────────────────────────
        $summary = $fb->getAttendanceSummary($empId, $targetYear, $targetMonth);

        // ── 3. Get bonuses/deductions/advance ───────────────────────────────────
        $adjustments = $fb->getSalaryAdjustments($empId, $targetKey);
        $summary     = array_merge($summary, $adjustments);

        // ── 4. Calculate salary ──────────────────────────────────────────────────
        $salaryData = calculateSalary($employee, $summary, $settings);
        $salaryData['month']        = $targetMonthStr;
        $salaryData['month_num']    = $targetMonth;
        $salaryData['year']         = $targetYear;
        $salaryData['payment_mode'] = $employee['payment_mode'] ?? 'CASH';

        // ── 5. Generate PDF ─────────────────────────────────────────────────────
        $pdfFilename = "salary_{$empId}_{$targetKey}.pdf";
        $pdfPath     = PDF_TEMP_DIR . $pdfFilename;
        generateSalarySlipPDF($employee, $salaryData, $company, $pdfPath);
        log_cron("  PDF generated: $pdfFilename");

        // ── 6. Upload to Firebase Storage ────────────────────────────────────────
        $storagePath = "salary_slips/$targetYear/$targetMonth/{$pdfFilename}";
        $slipUrl     = $fb->uploadPdfToStorage($pdfPath, $storagePath);
        $salaryData['slip_url'] = $slipUrl;
        log_cron("  Uploaded to Storage: $storagePath");

        // ── 7. Save to Firestore ──────────────────────────────────────────────────
        $fb->saveSalaryRecord($empId, $targetKey, array_merge($salaryData, [
            'employee_id'  => $empId,
            'month_key'    => $targetKey,
            'generated_at' => date('c'),
            'expires_at'   => date('c', strtotime('+' . SLIP_RETENTION_MONTHS . ' months')),
        ]));
        log_cron("  Saved to Firestore");

        // ── 8. Send email ──────────────────────────────────────────────────────────
        if (!empty($employee['email']) && !empty($smtpCfg)) {
            $mailResult = sendSalarySlipEmail($smtpCfg, $employee, $salaryData, $company, $pdfPath);
            log_cron("  Email " . ($mailResult['success'] ? 'sent to' : 'FAILED:') . ' ' .
                ($mailResult['success'] ? $employee['email'] : $mailResult['message']));
        } else {
            log_cron("  Email skipped (no email or SMTP not configured)");
        }

        // ── 9. Send SMS ──────────────────────────────────────────────────────────────
        if ($sms->isEnabled() && !empty($employee['mobile'])) {
            $smsOk = $sms->sendSalaryAlert($employee, $salaryData, $company);
            log_cron("  SMS " . ($smsOk ? 'sent' : 'failed') . " to: " . $employee['mobile']);
        }

        // ── 10. Cleanup local temp PDF ──────────────────────────────────────────────
        if (file_exists($pdfPath)) unlink($pdfPath);

        $successCount++;

    } catch (Throwable $e) {
        log_cron("  ERROR for $empId: " . $e->getMessage());
        $failCount++;
    }
}

// ── Cleanup expired slips from Firebase Storage ──────────────────────────────────
try {
    $deleted = $fb->cleanupExpiredSlips();
    log_cron("Cleaned up expired slips: $deleted files removed");
} catch (Throwable $e) {
    log_cron("Cleanup error: " . $e->getMessage());
}

log_cron("=== DONE. Success: $successCount | Failed: $failCount ===\n");

function log_cron(string $msg): void {
    echo '[' . date('H:i:s') . '] ' . $msg . PHP_EOL;
}
