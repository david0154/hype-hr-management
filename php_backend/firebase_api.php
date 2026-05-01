<?php
/**
 * Hype HR Management — Firebase REST API Helper
 * Uses Firebase REST API + Service Account JWT for server-side operations
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

function getFirebaseAccessToken(): string {
    static $cachedToken = null;
    static $tokenExpiry = 0;

    if ($cachedToken && time() < $tokenExpiry - 60) {
        return $cachedToken;
    }

    if (!file_exists(SERVICE_ACCOUNT_PATH)) {
        throw new RuntimeException('Missing Firebase service account file: ' . SERVICE_ACCOUNT_PATH);
    }

    $serviceAccount = json_decode(file_get_contents(SERVICE_ACCOUNT_PATH), true);
    if (empty($serviceAccount['client_email']) || empty($serviceAccount['private_key'])) {
        throw new RuntimeException('Invalid Firebase service account JSON');
    }

    $now = time();
    $payload = [
        'iss'   => $serviceAccount['client_email'],
        'scope' => 'https://www.googleapis.com/auth/datastore https://www.googleapis.com/auth/devstorage.full_control',
        'aud'   => 'https://oauth2.googleapis.com/token',
        'iat'   => $now,
        'exp'   => $now + 3600,
    ];

    $header = base64UrlEncode(json_encode(['alg' => 'RS256', 'typ' => 'JWT']));
    $claims = base64UrlEncode(json_encode($payload));
    $signature = '';
    openssl_sign("$header.$claims", $signature, $serviceAccount['private_key'], 'SHA256');
    $jwt = "$header.$claims." . base64UrlEncode($signature);

    $ch = curl_init('https://oauth2.googleapis.com/token');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query([
            'grant_type' => 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion'  => $jwt,
        ]),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
    ]);
    $raw = curl_exec($ch);
    curl_close($ch);

    $response = json_decode($raw ?: '{}', true);
    $cachedToken = $response['access_token'] ?? '';
    $tokenExpiry = $now + (int)($response['expires_in'] ?? 3600);

    if (!$cachedToken) {
        throw new RuntimeException('Unable to obtain Firebase access token');
    }

    return $cachedToken;
}

function base64UrlEncode(string $data): string {
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

function firestoreUrl(string $path): string {
    return 'https://firestore.googleapis.com/v1/projects/' . FIREBASE_PROJECT_ID . '/databases/(default)/documents/' . ltrim($path, '/');
}

function firestoreRequest(string $method, string $path, ?array $body = null): ?array {
    $token = getFirebaseAccessToken();
    $ch = curl_init(firestoreUrl($path));
    $opts = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => [
            'Authorization: Bearer ' . $token,
            'Content-Type: application/json',
        ],
        CURLOPT_TIMEOUT => 30,
    ];

    if ($body !== null) {
        $opts[CURLOPT_POSTFIELDS] = json_encode($body);
    }

    curl_setopt_array($ch, $opts);
    $raw = curl_exec($ch);
    curl_close($ch);
    return json_decode($raw ?: '{}', true);
}

function firestoreValue(array $val): mixed {
    if (isset($val['stringValue'])) return $val['stringValue'];
    if (isset($val['integerValue'])) return (int)$val['integerValue'];
    if (isset($val['doubleValue'])) return (float)$val['doubleValue'];
    if (isset($val['booleanValue'])) return (bool)$val['booleanValue'];
    if (isset($val['nullValue'])) return null;
    if (isset($val['timestampValue'])) return $val['timestampValue'];
    if (isset($val['arrayValue'])) return array_map('firestoreValue', $val['arrayValue']['values'] ?? []);
    if (isset($val['mapValue'])) {
        $out = [];
        foreach (($val['mapValue']['fields'] ?? []) as $k => $v) {
            $out[$k] = firestoreValue($v);
        }
        return $out;
    }
    return null;
}

function firestoreDocToArray(array $doc): array {
    $out = [];
    foreach (($doc['fields'] ?? []) as $key => $val) {
        $out[$key] = firestoreValue($val);
    }
    return $out;
}

function phpToFirestoreValue(mixed $value): array {
    if (is_null($value)) return ['nullValue' => null];
    if (is_bool($value)) return ['booleanValue' => $value];
    if (is_int($value)) return ['integerValue' => (string)$value];
    if (is_float($value)) return ['doubleValue' => $value];
    if (is_string($value)) return ['stringValue' => $value];
    if (is_array($value) && array_is_list($value)) {
        return ['arrayValue' => ['values' => array_map('phpToFirestoreValue', $value)]];
    }
    if (is_array($value)) {
        $fields = [];
        foreach ($value as $k => $v) {
            $fields[$k] = phpToFirestoreValue($v);
        }
        return ['mapValue' => ['fields' => $fields]];
    }
    return ['stringValue' => (string)$value];
}

function arrayToFirestoreFields(array $data): array {
    $fields = [];
    foreach ($data as $key => $value) {
        $fields[$key] = phpToFirestoreValue($value);
    }
    return ['fields' => $fields];
}

function firebaseSet(string $path, array $data): void {
    firestoreRequest('PATCH', $path, arrayToFirestoreFields($data));
}

function uploadToFirebaseStorage(string $localPath, string $remotePath): string {
    $token = getFirebaseAccessToken();
    $bucket = FIREBASE_STORAGE_BUCKET;
    $encoded = rawurlencode($remotePath);
    $url = "https://storage.googleapis.com/upload/storage/v1/b/{$bucket}/o?uploadType=media&name={$encoded}";

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => file_get_contents($localPath),
        CURLOPT_HTTPHEADER => [
            'Authorization: Bearer ' . $token,
            'Content-Type: application/pdf',
        ],
        CURLOPT_TIMEOUT => 60,
    ]);
    curl_exec($ch);
    curl_close($ch);

    return "https://storage.googleapis.com/{$bucket}/{$remotePath}";
}

function deleteFromFirebaseStorage(string $url): void {
    $bucket = FIREBASE_STORAGE_BUCKET;
    $path = str_replace("https://storage.googleapis.com/{$bucket}/", '', $url);
    if (!$path || $path === $url) return;

    $token = getFirebaseAccessToken();
    $encoded = rawurlencode($path);
    $ch = curl_init("https://storage.googleapis.com/storage/v1/b/{$bucket}/o/{$encoded}");
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => 'DELETE',
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token],
        CURLOPT_TIMEOUT => 30,
    ]);
    curl_exec($ch);
    curl_close($ch);
}

class HypeFirebaseAPI {

    public function getSettings(): array {
        return $this->getDocument('settings/app') ?? [
            'monthly_working_days' => 26,
            'ot_rate_multiplier' => 1.5,
        ];
    }

    public function getCompanyDetails(): array {
        return $this->getDocument('settings/company') ?? [
            'name' => 'Hype Pvt Ltd',
            'address' => '',
            'email' => SUPPORT_MAIL,
            'phone' => '',
        ];
    }

    public function getSmtpConfig(): array {
        return $this->getDocument('settings/smtp') ?? [];
    }

    public function getManagementRoles(): array {
        return $this->getCollection('management_users');
    }

    public function getActiveEmployees(): array {
        $all = $this->getCollection('employees');
        return array_values(array_filter($all, fn($emp) => !isset($emp['active']) || $emp['active'] === true || $emp['active'] === 1 || $emp['active'] === '1'));
    }

    public function salarySlipExists(string $employeeId, string $monthKey): bool {
        return $this->getDocument("salary/{$employeeId}_{$monthKey}") !== null;
    }

    public function getSalaryAdjustments(string $employeeId, string $monthKey): array {
        $adjustments = $this->getCollection('salary_adjustments');
        $bonus = 0.0;
        $deduction = 0.0;
        $advance = 0.0;

        foreach ($adjustments as $row) {
            if (($row['employee_id'] ?? '') !== $employeeId) continue;
            if (($row['month_key'] ?? '') !== $monthKey) continue;
            $bonus += (float)($row['bonus'] ?? 0);
            $deduction += (float)($row['deduction'] ?? 0);
            $advance += (float)($row['advance'] ?? 0);
        }

        return [
            'bonus' => $bonus,
            'deduction' => $deduction,
            'advance' => $advance,
        ];
    }

    public function getAttendanceSummary(string $employeeId, int $year, int $month): array {
        $sessions = $this->getCollection('sessions');
        $fullDays = 0.0;
        $halfDays = 0.0;
        $absentDays = 0.0;
        $paidHolidays = 0.0;
        $otHours = 0.0;

        $daysInMonth = cal_days_in_month(CAL_GREGORIAN, $month, $year);
        $presentMap = [];

        foreach ($sessions as $session) {
            if (($session['employee_id'] ?? '') !== $employeeId) continue;
            $date = $session['date'] ?? '';
            if (!$date || substr($date, 0, 7) !== sprintf('%04d-%02d', $year, $month)) continue;

            $dutyHours = (float)($session['duty_hours'] ?? 0);
            $sessionOt = (float)($session['ot_hours'] ?? 0);
            $presentMap[$date] = true;

            if ($dutyHours < 4) {
                $absentDays += 1;
            } elseif ($dutyHours < 7) {
                $halfDays += 1;
            } else {
                $fullDays += 1;
            }

            if ($sessionOt >= 4 && $sessionOt < 7) {
                $otHours += 4;
            } elseif ($sessionOt >= 7) {
                $otHours += $sessionOt;
            }
        }

        for ($day = 1; $day <= $daysInMonth; $day++) {
            $date = sprintf('%04d-%02d-%02d', $year, $month, $day);
            $dow = (int)date('w', strtotime($date));
            if ($dow !== 0) continue;

            $sat = date('Y-m-d', strtotime($date . ' -1 day'));
            $mon = date('Y-m-d', strtotime($date . ' +1 day'));
            $satPresent = isset($presentMap[$sat]);
            $monPresent = isset($presentMap[$mon]);

            if ($satPresent && $monPresent) {
                $paidHolidays += 1;
            } elseif ($satPresent || $monPresent) {
                $paidHolidays += 0.5;
            }
        }

        return [
            'total_present' => $fullDays,
            'half_days' => $halfDays,
            'absent_days' => $absentDays,
            'paid_holidays' => $paidHolidays,
            'ot_hours' => $otHours,
        ];
    }

    public function uploadPdfToStorage(string $pdfPath, string $storagePath): string {
        return uploadToFirebaseStorage($pdfPath, $storagePath);
    }

    public function saveSalaryRecord(string $employeeId, string $monthKey, array $data): void {
        firebaseSet("salary/{$employeeId}_{$monthKey}", $data);
    }

    public function cleanupExpiredSlips(): int {
        $salaryRows = $this->getCollection('salary');
        $deleted = 0;
        $now = time();

        foreach ($salaryRows as $row) {
            $expiresAt = strtotime($row['expires_at'] ?? '');
            if (!$expiresAt || $expiresAt > $now) continue;
            if (!empty($row['slip_url'])) {
                deleteFromFirebaseStorage($row['slip_url']);
                $deleted++;
            }
        }

        return $deleted;
    }

    private function getDocument(string $path): ?array {
        $result = firestoreRequest('GET', $path);
        if (isset($result['error']) || !isset($result['fields'])) {
            return null;
        }
        return firestoreDocToArray($result);
    }

    private function getCollection(string $collection): array {
        $result = firestoreRequest('GET', $collection);
        $docs = [];
        foreach (($result['documents'] ?? []) as $doc) {
            $docs[] = firestoreDocToArray($doc);
        }
        return $docs;
    }
}
