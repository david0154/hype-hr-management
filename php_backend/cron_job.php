<?php
/**
 * Hype HR Management — Monthly Salary Cron Job
 *
 * Schedule (crontab):
 *   5 0 1 * * php /var/www/hype-hr/php_backend/cron_job.php >> /var/log/hype_hr_cron.log 2>&1
 *
 * Process each 1st of month:
 *  1. Fetch all active employees from Firestore
 *  2. Calculate attendance summary for previous month
 *  3. Apply attendance rules (Duty/OT/Sunday)
 *  4. Calculate salary using formula
 *  5. Generate PDF salary slip (company logo + full format)
 *  6. Upload to Firebase Storage (1-year expiry)
 *  7. Save salary record to Firestore
 *  8. Send email if employee email + SMTP configured
 *  9. Cleanup expired slips (>1 year old)
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/salary_generator.php';
require_once __DIR__ . '/mailer.php';
require_once __DIR__ . '/firebase_api.php';

$now        = new DateTime('now', new DateTimeZone('Asia/Kolkata'));
$target     = (clone $now)->modify('first day of last month');
$tMonth     = (int)$target->format('n');
$tYear      = (int)$target->format('Y');
$monthName  = $target->format('F');
$monthPad   = $target->format('m');

echo "[Hype HR Cron] Salary generation for $monthName $tYear\n";
echo "[Hype HR Cron] Started: " . $now->format('Y-m-d H:i:s') . "\n";
echo str_repeat('-', 55) . "\n";

$settings   = firebaseGet('settings/company') ?? [];
$company    = [
    'name'    => $settings['name']    ?? 'Hype Pvt Ltd',
    'address' => $settings['address'] ?? '',
    'email'   => $settings['email']   ?? SUPPORT_MAIL,
    'phone'   => $settings['phone']   ?? '',
];
$smtpConfig = [
    'host'      => $settings['smtp_host']      ?? '',
    'port'      => $settings['smtp_port']      ?? 587,
    'user'      => $settings['smtp_user']      ?? '',
    'pass'      => $settings['smtp_pass']      ?? '',
    'from_name' => $settings['smtp_from_name'] ?? $company['name'],
];
$smtpEnabled = !empty($smtpConfig['host']) && !empty($smtpConfig['user']) && !empty($smtpConfig['pass']);

echo "[Hype HR Cron] Company : {$company['name']}\n";
echo "[Hype HR Cron] SMTP    : " . ($smtpEnabled ? 'Enabled (' . $smtpConfig['user'] . ')' : 'Disabled') . "\n\n";

$employees = firebaseQuery('employees', [['status', '==', 'active']]);
if (empty($employees)) { echo "No active employees. Exiting.\n"; exit(0); }
echo "[Hype HR Cron] Employees: " . count($employees) . "\n\n";

$ok = $emailsSent = $errors = 0;

foreach ($employees as $emp) {
    $empId   = $emp['employee_id'] ?? 'UNKNOWN';
    $empName = $emp['name']        ?? 'Unknown';
    echo "[Hype HR Cron] Processing: $empId - $empName\n";

    try {
        // Skip if already generated
        $docId   = "{$empId}_{$tYear}_{$monthPad}";
        $existing = firebaseGet("salary/$docId");
        if ($existing && !empty($existing['slip_url'])) {
            echo "   Skip: already generated\n";
            $ok++;
            continue;
        }

        $summary               = getAttendanceSummary($empId, $tYear, $tMonth, $settings);
        $salaryData            = calculateSalary($emp, $summary, $settings);
        $salaryData['month']        = $monthName;
        $salaryData['month_num']    = $tMonth;
        $salaryData['year']         = $tYear;
        $salaryData['employee_id']  = $empId;
        $salaryData['employee_name']= $empName;
        $salaryData['payment_mode'] = $settings['default_payment_mode'] ?? 'CASH';

        // Generate PDF
        $pdfFile = PDF_TEMP_DIR . "{$empId}_{$tYear}_{$monthPad}_slip.pdf";
        generateSalarySlipPDF($emp, $salaryData, $company, $pdfFile);
        echo "   PDF: generated\n";

        // Upload to Firebase Storage
        $storagePath = "salary_slips/{$empId}/{$tYear}_{$monthPad}_slip.pdf";
        $slipUrl     = uploadToFirebaseStorage($pdfFile, $storagePath);
        echo "   Storage: uploaded\n";

        // Save to Firestore
        $expiry                        = date('Y-m-d', mktime(0,0,0,$tMonth,1,$tYear+1));
        $salaryData['slip_url']        = $slipUrl;
        $salaryData['generated_at']    = date('Y-m-d H:i:s');
        $salaryData['slip_expires_at'] = $expiry;
        firebaseSet("salary/$docId", $salaryData);
        echo "   Firestore: saved\n";

        // Email
        if ($smtpEnabled && !empty($emp['email'])) {
            $sent = sendSalarySlipEmail($smtpConfig, $emp, $salaryData, $company, $pdfFile);
            echo '   Email: ' . ($sent ? 'sent to ' . $emp['email'] : 'failed') . "\n";
            if ($sent) $emailsSent++;
        } else {
            echo "   Email: skipped (no email or SMTP not configured)\n";
        }

        // Cleanup temp
        if (file_exists($pdfFile)) unlink($pdfFile);

        $ok++;
        echo "   Done: $empId\n\n";

    } catch (Throwable $e) {
        $errors++;
        echo "   ERROR: " . $e->getMessage() . "\n\n";
        error_log("[HypeHR Cron] $empId: " . $e->getMessage());
    }
}

// Clean expired slips (>1 year)
cleanExpiredSlips();

echo str_repeat('-', 55) . "\n";
echo "[Hype HR Cron] Success : $ok | Emails: $emailsSent | Errors: $errors\n";
echo "[Hype HR Cron] Done at : " . date('Y-m-d H:i:s') . "\n";


// ---- Helpers ----------------------------------------------------------------

function getAttendanceSummary(string $empId, int $year, int $month, array $settings): array {
    $pad   = str_pad($month, 2, '0', STR_PAD_LEFT);
    $start = "{$year}-{$pad}-01";
    $end   = date('Y-m-t', mktime(0,0,0,$month,1,$year));
    $days  = (int)date('t', mktime(0,0,0,$month,1,$year));

    $sessions = firebaseQuery('sessions', [
        ['employee_id', '==', $empId],
        ['date', '>=', $start],
        ['date', '<=', $end],
    ]);

    $fullDays = $halfDays = $absentDays = 0;
    $otHours  = 0.0;

    foreach ($sessions as $s) {
        $st = $s['status'] ?? 'Absent';
        if ($st === 'Full Day')     $fullDays++;
        elseif ($st === 'Half Day') $halfDays++;
        else                        $absentDays++;

        if (($s['ot_status'] ?? 'No OT') !== 'No OT') {
            $otHours += (float)($s['ot_hours'] ?? 0);
        }
    }

    // Sunday rule
    $paidHolidays = 0.0;
    for ($d = 1; $d <= $days; $d++) {
        $dt = new DateTime("{$year}-{$pad}-" . str_pad($d, 2, '0', STR_PAD_LEFT));
        if ($dt->format('N') == 7) {
            $sat = (clone $dt)->modify('-1 day')->format('Y-m-d');
            $mon = (clone $dt)->modify('+1 day')->format('Y-m-d');
            $satOk = isDatePresent($empId, $sat);
            $monOk = isDatePresent($empId, $mon);
            if ($satOk && $monOk)  $paidHolidays += 1;
            elseif ($satOk)        $paidHolidays += 0.5;
        }
    }

    $adj = firebaseGet("salary_adjustments/{$empId}_{$year}_{$pad}") ?? [];

    return [
        'total_present'  => $fullDays,
        'half_days'      => $halfDays,
        'absent_days'    => $absentDays,
        'ot_hours'       => round($otHours, 2),
        'paid_holidays'  => $paidHolidays,
        'bonus'          => (float)($adj['bonus']     ?? 0),
        'deduction'      => (float)($adj['deduction'] ?? 0),
        'advance'        => (float)($adj['advance']   ?? 0),
    ];
}

function isDatePresent(string $empId, string $date): bool {
    $sessions = firebaseQuery('sessions', [
        ['employee_id', '==', $empId],
        ['date', '==', $date],
    ]);
    foreach ($sessions as $s) {
        if (in_array($s['status'] ?? '', ['Full Day', 'Half Day'])) return true;
    }
    return false;
}

function cleanExpiredSlips(): void {
    echo "\n[Hype HR Cron] Cleaning expired slips...\n";
    $today = date('Y-m-d');
    $docs  = firebaseQuery('salary', [['slip_expires_at', '<=', $today]]);
    $n     = 0;
    foreach ($docs as $doc) {
        if (!empty($doc['slip_url'])) deleteFromFirebaseStorage($doc['slip_url']);
        firebaseUpdate("salary/{$doc['employee_id']}_{$doc['year']}_{$doc['month_num']}",
            ['slip_url' => null, 'slip_expired' => true]);
        $n++;
    }
    echo "[Hype HR Cron] Removed $n expired slips\n";
}
