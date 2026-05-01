<?php
/**
 * Hype HR Management — Webhook / API endpoint
 * Trigger salary generation, health checks, and manual monthly processing.
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/salary_generator.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/mailer.php';
require_once __DIR__ . '/sms_service.php';

header('Content-Type: application/json');

$action = $_GET['action'] ?? $_POST['action'] ?? 'health';

try {
    if ($action === 'health') {
        echo json_encode([
            'success' => true,
            'app' => APP_NAME,
            'status' => 'ok',
            'time' => date('c'),
        ]);
        exit;
    }

    if ($action === 'generate_salary') {
        $employeeId = trim($_GET['employee_id'] ?? $_POST['employee_id'] ?? '');
        $monthKey = trim($_GET['month_key'] ?? $_POST['month_key'] ?? date('Y-m', strtotime('first day of last month')));
        [$year, $month] = array_map('intval', explode('-', $monthKey));

        $fb = new HypeFirebaseAPI();
        $settings = $fb->getSettings();
        $company = $fb->getCompanyDetails();
        $smtpCfg = $fb->getSmtpConfig();
        $sms = new HypeSmsService();
        $employees = $fb->getActiveEmployees();

        $processed = [];
        foreach ($employees as $employee) {
            if ($employeeId && ($employee['employee_id'] ?? '') !== $employeeId) continue;

            $empId = $employee['employee_id'] ?? '';
            if (!$empId) continue;

            $summary = $fb->getAttendanceSummary($empId, $year, $month);
            $summary = array_merge($summary, $fb->getSalaryAdjustments($empId, $monthKey));
            $salaryData = calculateSalary($employee, $summary, $settings);
            $salaryData['month'] = date('F', strtotime($monthKey . '-01'));
            $salaryData['month_num'] = $month;
            $salaryData['year'] = $year;
            $salaryData['payment_mode'] = $employee['payment_mode'] ?? 'CASH';

            $pdfFilename = "salary_{$empId}_{$monthKey}.pdf";
            $pdfPath = PDF_TEMP_DIR . $pdfFilename;
            generateSalarySlipPDF($employee, $salaryData, $company, $pdfPath);
            $storagePath = "salary_slips/$year/$month/$pdfFilename";
            $salaryData['slip_url'] = $fb->uploadPdfToStorage($pdfPath, $storagePath);

            $fb->saveSalaryRecord($empId, $monthKey, array_merge($salaryData, [
                'employee_id' => $empId,
                'month_key' => $monthKey,
                'generated_at' => date('c'),
                'expires_at' => date('c', strtotime('+12 months')),
            ]));

            if (!empty($employee['email']) && !empty($smtpCfg)) {
                sendSalarySlipEmail($smtpCfg, $employee, $salaryData, $company, $pdfPath);
            }
            if ($sms->isEnabled() && !empty($employee['mobile'])) {
                $sms->sendSalaryAlert($employee, $salaryData, $company);
            }
            if (file_exists($pdfPath)) unlink($pdfPath);

            $processed[] = [
                'employee_id' => $empId,
                'name' => $employee['name'] ?? '',
                'month_key' => $monthKey,
                'slip_url' => $salaryData['slip_url'] ?? '',
                'final_salary' => $salaryData['final_salary'] ?? 0,
            ];
        }

        echo json_encode(['success' => true, 'processed' => $processed]);
        exit;
    }

    echo json_encode(['success' => false, 'message' => 'Invalid action']);
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => $e->getMessage()]);
}
