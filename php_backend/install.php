<?php
/**
 * Hype HR Management — One-Click Install
 * Visit https://yoursite.com/hype-hr/install.php to set up.
 * DELETE THIS FILE after installation!
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $projectId   = trim($_POST['project_id']   ?? '');
    $apiKey      = trim($_POST['api_key']       ?? '');
    $smtpHost    = trim($_POST['smtp_host']     ?? '');
    $smtpPort    = trim($_POST['smtp_port']     ?? '587');
    $smtpUser    = trim($_POST['smtp_user']     ?? '');
    $smtpPass    = trim($_POST['smtp_pass']     ?? '');
    $smtpFrom    = trim($_POST['smtp_from']     ?? '');
    $smsEnabled  = isset($_POST['sms_enabled']);
    $twilioSid   = trim($_POST['twilio_sid']    ?? '');
    $twilioToken = trim($_POST['twilio_token']  ?? '');
    $twilioFrom  = trim($_POST['twilio_from']   ?? '');

    // Write .env file
    $env = "FIREBASE_PROJECT_ID={$projectId}\n"
         . "FIREBASE_API_KEY={$apiKey}\n"
         . "SMTP_HOST={$smtpHost}\n"
         . "SMTP_PORT={$smtpPort}\n"
         . "SMTP_USER={$smtpUser}\n"
         . "SMTP_PASS={$smtpPass}\n"
         . "SMTP_FROM={$smtpFrom}\n"
         . "SMS_ENABLED=" . ($smsEnabled ? 'true' : 'false') . "\n"
         . "TWILIO_SID={$twilioSid}\n"
         . "TWILIO_TOKEN={$twilioToken}\n"
         . "TWILIO_FROM={$twilioFrom}\n";

    file_put_contents(__DIR__ . '/.env', $env);

    // Create dirs
    @mkdir(__DIR__ . '/salary_slips', 0755, true);
    @mkdir(__DIR__ . '/vendor',       0755, true);

    // Write cron instructions
    $cronLine = "0 6 1 * * php " . realpath(__DIR__) . "/cron_job.php >> /var/log/hype_hr_cron.log 2>&1";

    $success = true;
    $message = "Installation complete! Add this cron job on your server:<br><code>{$cronLine}</code><br><br>";
    $message .= "<strong style='color:red;'>IMPORTANT: Delete this install.php file immediately!</strong>";
}
?>
<!DOCTYPE html>
<html>
<head><title>Hype HR — Install</title>
<style>
body{font-family:Arial;max-width:600px;margin:40px auto;padding:20px;}
h1{color:#01696f;}input,select{width:100%;padding:8px;margin:6px 0 12px;border:1px solid #ccc;border-radius:6px;}
button{background:#01696f;color:#fff;padding:12px 24px;border:none;border-radius:8px;cursor:pointer;font-size:15px;}
.msg{background:#e8f8f5;padding:16px;border-radius:8px;margin-bottom:20px;}
</style></head>
<body>
<h1>🚀 Hype HR Management — Install</h1>
<?php if (!empty($message)): ?>
    <div class="msg"><?= $message ?></div>
<?php endif; ?>
<form method="post">
    <h3>Firebase Config</h3>
    <label>Firebase Project ID</label>
    <input name="project_id" placeholder="hype-hr-management" required>
    <label>Firebase Web API Key</label>
    <input name="api_key" placeholder="AIzaSy..." required>
    <h3>SMTP Email (Optional)</h3>
    <label>SMTP Host</label>
    <input name="smtp_host" placeholder="smtp.gmail.com">
    <label>SMTP Port</label>
    <input name="smtp_port" value="587">
    <label>SMTP Username (email)</label>
    <input name="smtp_user" type="email">
    <label>SMTP Password</label>
    <input name="smtp_pass" type="password">
    <label>From Email</label>
    <input name="smtp_from" type="email">
    <h3>SMS via Twilio (Optional)</h3>
    <label><input type="checkbox" name="sms_enabled"> Enable SMS notifications</label><br>
    <label>Twilio Account SID</label>
    <input name="twilio_sid">
    <label>Twilio Auth Token</label>
    <input name="twilio_token" type="password">
    <label>Twilio From Number</label>
    <input name="twilio_from" placeholder="+1234567890">
    <button type="submit">✅ Install Hype HR Backend</button>
</form>
</body></html>
