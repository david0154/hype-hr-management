<?php
/**
 * Hype HR Management — One Click Installer
 * Upload php_backend to hosting, open install.php in browser, fill values, done.
 */

$root = __DIR__;
$message = '';
$success = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $env = [
        'FIREBASE_PROJECT_ID' => trim($_POST['firebase_project_id'] ?? ''),
        'FIREBASE_API_KEY' => trim($_POST['firebase_api_key'] ?? ''),
        'FIREBASE_STORAGE_BUCKET' => trim($_POST['firebase_storage_bucket'] ?? ''),
        'SMS_PROVIDER' => trim($_POST['sms_provider'] ?? ''),
        'SMS_API_KEY' => trim($_POST['sms_api_key'] ?? ''),
        'SMS_AUTH_TOKEN' => trim($_POST['sms_auth_token'] ?? ''),
        'SMS_ACCOUNT_SID' => trim($_POST['sms_account_sid'] ?? ''),
        'SMS_FROM_NUMBER' => trim($_POST['sms_from_number'] ?? ''),
        'SMS_SENDER_ID' => trim($_POST['sms_sender_id'] ?? 'HYPEHR'),
    ];

    $lines = [];
    foreach ($env as $k => $v) {
        $lines[] = $k . '="' . addslashes($v) . '"';
    }

    file_put_contents($root . '/.env', implode(PHP_EOL, $lines) . PHP_EOL);

    if (!empty($_POST['service_account_json'])) {
        file_put_contents($root . '/serviceAccountKey.json', trim($_POST['service_account_json']));
    }

    $htaccess = "RewriteEngine On\nRewriteCond %{REQUEST_FILENAME} !-f\nRewriteCond %{REQUEST_FILENAME} !-d\nRewriteRule ^ webhook.php [QSA,L]\n";
    file_put_contents(dirname(__DIR__) . '/.htaccess', $htaccess);

    $success = true;
    $message = 'Installation complete. Now run composer install and set cron: 5 0 1 * * php ' . $root . '/cron_job.php';
}
?>
<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hype HR Installer</title>
<style>
body{font-family:Arial,sans-serif;background:#f5f7fb;margin:0;padding:24px;color:#222}.wrap{max-width:900px;margin:auto;background:#fff;padding:24px;border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.08)}
input,textarea,select{width:100%;padding:12px;margin-top:6px;margin-bottom:16px;border:1px solid #ccc;border-radius:8px;box-sizing:border-box}button{background:#0d6efd;color:#fff;border:none;padding:14px 18px;border-radius:8px;font-weight:700;cursor:pointer}.ok{padding:12px;background:#eaf8ee;border:1px solid #8bd3a4;border-radius:8px;margin-bottom:16px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<h1>Hype HR Management Installer</h1>
<p>Configure Firebase, optional SMS, and upload service account JSON for one-click hosting setup.</p>
<?php if ($message): ?><div class="<?= $success ? 'ok' : '' ?>"><?= htmlspecialchars($message) ?></div><?php endif; ?>
<form method="post">
<div class="grid">
<div><label>Firebase Project ID<input name="firebase_project_id" required></label></div>
<div><label>Firebase API Key<input name="firebase_api_key"></label></div>
<div><label>Firebase Storage Bucket<input name="firebase_storage_bucket" required placeholder="your-project.appspot.com"></label></div>
<div><label>SMS Provider<select name="sms_provider"><option value="">Disabled</option><option value="twilio">Twilio</option><option value="fast2sms">Fast2SMS</option><option value="msg91">MSG91</option></select></label></div>
<div><label>SMS API Key<input name="sms_api_key"></label></div>
<div><label>SMS Auth Token<input name="sms_auth_token"></label></div>
<div><label>SMS Account SID<input name="sms_account_sid"></label></div>
<div><label>SMS From Number<input name="sms_from_number"></label></div>
<div><label>SMS Sender ID<input name="sms_sender_id" value="HYPEHR"></label></div>
</div>
<label>Firebase Service Account JSON<textarea name="service_account_json" rows="12" placeholder='Paste full service account JSON here'></textarea></label>
<button type="submit">Install Backend</button>
</form>
</div></body></html>
