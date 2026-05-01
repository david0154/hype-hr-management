<?php
/**
 * Hype HR Management — Optional SMS Service
 * Provider: Twilio (default) — extend for MSG91, Fast2SMS, etc.
 * Enabled via SMS_ENABLED env var + Twilio credentials.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

class HypeSmsService {

    private bool   $enabled;
    private string $provider;

    public function __construct() {
        $this->enabled  = (bool)SMS_ENABLED;
        $this->provider = SMS_PROVIDER;
    }

    public function isEnabled(): bool { return $this->enabled; }

    /**
     * Send salary alert SMS when slip is generated.
     */
    public function sendSalaryAlert(array $employee, array $salaryData, array $company): bool {
        if (!$this->enabled) return false;
        $mobile = $this->formatMobile($employee['mobile'] ?? '');
        if (!$mobile) return false;

        $name    = $employee['name']               ?? 'Employee';
        $month   = ($salaryData['month'] ?? '') . ' ' . ($salaryData['year'] ?? '');
        $amount  = number_format((float)($salaryData['final_salary'] ?? 0), 0);
        $company = $company['name']                 ?? 'Hype HR';

        $message = "Hi {$name}! Your salary slip for {$month} is ready. "
                 . "Net Pay: Rs.{$amount}. Download via Hype HR app. -{$company}";

        return match($this->provider) {
            'twilio'  => $this->sendTwilio($mobile, $message),
            'msg91'   => $this->sendMsg91($mobile, $message),
            default   => $this->sendTwilio($mobile, $message),
        };
    }

    private function formatMobile(string $mobile): string {
        $mobile = preg_replace('/[^0-9+]/', '', $mobile);
        if (empty($mobile)) return '';
        if (str_starts_with($mobile, '+')) return $mobile;
        if (strlen($mobile) === 10) return '+91' . $mobile;
        return '+' . $mobile;
    }

    private function sendTwilio(string $to, string $message): bool {
        if (empty(TWILIO_SID) || empty(TWILIO_TOKEN)) {
            error_log('[HypeHR SMS] Twilio credentials not set');
            return false;
        }
        $url  = 'https://api.twilio.com/2010-04-01/Accounts/' . TWILIO_SID . '/Messages.json';
        $data = ['To' => $to, 'From' => TWILIO_FROM, 'Body' => $message];
        $ch   = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => http_build_query($data),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_USERPWD        => TWILIO_SID . ':' . TWILIO_TOKEN,
            CURLOPT_TIMEOUT        => 20,
        ]);
        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        error_log("[HypeHR SMS] Twilio → {$to} | HTTP {$status} | " . substr($raw, 0, 120));
        return $status === 201;
    }

    private function sendMsg91(string $to, string $message): bool {
        $authKey  = getenv('MSG91_AUTH_KEY') ?: '';
        $senderId = getenv('MSG91_SENDER_ID') ?: 'HYPEHR';
        if (empty($authKey)) { error_log('[HypeHR SMS] MSG91 auth key not set'); return false; }
        $mobile = ltrim($to, '+');
        $url    = 'https://api.msg91.com/api/sendhttp.php?' . http_build_query([
            'authkey'  => $authKey,
            'mobiles'  => $mobile,
            'message'  => $message,
            'sender'   => $senderId,
            'route'    => '4',
            'country'  => '91',
        ]);
        $ch = curl_init($url);
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20]);
        $result = curl_exec($ch);
        curl_close($ch);
        error_log("[HypeHR SMS] MSG91 → {$mobile} | " . $result);
        return strpos($result, 'type=success') !== false;
    }
}
