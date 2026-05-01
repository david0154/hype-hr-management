<?php
/**
 * Hype HR Management — Optional SMS Service
 * Supports: Twilio, Fast2SMS (India), MSG91 (India)
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 *
 * Usage:
 *   $sms = new HypeSmsService();
 *   $sms->sendSalaryAlert($employee, $salaryData, $company);
 */

require_once __DIR__ . '/config.php';

class HypeSmsService {

    private string $provider;

    public function __construct() {
        $this->provider = strtolower(SMS_PROVIDER);
    }

    /** Returns true if SMS is configured and enabled */
    public function isEnabled(): bool {
        return !empty($this->provider) && !empty(SMS_API_KEY);
    }

    /**
     * Send salary alert SMS to employee
     * @param array $employee  ['name','mobile','employee_id']
     * @param array $salaryData ['month','year','final_salary','payment_mode']
     * @param array $company   ['name']
     * @return bool
     */
    public function sendSalaryAlert(array $employee, array $salaryData, array $company): bool {
        if (!$this->isEnabled()) return false;

        $mobile = preg_replace('/\D/', '', $employee['mobile'] ?? '');
        if (strlen($mobile) < 10) return false;

        $name    = $employee['name']           ?? 'Employee';
        $empId   = $employee['employee_id']    ?? '';
        $month   = ($salaryData['month']       ?? '') . ' ' . ($salaryData['year'] ?? '');
        $amount  = 'Rs.' . number_format((float)($salaryData['final_salary'] ?? 0), 0);
        $mode    = $salaryData['payment_mode'] ?? 'CASH';
        $companyName = $company['name']        ?? APP_NAME;

        $message = "Dear $name ($empId), Your salary for $month has been processed. "
                 . "Net Pay: $amount | Mode: $mode | $companyName";

        return match ($this->provider) {
            'twilio'    => $this->sendViaTwilio($mobile, $message),
            'fast2sms'  => $this->sendViaFast2SMS($mobile, $message),
            'msg91'     => $this->sendViaMSG91($mobile, $message),
            default     => false,
        };
    }

    /**
     * Send attendance alert SMS (security / supervisor mode)
     */
    public function sendAttendanceAlert(array $employee, string $action, string $location): bool {
        if (!$this->isEnabled()) return false;

        $mobile = preg_replace('/\D/', '', $employee['mobile'] ?? '');
        if (strlen($mobile) < 10) return false;

        $name  = $employee['name']        ?? 'Employee';
        $empId = $employee['employee_id'] ?? '';
        $time  = date('h:i A');
        $msg   = "HYPE HR: $name ($empId) has checked $action at $location on " . date('d M Y') . " at $time.";

        return match ($this->provider) {
            'twilio'   => $this->sendViaTwilio($mobile, $msg),
            'fast2sms' => $this->sendViaFast2SMS($mobile, $msg),
            'msg91'    => $this->sendViaMSG91($mobile, $msg),
            default    => false,
        };
    }

    // ── Twilio ────────────────────────────────────────────────────────────────────
    private function sendViaTwilio(string $mobile, string $message): bool {
        if (strlen($mobile) === 10) $mobile = '+91' . $mobile;
        elseif (!str_starts_with($mobile, '+')) $mobile = '+' . $mobile;

        $url  = 'https://api.twilio.com/2010-04-01/Accounts/' . SMS_ACCOUNT_SID . '/Messages.json';
        $data = ['To' => $mobile, 'From' => SMS_FROM_NUMBER, 'Body' => $message];

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => http_build_query($data),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_USERPWD        => SMS_ACCOUNT_SID . ':' . SMS_AUTH_TOKEN,
            CURLOPT_TIMEOUT        => 15,
        ]);
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        $result = json_decode($response, true);
        return $httpCode === 201 && isset($result['sid']);
    }

    // ── Fast2SMS (India — cheapest option) ────────────────────────────────────────
    private function sendViaFast2SMS(string $mobile, string $message): bool {
        if (strlen($mobile) > 10) $mobile = substr($mobile, -10);

        $ch = curl_init('https://www.fast2sms.com/dev/bulkV2');
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode([
                'route'    => 'q',
                'message'  => $message,
                'language' => 'english',
                'flash'    => 0,
                'numbers'  => $mobile,
            ]),
            CURLOPT_HTTPHEADER     => [
                'authorization: ' . SMS_API_KEY,
                'Content-Type: application/json',
            ],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 15,
        ]);
        $response = curl_exec($ch);
        curl_close($ch);

        $result = json_decode($response, true);
        return isset($result['return']) && $result['return'] === true;
    }

    // ── MSG91 (India) ────────────────────────────────────────────────────────────
    private function sendViaMSG91(string $mobile, string $message): bool {
        if (strlen($mobile) === 10) $mobile = '91' . $mobile;

        $ch = curl_init('https://api.msg91.com/api/v5/flow/');
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode([
                'template_id' => SMS_SENDER_ID,
                'short_url'   => '0',
                'realTimeResponse' => '1',
                'recipients'  => [['mobiles' => $mobile, 'var1' => substr($message, 0, 200)]],
            ]),
            CURLOPT_HTTPHEADER     => [
                'authkey: ' . SMS_API_KEY,
                'Content-Type: application/json',
            ],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 15,
        ]);
        $response = curl_exec($ch);
        curl_close($ch);

        $result = json_decode($response, true);
        return isset($result['type']) && $result['type'] === 'success';
    }
}
