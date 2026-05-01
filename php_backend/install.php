<?php
/**
 * Hype HR Management \u2014 One-Click Install
 * Visit https://yoursite.com/hype-hr/install.php to set up.
 * \u26a0\ufe0f DELETE THIS FILE after installation!
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

$errors  = [];
$success = false;
$message = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $projectId     = trim($_POST['project_id']     ?? '');
    $storageBucket = trim($_POST['storage_bucket'] ?? '');
    $apiKey        = trim($_POST['api_key']         ?? '');
    $serviceJson   = trim($_POST['service_json']    ?? '');
    $apiSecret     = trim($_POST['api_secret']      ?? '');
    $smtpHost      = trim($_POST['smtp_host']       ?? '');
    $smtpPort      = trim($_POST['smtp_port']       ?? '587');
    $smtpUser      = trim($_POST['smtp_user']       ?? '');
    $smtpPass      = trim($_POST['smtp_pass']       ?? '');
    $smtpFrom      = trim($_POST['smtp_from']       ?? '');
    $smtpFromName  = trim($_POST['smtp_from_name']  ?? 'Hype HR Management');
    $smsEnabled    = isset($_POST['sms_enabled']);
    $smsProvider   = trim($_POST['sms_provider']    ?? '');
    $smsApiKey     = trim($_POST['sms_api_key']     ?? '');
    $twilioSid     = trim($_POST['twilio_sid']      ?? '');
    $twilioToken   = trim($_POST['twilio_token']    ?? '');
    $twilioFrom    = trim($_POST['twilio_from']     ?? '');

    // Validation
    if (empty($projectId))  $errors[] = 'Firebase Project ID is required.';
    if (empty($apiKey))     $errors[] = 'Firebase Web API Key is required.';
    if (empty($apiSecret))  $apiSecret = bin2hex(random_bytes(24)); // auto-generate

    if (empty($storageBucket)) {
        $storageBucket = $projectId . '.appspot.com';
    }

    if (empty($errors)) {
        $env = "FIREBASE_PROJECT_ID={$projectId}\n"
             . "FIREBASE_STORAGE_BUCKET={$storageBucket}\n"
             . "FIREBASE_API_KEY={$apiKey}\n"
             . (empty($serviceJson) ? '' : "FIREBASE_SERVICE_JSON={$serviceJson}\n")
             . "API_SECRET={$apiSecret}\n"
             . "SMTP_HOST={$smtpHost}\n"
             . "SMTP_PORT={$smtpPort}\n"
             . "SMTP_USER={$smtpUser}\n"
             . "SMTP_PASS={$smtpPass}\n"
             . "SMTP_FROM={$smtpFrom}\n"
             . "SMTP_FROM_NAME={$smtpFromName}\n"
             . "SMS_ENABLED=" . ($smsEnabled ? 'true' : 'false') . "\n"
             . "SMS_PROVIDER={$smsProvider}\n"
             . "SMS_API_KEY={$smsApiKey}\n"
             . (empty($twilioSid)   ? '' : "SMS_ACCOUNT_SID={$twilioSid}\n")
             . (empty($twilioToken) ? '' : "SMS_AUTH_TOKEN={$twilioToken}\n")
             . (empty($twilioFrom)  ? '' : "SMS_FROM_NUMBER={$twilioFrom}\n");

        file_put_contents(__DIR__ . '/.env', $env);

        // Create required directories
        foreach (['/temp', '/salary_slips'] as $dir) {
            @mkdir(__DIR__ . $dir, 0755, true);
        }

        // Cron suggestion
        $cronPath = realpath(__DIR__) . '/cron_job.php';
        $cronLine = "5 0 1 * * TZ=Asia/Kolkata php {$cronPath} >> /var/log/hype_hr_cron.log 2>&1";

        $success = true;
        $message = "<strong>\u2705 Installation complete!</strong><br><br>"
                 . "<strong>API Secret (save this):</strong> <code>{$apiSecret}</code><br><br>"
                 . "<strong>\ud83d\udcc5 Cron Job (add to server crontab):</strong><br>"
                 . "<code style='word-break:break-all'>{$cronLine}</code><br><br>"
                 . "<em>Run: <code>crontab -e</code> and paste the line above.</em><br><br>"
                 . "<strong>Next steps:</strong><br>"
                 . "1. Run <code>composer install</code> inside <code>php_backend/</code><br>"
                 . "2. Upload <code>firebase-service-account.json</code> to the backend folder<br>"
                 . "3. Configure SMTP settings in your Firestore <code>settings/smtp</code> document<br>"
                 . "4. <strong style='color:red;'>\u26a0\ufe0f DELETE this install.php file immediately!</strong>";
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hype HR \u2014 Install</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, Helvetica, sans-serif; background: #f0f4f4; color: #222; padding: 24px 16px; }
    .wrap { max-width: 640px; margin: 0 auto; background: #fff; border-radius: 12px;
            padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,.08); }
    h1   { color: #01696f; font-size: 22px; margin-bottom: 4px; }
    h3   { color: #01696f; font-size: 15px; margin: 24px 0 8px; border-bottom: 1px solid #e0e0e0; padding-bottom: 4px; }
    p.sub { color: #666; font-size: 13px; margin-bottom: 20px; }
    label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 4px; color: #444; }
    input[type=text], input[type=email], input[type=password], input[type=number], select {
      width: 100%; padding: 9px 12px; border: 1px solid #ccc; border-radius: 6px;
      font-size: 14px; margin-bottom: 14px; transition: border-color .2s;
    }
    input:focus, select:focus { outline: none; border-color: #01696f; }
    .checkbox-row { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
    .checkbox-row label { margin: 0; font-weight: normal; }
    button[type=submit] {
      background: #01696f; color: #fff; padding: 12px 28px; border: none;
      border-radius: 8px; font-size: 15px; cursor: pointer; width: 100%; margin-top: 8px;
    }
    button[type=submit]:hover { background: #0c4e54; }
    .msg  { background: #e8f8f5; border: 1px solid #a0d8ce; padding: 16px; border-radius: 8px;
            margin-bottom: 20px; font-size: 14px; line-height: 1.7; }
    .err  { background: #ffeef0; border: 1px solid #f5a0a8; padding: 14px; border-radius: 8px;
            margin-bottom: 20px; font-size: 14px; }
    .err li { margin-left: 18px; }
    code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
    .optional { color: #999; font-weight: normal; font-size: 12px; }
    .note { font-size: 12px; color: #888; margin-top: -10px; margin-bottom: 14px; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>\ud83d\ude80 Hype HR Management \u2014 Install</h1>
  <p class="sub">One-click backend setup. Fill in the required fields below.</p>

  <?php if (!empty($errors)): ?>
    <div class="err"><strong>Please fix the following:</strong><ul>
      <?php foreach ($errors as $e): ?><li><?= htmlspecialchars($e) ?></li><?php endforeach; ?>
    </ul></div>
  <?php endif; ?>

  <?php if ($success): ?>
    <div class="msg"><?= $message ?></div>
  <?php else: ?>
  <form method="post">
    <h3>\ud83d\udd25 Firebase Config <span class="optional">(required)</span></h3>
    <label>Firebase Project ID</label>
    <input type="text" name="project_id" placeholder="hype-hr-management" required value="<?= htmlspecialchars($_POST['project_id'] ?? '') ?>">
    <label>Firebase Storage Bucket</label>
    <input type="text" name="storage_bucket" placeholder="hype-hr-management.appspot.com" value="<?= htmlspecialchars($_POST['storage_bucket'] ?? '') ?>">
    <p class="note">Leave blank to auto-generate from Project ID.</p>
    <label>Firebase Web API Key</label>
    <input type="text" name="api_key" placeholder="AIzaSy..." required value="<?= htmlspecialchars($_POST['api_key'] ?? '') ?>">
    <label>Service Account JSON Path <span class="optional">(optional)</span></label>
    <input type="text" name="service_json" placeholder="/var/www/html/php_backend/firebase-service-account.json" value="<?= htmlspecialchars($_POST['service_json'] ?? '') ?>">
    <p class="note">Absolute server path to your downloaded Firebase service account JSON file.</p>
    <label>API Secret <span class="optional">(auto-generated if blank)</span></label>
    <input type="text" name="api_secret" placeholder="leave blank to auto-generate" value="<?= htmlspecialchars($_POST['api_secret'] ?? '') ?>">

    <h3>\ud83d\udce7 SMTP Email <span class="optional">(optional)</span></h3>
    <label>SMTP Host</label>
    <input type="text" name="smtp_host" placeholder="smtp.gmail.com" value="<?= htmlspecialchars($_POST['smtp_host'] ?? '') ?>">
    <label>SMTP Port</label>
    <input type="number" name="smtp_port" value="<?= htmlspecialchars($_POST['smtp_port'] ?? '587') ?>">
    <label>SMTP Username (email)</label>
    <input type="email" name="smtp_user" value="<?= htmlspecialchars($_POST['smtp_user'] ?? '') ?>">
    <label>SMTP Password</label>
    <input type="password" name="smtp_pass">
    <label>From Email</label>
    <input type="email" name="smtp_from" value="<?= htmlspecialchars($_POST['smtp_from'] ?? '') ?>">
    <label>From Name</label>
    <input type="text" name="smtp_from_name" placeholder="Hype HR Management" value="<?= htmlspecialchars($_POST['smtp_from_name'] ?? 'Hype HR Management') ?>">

    <h3>\ud83d\udcf1 SMS Notifications <span class="optional">(optional)</span></h3>
    <div class="checkbox-row">
      <input type="checkbox" name="sms_enabled" id="sms_enabled" <?= !empty($_POST['sms_enabled']) ? 'checked' : '' ?>>
      <label for="sms_enabled">Enable SMS notifications</label>
    </div>
    <label>SMS Provider</label>
    <select name="sms_provider">
      <option value="">\u2014 Select provider \u2014</option>
      <option value="fast2sms" <?= ($_POST['sms_provider'] ?? '') === 'fast2sms' ? 'selected' : '' ?>>Fast2SMS (India \u2014 recommended)</option>
      <option value="msg91"    <?= ($_POST['sms_provider'] ?? '') === 'msg91'    ? 'selected' : '' ?>>MSG91 (India)</option>
      <option value="twilio"   <?= ($_POST['sms_provider'] ?? '') === 'twilio'   ? 'selected' : '' ?>>Twilio (International)</option>
    </select>
    <label>SMS API Key <span class="optional">(Fast2SMS / MSG91 key, or Twilio Auth Token)</span></label>
    <input type="password" name="sms_api_key">
    <label>Twilio Account SID <span class="optional">(Twilio only)</span></label>
    <input type="text" name="twilio_sid" value="<?= htmlspecialchars($_POST['twilio_sid'] ?? '') ?>">
    <label>Twilio Auth Token <span class="optional">(Twilio only)</span></label>
    <input type="password" name="twilio_token">
    <label>Twilio From Number <span class="optional">(Twilio only, e.g. +1234567890)</span></label>
    <input type="text" name="twilio_from" placeholder="+1234567890" value="<?= htmlspecialchars($_POST['twilio_from'] ?? '') ?>">

    <button type="submit">\u2705 Install Hype HR Backend</button>
  </form>
  <?php endif; ?>
</div>
</body></html>
