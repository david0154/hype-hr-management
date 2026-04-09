<?php
/**
 * Hype HR Management — Email Mailer (PHPMailer wrapper)
 * Sends salary slip via company SMTP credentials stored in Firebase settings
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/vendor/phpmailer/src/PHPMailer.php';
require_once __DIR__ . '/vendor/phpmailer/src/SMTP.php';
require_once __DIR__ . '/vendor/phpmailer/src/Exception.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

/**
 * Send salary slip email to employee
 *
 * @param array  $smtpConfig  ['host','port','user','pass','from_name']
 * @param array  $employee    ['name','email','employee_id']
 * @param array  $salaryData  ['month','year','final_salary','slip_url','payment_mode']
 * @param array  $company     ['name','address','email']
 * @param string $pdfPath     Local path to PDF attachment (optional)
 * @return bool
 */
function sendSalarySlipEmail(
    array  $smtpConfig,
    array  $employee,
    array  $salaryData,
    array  $company,
    string $pdfPath = ''
): bool {
    if (empty($employee['email'])) {
        return false;
    }

    $mail = new PHPMailer(true);
    try {
        $mail->isSMTP();
        $mail->Host       = $smtpConfig['host']      ?? '';
        $mail->Port       = (int)($smtpConfig['port']  ?? 587);
        $mail->SMTPAuth   = true;
        $mail->Username   = $smtpConfig['user']      ?? '';
        $mail->Password   = $smtpConfig['pass']      ?? '';
        $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
        $mail->CharSet    = 'UTF-8';

        $mail->setFrom(
            $smtpConfig['user'],
            $smtpConfig['from_name'] ?? ($company['name'] ?? APP_NAME)
        );
        $mail->addAddress($employee['email'], $employee['name'] ?? '');
        $mail->addReplyTo(SUPPORT_MAIL, 'Nexuzy Lab Support');

        if ($pdfPath && file_exists($pdfPath)) {
            $filename = 'SalarySlip_' . ($employee['employee_id'] ?? 'EMP') .
                        '_' . ($salaryData['month'] ?? '') .
                        '_' . ($salaryData['year'] ?? '') . '.pdf';
            $mail->addAttachment($pdfPath, $filename);
        }

        $month     = $salaryData['month']        ?? '';
        $year      = $salaryData['year']         ?? '';
        $final     = number_format((float)($salaryData['final_salary'] ?? 0), 2);
        $slipUrl   = $salaryData['slip_url']     ?? '';
        $empName   = $employee['name']           ?? 'Employee';
        $compName  = $company['name']            ?? APP_NAME;
        $compAddr  = $company['address']         ?? '';
        $compEmail = $company['email']           ?? SUPPORT_MAIL;
        $payMode   = $salaryData['payment_mode'] ?? 'CASH';

        $mail->isHTML(true);
        $mail->Subject = "Salary Slip - $month $year | $compName";

        $downloadBtn = $slipUrl
            ? "<p style='text-align:center;margin:20px 0'><a href='$slipUrl' style='display:inline-block;background:#f77f00;color:#fff;padding:13px 28px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:14px'>Download Salary Slip PDF</a></p><p style='font-size:12px;color:#999;text-align:center'>Available for download for <strong>1 year</strong> from generation date.</p>"
            : '';

        $mail->Body = <<<HTML
<!DOCTYPE html><html><head><meta charset='UTF-8'>
<style>
body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0}
.c{max-width:600px;margin:30px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1)}
.h{background:#0d1b2a;padding:28px 30px;text-align:center}
.h h1{color:#f77f00;margin:0;font-size:22px}
.h p{color:#aaa;margin:5px 0 0;font-size:13px}
.b{padding:30px}
.sb{background:#f0faf4;border:2px solid #2e8b57;border-radius:8px;padding:18px 24px;margin:20px 0;text-align:center}
.sb .amt{font-size:32px;font-weight:bold;color:#2e8b57}
.sb .lbl{color:#555;font-size:13px;margin-top:4px}
table{width:100%;border-collapse:collapse;margin:16px 0}
td{padding:9px 14px;border:1px solid #e0e0e0;font-size:13px}
td:first-child{background:#f7f7f7;font-weight:bold;width:50%}
.ft{background:#0d1b2a;padding:16px 30px;text-align:center;color:#666;font-size:11px}
.ft a{color:#f77f00;text-decoration:none}
</style></head><body>
<div class='c'>
<div class='h'><h1>$compName</h1><p>$compAddr</p></div>
<div class='b'>
<h2 style='color:#0d1b2a'>Dear $empName,</h2>
<p>Your salary slip for <strong>$month $year</strong> is ready.</p>
<div class='sb'><div class='amt'>Rs. $final</div><div class='lbl'>Net Salary &mdash; $month $year</div></div>
<table>
<tr><td>Employee</td><td>$empName</td></tr>
<tr><td>Month</td><td>$month $year</td></tr>
<tr><td>Final Salary</td><td><strong>Rs. $final</strong></td></tr>
<tr><td>Payment Mode</td><td>$payMode</td></tr>
</table>
$downloadBtn
<p style='font-size:12px;color:#888'>For queries, contact HR or reply to this email.</p>
</div>
<div class='ft'>
<p>&copy; $year $compName &nbsp;|&nbsp; <a href='mailto:$compEmail'>$compEmail</a></p>
<p>Developed by David &nbsp;|&nbsp; <a href='https://github.com/david0154'>Nexuzy Lab</a> &nbsp;|&nbsp; Support: <a href='mailto:nexuzylab@gmail.com'>nexuzylab@gmail.com</a></p>
</div></div></body></html>
HTML;
        $mail->AltBody = "Dear $empName, your salary of Rs. $final for $month $year. Download: $slipUrl";

        $mail->send();
        return true;
    } catch (Exception $e) {
        error_log('[HypeHR Mailer] Failed: ' . $employee['email'] . ' - ' . $e->getMessage());
        return false;
    }
}
