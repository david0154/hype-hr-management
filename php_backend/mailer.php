<?php
/**
 * Hype HR Management — Email Sender (PHPMailer)
 * SMTP settings loaded dynamically from Firestore `settings/smtp`.
 * Fallback to environment variables / config.php constants.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/vendor/autoload.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

/**
 * Build SMTP settings array.
 * Priority: Firestore settings/smtp → .env vars → config.php defaults
 */
function get_smtp_settings(?array $smtpDoc = null): array {
    if ($smtpDoc === null) {
        // Read from Firestore at runtime if not passed
        if (function_exists('firebase_get_document')) {
            $smtpDoc = firebase_get_document('settings/smtp') ?? [];
        } else {
            $smtpDoc = [];
        }
    }
    return [
        'enabled'   => (bool)($smtpDoc['enabled']    ?? false),
        'host'      => $smtpDoc['host']               ?? SMTP_DEFAULT_HOST,
        'port'      => (int)($smtpDoc['port']         ?? SMTP_DEFAULT_PORT),
        'username'  => $smtpDoc['username']           ?? SMTP_DEFAULT_USER,
        'password'  => $smtpDoc['password']           ?? SMTP_DEFAULT_PASS,
        'from'      => $smtpDoc['from_email']         ?? SMTP_DEFAULT_FROM,
        'from_name' => $smtpDoc['from_name']          ?? SMTP_DEFAULT_FROM_NAME,
        'encryption'=> $smtpDoc['encryption']         ?? 'tls',
    ];
}

/**
 * sendSalarySlipEmail()
 * Called from cron_job.php after PDF is generated.
 *
 * @param array  $smtpCfg   Raw Firestore smtp doc (or [])
 * @param array  $employee  Employee document
 * @param array  $salaryData Computed salary breakdown
 * @param array  $company   Company details
 * @param string $pdfPath   Local path to generated PDF
 * @return array ['success'=>bool, 'message'=>string]
 */
function sendSalarySlipEmail(
    array  $smtpCfg,
    array  $employee,
    array  $salaryData,
    array  $company,
    string $pdfPath
): array {
    $toEmail = $employee['email'] ?? '';
    if (empty($toEmail)) return ['success' => false, 'message' => 'No employee email'];

    $smtp = get_smtp_settings($smtpCfg);
    if (!$smtp['enabled'] || empty($smtp['username'])) {
        return ['success' => false, 'message' => 'SMTP not enabled or username missing'];
    }

    $month        = ($salaryData['month'] ?? '') . ' ' . ($salaryData['year'] ?? '');
    $finalSalary  = (float)($salaryData['final_salary'] ?? 0);
    $companyName  = $company['name'] ?? 'Hype HR';
    $empName      = $employee['name'] ?? 'Employee';

    $mail = new PHPMailer(true);
    try {
        $mail->isSMTP();
        $mail->Host       = $smtp['host'];
        $mail->SMTPAuth   = true;
        $mail->Username   = $smtp['username'];
        $mail->Password   = $smtp['password'];
        $mail->SMTPSecure = strtolower($smtp['encryption']) === 'ssl'
            ? PHPMailer::ENCRYPTION_SMTPS
            : PHPMailer::ENCRYPTION_STARTTLS;
        $mail->Port       = $smtp['port'];
        $mail->CharSet    = 'UTF-8';

        $mail->setFrom($smtp['from'] ?: $smtp['username'], $smtp['from_name']);
        $mail->addAddress($toEmail, $empName);

        $mail->isHTML(true);
        $mail->Subject = "Your Salary Slip for {$month} — {$companyName}";
        $mail->Body    = buildEmailHtml($empName, $month, $finalSalary, $companyName, $salaryData);
        $mail->AltBody = "Dear {$empName}, Your salary slip for {$month} is attached. "
                       . "Net Pay: Rs. " . number_format($finalSalary, 2) . ".";

        if (file_exists($pdfPath)) {
            $mail->addAttachment($pdfPath, "SalarySlip_{$month}.pdf");
        }

        $mail->send();
        error_log("[HypeHR] Email sent to {$toEmail} for {$month}");
        return ['success' => true, 'message' => 'Sent'];

    } catch (Exception $e) {
        error_log("[HypeHR] Email error to {$toEmail}: {$e->getMessage()}");
        return ['success' => false, 'message' => $e->getMessage()];
    }
}

function buildEmailHtml(
    string $name,
    string $month,
    float  $salary,
    string $company,
    array  $data
): string {
    $amt      = 'Rs. ' . number_format($salary, 2);
    $present  = (int)($data['total_present'] ?? 0);
    $half     = (int)($data['half_days']     ?? 0);
    $absent   = (int)($data['absent_days']   ?? 0);
    $otHours  = number_format((float)($data['ot_hours'] ?? 0), 1);
    $attSal   = 'Rs. ' . number_format((float)($data['attendance_salary'] ?? 0), 2);
    $otPay    = 'Rs. ' . number_format((float)($data['ot_pay']            ?? 0), 2);
    $mode     = htmlspecialchars($data['payment_mode'] ?? 'CASH');
    return <<<HTML
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
<table width="600" align="center" cellpadding="0" cellspacing="0" style="background:#fff;margin:20px auto;border-radius:8px;overflow:hidden;">
  <tr><td style="background:#01696f;padding:24px;text-align:center;">
    <h1 style="color:#fff;margin:0;font-size:22px;">{$company}</h1>
    <p style="color:#b2dfdb;margin:6px 0 0;font-size:14px;">Salary Slip — {$month}</p>
  </td></tr>
  <tr><td style="padding:24px;">
    <p style="font-size:16px;">Dear <strong>{$name}</strong>,</p>
    <p>Your salary slip for <strong>{$month}</strong> has been generated and is attached to this email.</p>
    <table width="100%" cellpadding="8" cellspacing="0" style="border-collapse:collapse;margin:16px 0;">
      <tr style="background:#f0f7f7;"><td style="border:1px solid #ddd;"><strong>Present Days</strong></td><td style="border:1px solid #ddd;">{$present} days</td></tr>
      <tr><td style="border:1px solid #ddd;"><strong>Half Days</strong></td><td style="border:1px solid #ddd;">{$half} days</td></tr>
      <tr style="background:#f0f7f7;"><td style="border:1px solid #ddd;"><strong>Absent Days</strong></td><td style="border:1px solid #ddd;">{$absent} days</td></tr>
      <tr><td style="border:1px solid #ddd;"><strong>OT Hours</strong></td><td style="border:1px solid #ddd;">{$otHours} hrs</td></tr>
      <tr style="background:#f0f7f7;"><td style="border:1px solid #ddd;"><strong>Attendance Salary</strong></td><td style="border:1px solid #ddd;">{$attSal}</td></tr>
      <tr><td style="border:1px solid #ddd;"><strong>Overtime Pay</strong></td><td style="border:1px solid #ddd;">{$otPay}</td></tr>
      <tr style="background:#01696f;"><td style="border:1px solid #01696f;color:#fff;"><strong>Net Salary</strong></td><td style="border:1px solid #01696f;color:#fff;"><strong>{$amt}</strong></td></tr>
    </table>
    <p>Payment Mode: <strong>{$mode}</strong></p>
    <p style="color:#888;font-size:12px;margin-top:24px;">Please find the full salary slip as a PDF attachment.<br>This is an automated email from Hype HR Management System.</p>
  </td></tr>
  <tr><td style="background:#f0f0f0;padding:12px;text-align:center;font-size:11px;color:#888;">
    Developed by David | Nexuzy Lab | nexuzylab@gmail.com
  </td></tr>
</table>
</body></html>
HTML;
}
