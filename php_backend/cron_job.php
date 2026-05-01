<?php
/**
 * Hype HR Management — Monthly Cron Job
 * Schedule this on your hosting:
 *   0 6 1 * * php /path/to/php_backend/cron_job.php
 * (Runs at 06:00 on the 1st of every month)
 *
 * Steps:
 *  1. Fetch all active employees
 *  2. For each employee with pdf_pending=true, generate PDF
 *  3. Upload to Firebase Storage
 *  4. Update salary record with slip_url
 *  5. Send email (if employee has email and SMTP configured)
 *  6. Send SMS (optional, if Twilio configured)
 *  7. Delete salary slips older than 12 months from Storage
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/salary_calculator.php';
require_once __DIR__ . '/salary_generator.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/mailer.php';

// Prevent concurrent runs
if (file_exists(CRON_LOCK_FILE)) {
    $age = time() - filemtime(CRON_LOCK_FILE);
    if ($age < 3600) { echo "[HypeHR] Cron already running.\n"; exit; }
}
file_put_contents(CRON_LOCK_FILE, getmypid());
register_shutdown_function(fn() => @unlink(CRON_LOCK_FILE));

echo "[HypeHR Cron] Starting at " . date('Y-m-d H:i:s') . "\n";

// Determine last month
$cal     = new DateTime('first day of last month');
$month   = $cal->format('F');     // e.g. "April"
$year    = $cal->format('Y');     // e.g. "2026"
$monthKey = $cal->format('Y-m'); // e.g. "2026-04"

// Company info
$company = firebase_get_document('settings/company');
$companyName = $company['name'] ?? 'Hype Pvt Ltd';

// Employees
$employees = firebase_query_collection('employees', 'is_active', true);
echo "[HypeHR Cron] Processing " . count($employees) . " employees for {$month} {$year}\n";

foreach ($employees as $emp) {
    $empId = $emp['employee_id'] ?? '';
    if (!$empId) continue;

    $docId = "{$empId}_{$monthKey}";
    $salaryRecord = firebase_get_document("salary/{$docId}");

    // If no record yet, calculate and create
    if (empty($salaryRecord)) {
        $baseSalary = (float)($emp['salary'] ?? 0);
        $sessions   = firebase_query_collection('sessions', 'employee_id', $empId);
        $sessions   = array_filter($sessions, fn($s) => ($s['month_key'] ?? '') === $monthKey);

        $extras    = firebase_query_collection('salary_extras', 'employee_id', $empId);
        $extra     = current(array_filter($extras, fn($e) => ($e['month_key'] ?? '') === $monthKey)) ?: [];

        $calc = calculate_salary(
            $baseSalary,
            array_values($sessions),
            $monthKey,
            (float)($extra['bonus']     ?? 0),
            (float)($extra['deduction'] ?? 0),
            (float)($extra['advance']   ?? 0),
        );

        $salaryRecord = array_merge($calc, [
            'employee_id'  => $empId,
            'name'         => $emp['name'] ?? '',
            'month'        => $month,
            'year'         => $year,
            'month_key'    => $monthKey,
            'company_name' => $companyName,
            'company_address' => $company['address'] ?? '',
            'payment_mode' => $emp['payment_mode'] ?? 'CASH',
            'slip_url'     => '',
            'pdf_pending'  => true,
        ]);
        firebase_set_document("salary/{$docId}", $salaryRecord);
        echo "[HypeHR Cron] Salary calculated for {$empId}\n";
    }

    // Generate PDF if pending
    if (!empty($salaryRecord['pdf_pending']) || empty($salaryRecord['slip_url'])) {
        $pdfUrl = generate_salary_slip($salaryRecord, $emp, $company);
        if ($pdfUrl) {
            firebase_set_document("salary/{$docId}", [
                'slip_url'    => $pdfUrl,
                'pdf_pending' => false,
                'generated_at' => date('c'),
            ]);
            $salaryRecord['slip_url'] = $pdfUrl;
            echo "[HypeHR Cron] PDF generated for {$empId}: {$pdfUrl}\n";

            // Email
            $email = $emp['email'] ?? '';
            $localPdf = PDF_OUTPUT_DIR . "slip_{$empId}_{$month}_{$year}.pdf";
            if (!empty($email)) {
                $sent = send_salary_slip_email(
                    $email,
                    $emp['name'] ?? 'Employee',
                    "{$month} {$year}",
                    $localPdf,
                    (float)$salaryRecord['final_salary'],
                    $companyName
                );
                echo "[HypeHR Cron] Email to {$email}: " . ($sent ? 'sent' : 'skipped') . "\n";
            }

            // SMS (optional)
            $mobile = $emp['mobile'] ?? '';
            if (!empty($mobile)) {
                $smsSent = send_salary_sms(
                    $mobile,
                    $emp['name'] ?? 'Employee',
                    "{$month} {$year}",
                    (float)$salaryRecord['final_salary']
                );
                echo "[HypeHR Cron] SMS to {$mobile}: " . ($smsSent ? 'sent' : 'skipped/disabled') . "\n";
            }
        } else {
            echo "[HypeHR Cron] PDF generation FAILED for {$empId}\n";
        }
    } else {
        echo "[HypeHR Cron] Skipping {$empId} — slip already generated\n";
    }
}

// Cleanup slips older than 12 months
$cutoff = new DateTime();
$cutoff->modify('-' . SLIP_RETAIN_MONTHS . ' months');
$files = glob(PDF_OUTPUT_DIR . '*.pdf') ?: [];
foreach ($files as $file) {
    $mtime = filemtime($file);
    if ($mtime < $cutoff->getTimestamp()) {
        unlink($file);
        echo "[HypeHR Cron] Deleted old slip: " . basename($file) . "\n";
    }
}

echo "[HypeHR Cron] Completed at " . date('Y-m-d H:i:s') . "\n";
