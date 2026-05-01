<?php
/**
 * Hype HR Management \u2014 Optional SMS Service
 * Providers: Twilio | Fast2SMS (India) | MSG91 (India)
 * Set SMS_ENABLED=true + SMS_PROVIDER + SMS_API_KEY in .env to enable.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

class HypeSmsService {

    private bool   $enabled;
    private string $provider;

    public function __construct() {
        $this->enabled  = (bool)SMS_ENABLED;
        $this->provider = strtolower(SMS_PROVIDER);
    }

    public function isEnabled(): bool { return $this->enabled; }

    /**
     * Send salary alert SMS when slip is generated.
     */
    public function sendSalaryAlert(array $employee, array $salaryData, array $company): bool {
        if (!$this->enabled) return false;
        $mobile = $this->formatMobile($employee['mobile'] ?? '');
        if (!$mobile) return false;

        $name    = $employee['name']                ?? 'Employee';
        $month   = ($salaryData['month'] ?? '') . ' ' . ($salaryData['year'] ?? '');
        $amount  = number_format((float)($salaryData['final_salary'] ?? 0), 0);
        $co      = $company['name']                 ?? 'Hype HR';

        $message = "Hi {$name}! Your salary slip for {$month} is ready. "
                 . "Net Pay: Rs.{$amount}. Download via Hype HR app. -{$co}";

        return match($this->provider) {
            'fast2sms' => $this->sendFast2Sms($mobile, $message),
            'msg91'    => $this->sendMsg91($mobile, $message),
            'twilio'   => $this->sendTwilio($mobile, $message),
            default    => $this->autoDetect($mobile, $message),
        };
    }

    /**
     * Auto-detect provider based on available credentials.
     * Priority: Fast2SMS (India) > MSG91 > Twilio
     */
    private function autoDetect(string $mobile, string $message): bool {
        if (!empty(SMS_API_KEY)) {
            // Try Fast2SMS if API key looks like Fast2SMS format or no provider set
            return $this->sendFast2Sms($mobile, $message);
        }
        if (!empty(TWILIO_SID) && !empty(TWILIO_TOKEN)) {
            return $this->sendTwilio($mobile, $message);
        }
        error_log('[HypeHR SMS] No SMS provider credentials configured');
        return false;
    }

    private function formatMobile(string $mobile): string {
        $mobile = preg_replace('/[^0-9+]/', '', $mobile);
        if (empty($mobile)) return '';
        if (str_starts_with($mobile, '+')) return $mobile;
        if (strlen($mobile) === 10) return '+91' . $mobile;  // Indian number
        return '+' . $mobile;
    }

    /**
     * Fast2SMS \u2014 India-specific, most cost-effective
     * API Key from: https://www.fast2sms.com/
     * Set SMS_API_KEY=your_fast2sms_api_key in .env
     */
    private function sendFast2Sms(string $to, string $message): bool {
        $apiKey = SMS_API_KEY;
        if (empty($apiKey)) {
            error_log('[HypeHR SMS] Fast2SMS API key not set (SMS_API_KEY)');
            return false;
        }
        // Fast2SMS uses 10-digit number without country code
        $mobile10 = preg_replace('/^\+91/', '', ltrim($to, '+'));
        $mobile10 = substr($mobile10, -10);

        $ch = curl_init('https://www.fast2sms.com/dev/bulkV2');
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode([
                'route'   => 'q',
                'message' => $message,
                'numbers' => $mobile10,
            ]),
            CURLOPT_HTTPHEADER     => [
                'authorization: ' . $apiKey,
                'Content-Type: application/json',
            ],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 20,
        ]);
        $raw    = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        $resp = json_decode($raw, true);
        $ok   = ($status === 200) && isset($resp['return']) && $resp['return'] === true;
        error_log("[HypeHR SMS] Fast2SMS -> {$mobile10} | HTTP {$status} | " . substr($raw, 0, 120));
        return $ok;
    }

    /**
     * Twilio SMS
     */
    private function sendTwilio(string $to, string $message): bool {
        if (empty(TWILIO_SID) || empty(TWILIO_TOKEN)) {
            error_log('[HypeHR SMS] Twilio credentials not set (SMS_ACCOUNT_SID + SMS_AUTH_TOKEN)');
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
        error_log("[HypeHR SMS] Twilio -> {$to} | HTTP {$status} | " . substr($raw, 0, 120));
        return $status === 201;
    }

    /**
     * MSG91 \u2014 India
     */
    private function sendMsg91(string $to, string $message): bool {
        $authKey  = SMS_API_KEY ?: (getenv('MSG91_AUTH_KEY') ?: '');
        $senderId = getenv('SMS_SENDER_ID') ?: 'HYPEHR';
        if (empty($authKey)) {
            error_log('[HypeHR SMS] MSG91 auth key not set (SMS_API_KEY)');
            return false;
        }
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
        error_log("[HypeHR SMS] MSG91 -> {$mobile} | " . $result);
        return strpos($result, 'type=success') !== false;
    }
}
