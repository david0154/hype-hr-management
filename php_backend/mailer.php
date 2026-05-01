<?php
/**
 * Hype HR Management — Email Sender
 * Uses PHPMailer (composer require phpmailer/phpmailer).
 * SMTP settings loaded dynamically from Firestore settings/smtp.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/vendor/autoload.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

function get_smtp_settings(): array {
    $settings = firebase_get_document('settings/smtp');
    return [
        'host'      => $settings['host']      ?? SMTP_DEFAULT_HOST,
        'port'      => (int)($settings['port'] ?? SMTP_DEFAULT_PORT),
        'username'  => $settings['username']  ?? SMTP_DEFAULT_USER,
        'password'  => $settings['password']  ?? SMTP_DEFAULT_PASS,
        'from'      => $settings['from_email'] ?? SMTP_DEFAULT_FROM,
        'from_name' => $settings['from_name'] ?? SMTP_DEFAULT_FROM_NAME,
        'enabled'   => (bool)($settings['enabled'] ?? false),
    ];
}

/**
 * Send salary slip email to employee.
 * @param string $toEmail     Recipient email
 * @param string $toName      Recipient name
 * @param string $month       e.g. "April 2026"
 * @param string $pdfPath     Local path to PDF
 * @param float  $finalSalary Net salary amount
 * @param string $companyName
 * @return bool
 */
function send_salary_slip_email(
    string $toEmail,
    string $toName,
    string $month,
    string $pdfPath,
    float  $finalSalary,
    string $companyName
): bool {
    $smtp = get_smtp_settings();
    if (!$smtp['enabled'] || empty($smtp['username'])) {
        error_log("[HypeHR] SMTP not configured or disabled. Skipping email to {$toEmail}");
        return false;
    }
    if (empty($toEmail)) return false;

    $mail = new PHPMailer(true);
    try {
        $mail->isSMTP();
        $mail->Host       = $smtp['host'];
        $mail->SMTPAuth   = true;
        $mail->Username   = $smtp['username'];
        $mail->Password   = $smtp['password'];
        $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
        $mail->Port       = $smtp['port'];
        $mail->setFrom($smtp['from'], $smtp['from_name']);
        $mail->addAddress($toEmail, $toName);
        $mail->isHTML(true);
        $mail->Subject = "Your Salary Slip for {$month} — {$companyName}";
        $mail->Body    = email_body_html($toName, $month, $finalSalary, $companyName);
        $mail->AltBody = "Dear {$toName}, Your salary slip for {$month} is attached. Net Pay: Rs. " . number_format($finalSalary, 2);
        if (file_exists($pdfPath)) $mail->addAttachment($pdfPath);
        $mail->send();
        error_log("[HypeHR] Salary slip email sent to {$toEmail} for {$month}");
        return true;
    } catch (Exception $e) {
        error_log("[HypeHR] Email failed to {$toEmail}: {$e->getMessage()}");
        return false;
    }
}

function email_body_html(string $name, string $month, float $salary, string $company): string {
    $amt = 'Rs. ' . number_format($salary, 2);
    return <<<HTML
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
        <div style="background:#01696f;padding:24px;text-align:center;">
            <h1 style="color:#fff;margin:0;">{$company}</h1>
            <p style="color:#e0f4f4;margin:4px 0 0;">Salary Slip — {$month}</p>
        </div>
        <div style="padding:24px;background:#f9f8f5;">
            <p style="font-size:16px;">Dear <strong>{$name}</strong>,</p>
            <p>Your salary slip for <strong>{$month}</strong> has been generated.</p>
            <div style="background:#fff;border-radius:8px;padding:16px;margin:16px 0;border:1px solid #e0e0e0;">
                <p style="margin:0;font-size:18px;color:#01696f;"><strong>Net Salary: {$amt}</strong></p>
            </div>
            <p>Please find your detailed salary slip attached as a PDF.</p>
            <p style="color:#888;font-size:12px;">This is an automated message from Hype HR Management System.</p>
        </div>
    </div>
    HTML;
}

/**
 * Optional SMS via Twilio.
 */
function send_salary_sms(string $mobile, string $name, string $month, float $salary): bool {
    if (!SMS_ENABLED || empty(TWILIO_SID)) return false;
    if (empty($mobile)) return false;

    $url  = "https://api.twilio.com/2010-04-01/Accounts/" . TWILIO_SID . "/Messages.json";
    $body = "Hi {$name}, your salary slip for {$month} is ready. Net Pay: Rs. " . number_format($salary, 2) . ". Download via Hype HR app.";
    $data = ['To' => '+91' . ltrim($mobile, '0+'), 'From' => TWILIO_FROM, 'Body' => $body];

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => http_build_query($data),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_USERPWD        => TWILIO_SID . ':' . TWILIO_TOKEN,
    ]);
    $result = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    error_log("[HypeHR] SMS to {$mobile}: HTTP {$status}");
    return $status === 201;
}
