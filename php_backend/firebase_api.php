<?php
/**
 * Hype HR Management — Firebase REST API Helper
 * Uses Firestore REST API + Service Account JWT for server-side access.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

// ── JWT / OAuth2 ─────────────────────────────────────────────────────────────
function getFirebaseAccessToken(): string {
    static $cachedToken = null;
    static $tokenExpiry = 0;
    if ($cachedToken && time() < $tokenExpiry - 60) return $cachedToken;

    if (!file_exists(SERVICE_ACCOUNT_PATH))
        throw new RuntimeException('Missing Firebase service account: ' . SERVICE_ACCOUNT_PATH);

    $sa = json_decode(file_get_contents(SERVICE_ACCOUNT_PATH), true);
    if (empty($sa['client_email']) || empty($sa['private_key']))
        throw new RuntimeException('Invalid Firebase service account JSON');

    $now     = time();
    $payload = [
        'iss'   => $sa['client_email'],
        'scope' => implode(' ', [
            'https://www.googleapis.com/auth/datastore',
            'https://www.googleapis.com/auth/devstorage.full_control',
        ]),
        'aud'   => 'https://oauth2.googleapis.com/token',
        'iat'   => $now,
        'exp'   => $now + 3600,
    ];
    $header  = b64u(json_encode(['alg' => 'RS256', 'typ' => 'JWT']));
    $claims  = b64u(json_encode($payload));
    $sig     = '';
    openssl_sign("$header.$claims", $sig, $sa['private_key'], 'SHA256');
    $jwt = "$header.$claims." . b64u($sig);

    $ch = curl_init('https://oauth2.googleapis.com/token');
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => http_build_query([
            'grant_type' => 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion'  => $jwt,
        ]),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 30,
    ]);
    $res = json_decode(curl_exec($ch) ?: '{}', true);
    curl_close($ch);

    $cachedToken = $res['access_token'] ?? '';
    $tokenExpiry = $now + (int)($res['expires_in'] ?? 3600);
    if (!$cachedToken) throw new RuntimeException('Cannot get Firebase access token');
    return $cachedToken;
}

function b64u(string $data): string {
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

// ── Firestore REST helpers ───────────────────────────────────────────────────
function firestoreUrl(string $path): string {
    return 'https://firestore.googleapis.com/v1/projects/' . FIREBASE_PROJECT_ID
         . '/databases/(default)/documents/' . ltrim($path, '/');
}

function firestoreRequest(string $method, string $path, ?array $body = null): ?array {
    $token = getFirebaseAccessToken();
    $ch    = curl_init(firestoreUrl($path));
    $opts  = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST  => $method,
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . $token,
            'Content-Type: application/json',
        ],
        CURLOPT_TIMEOUT => 30,
    ];
    if ($body !== null) $opts[CURLOPT_POSTFIELDS] = json_encode($body);
    curl_setopt_array($ch, $opts);
    $raw = curl_exec($ch);
    curl_close($ch);
    return json_decode($raw ?: '{}', true);
}

function fsValue(array $v): mixed {
    if (isset($v['stringValue']))    return $v['stringValue'];
    if (isset($v['integerValue']))   return (int)$v['integerValue'];
    if (isset($v['doubleValue']))    return (float)$v['doubleValue'];
    if (isset($v['booleanValue']))   return (bool)$v['booleanValue'];
    if (isset($v['nullValue']))      return null;
    if (isset($v['timestampValue'])) return $v['timestampValue'];
    if (isset($v['arrayValue']))     return array_map('fsValue', $v['arrayValue']['values'] ?? []);
    if (isset($v['mapValue'])) {
        $out = [];
        foreach ($v['mapValue']['fields'] ?? [] as $k => $fv) $out[$k] = fsValue($fv);
        return $out;
    }
    return null;
}

function fsDocToArray(array $doc): array {
    $out = [];
    foreach (($doc['fields'] ?? []) as $k => $v) $out[$k] = fsValue($v);
    return $out;
}

function phpToFs(mixed $value): array {
    if (is_null($value))   return ['nullValue'    => null];
    if (is_bool($value))   return ['booleanValue' => $value];
    if (is_int($value))    return ['integerValue'  => (string)$value];
    if (is_float($value))  return ['doubleValue'   => $value];
    if (is_string($value)) return ['stringValue'   => $value];
    if (is_array($value) && array_is_list($value))
        return ['arrayValue' => ['values' => array_map('phpToFs', $value)]];
    if (is_array($value)) {
        $fields = [];
        foreach ($value as $k => $v) $fields[$k] = phpToFs($v);
        return ['mapValue' => ['fields' => $fields]];
    }
    return ['stringValue' => (string)$value];
}

function arrayToFsFields(array $data): array {
    $fields = [];
    foreach ($data as $k => $v) $fields[$k] = phpToFs($v);
    return ['fields' => $fields];
}

function firebase_get_document(string $path): ?array {
    $res = firestoreRequest('GET', $path);
    if (isset($res['error']) || !isset($res['fields'])) return null;
    return fsDocToArray($res);
}

function firebaseSet(string $path, array $data): void {
    firestoreRequest('PATCH', $path, arrayToFsFields($data));
}

// ── Storage helpers ──────────────────────────────────────────────────────────
function uploadToFirebaseStorage(string $localPath, string $remotePath): string {
    $token   = getFirebaseAccessToken();
    $bucket  = FIREBASE_STORAGE_BUCKET;
    $encoded = rawurlencode($remotePath);
    $url     = "https://storage.googleapis.com/upload/storage/v1/b/{$bucket}/o"
             . "?uploadType=media&name={$encoded}";

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => file_get_contents($localPath),
        CURLOPT_HTTPHEADER     => [
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
    $bucket  = FIREBASE_STORAGE_BUCKET;
    $prefix  = "https://storage.googleapis.com/{$bucket}/";
    $path    = str_replace($prefix, '', $url);
    if (!$path || $path === $url) return;
    $token   = getFirebaseAccessToken();
    $encoded = rawurlencode($path);
    $ch = curl_init("https://storage.googleapis.com/storage/v1/b/{$bucket}/o/{$encoded}");
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST  => 'DELETE',
        CURLOPT_HTTPHEADER     => ['Authorization: Bearer ' . $token],
        CURLOPT_TIMEOUT        => 30,
    ]);
    curl_exec($ch);
    curl_close($ch);
}

// ── HypeFirebaseAPI class ────────────────────────────────────────────────────
class HypeFirebaseAPI {

    public function getSettings(): array {
        return $this->getDocument('settings/app') ?? [
            'monthly_working_days' => DEFAULT_WORKING_DAYS,
            'ot_rate_multiplier'   => DEFAULT_OT_MULTIPLIER,
        ];
    }

    public function getCompanyDetails(): array {
        return $this->getDocument('settings/company') ?? [
            'name'    => 'Hype Pvt Ltd',
            'address' => '',
            'email'   => SUPPORT_MAIL,
            'phone'   => '',
        ];
    }

    public function getSmtpConfig(): array {
        return $this->getDocument('settings/smtp') ?? [];
    }

    public function getActiveEmployees(): array {
        $all = $this->getCollection('employees');
        return array_values(array_filter($all, function ($e) {
            $active = $e['active'] ?? $e['is_active'] ?? true;
            return $active === true || $active === 1 || $active === '1' || $active === 'true';
        }));
    }

    public function salarySlipExists(string $employeeId, string $monthKey): bool {
        return $this->getDocument("salary/{$employeeId}_{$monthKey}") !== null;
    }

    public function getSalaryAdjustments(string $employeeId, string $monthKey): array {
        $rows = $this->getCollection('salary_adjustments');
        $bonus = $deduction = $advance = 0.0;
        foreach ($rows as $r) {
            if (($r['employee_id'] ?? '') !== $employeeId) continue;
            if (($r['month_key']   ?? '') !== $monthKey)   continue;
            $bonus     += (float)($r['bonus']     ?? 0);
            $deduction += (float)($r['deduction'] ?? 0);
            $advance   += (float)($r['advance']   ?? 0);
        }
        return compact('bonus', 'deduction', 'advance');
    }

    /**
     * getAttendanceSummary()
     *
     * Duty (first IN→OUT session per day):
     *   < 4 hrs  → Absent    (0)
     *   4–7 hrs  → Half Day  (0.5)
     *   ≥ 7 hrs  → Full Day  (1.0)
     *
     * OT (second IN→OUT session per day):
     *   < 4 hrs  → No OT      (0 OT days)
     *   4–7 hrs  → Half OT    (0.5 OT days)
     *   ≥ 7 hrs  → Full OT    (1.0 OT days)
     *
     * OT Pay = otDays × (baseSalary / workingDays) × otMultiplier
     *   — flat day rate, NOT hourly.
     *   — max 1.0 OT day per session regardless of actual hours worked.
     *
     * Sunday Rule:
     *   Saturday present AND Monday present → Sunday = Full paid holiday (1.0)
     *   Saturday present + Monday absent    → Sunday = Half paid holiday (0.5)
     *   Saturday absent  (any Monday)       → Sunday = No pay            (0.0)
     */
    public function getAttendanceSummary(string $employeeId, int $year, int $month): array {
        $sessions = $this->getCollection('sessions');
        $fullDays = $halfDays = $absentDays = $otDays = 0.0;
        $presentMap = [];

        foreach ($sessions as $s) {
            if (($s['employee_id'] ?? '') !== $employeeId) continue;
            $date = $s['date'] ?? '';
            if (!$date || substr($date, 0, 7) !== sprintf('%04d-%02d', $year, $month)) continue;

            // ── Duty session ──────────────────────────────────────────────────
            $dutyHrs = (float)($s['duty_hours'] ?? 0);
            if ($dutyHrs < DUTY_HALF_MIN_HOURS) {
                $absentDays += 1;
            } elseif ($dutyHrs < DUTY_FULL_MIN_HOURS) {
                $halfDays           += 1;
                $presentMap[$date]   = true;
            } else {
                $fullDays            += 1;
                $presentMap[$date]   = true;
            }

            // ── OT session (flat day-rate: 0 / 0.5 / 1.0) ────────────────────
            // < 4 hrs  → No OT
            // 4–7 hrs  → Half OT day (0.5)
            // ≥ 7 hrs  → Full OT day (1.0)
            // Max = 1 OT day regardless of actual hours (e.g. 12 hrs OT = 1 day)
            $otHrs = (float)($s['ot_hours'] ?? 0);
            if ($otHrs >= DUTY_FULL_MIN_HOURS) {
                $otDays += 1.0;
            } elseif ($otHrs >= OT_HALF_MIN_HOURS) {
                $otDays += 0.5;
            }
            // < 4 hrs → no OT day added
        }

        // ── Sunday Rule ───────────────────────────────────────────────────────
        $paidHolidays = 0.0;
        $daysInMonth  = cal_days_in_month(CAL_GREGORIAN, $month, $year);
        for ($day = 1; $day <= $daysInMonth; $day++) {
            $date = sprintf('%04d-%02d-%02d', $year, $month, $day);
            if ((int)date('w', strtotime($date)) !== 0) continue;

            $sat = date('Y-m-d', strtotime($date . ' -1 day'));
            $mon = date('Y-m-d', strtotime($date . ' +1 day'));
            $satPresent = isset($presentMap[$sat]);
            $monPresent = isset($presentMap[$mon]);

            if ($satPresent && $monPresent) {
                $paidHolidays += 1.0;
            } elseif ($satPresent && !$monPresent) {
                $paidHolidays += 0.5;
            }
        }

        return [
            'total_present' => $fullDays,
            'half_days'     => $halfDays,
            'absent_days'   => $absentDays,
            'paid_holidays' => $paidHolidays,
            'ot_days'       => $otDays,   // flat OT day units (0 / 0.5 / 1.0 per session)
        ];
    }

    public function uploadPdfToStorage(string $pdfPath, string $storagePath): string {
        return uploadToFirebaseStorage($pdfPath, $storagePath);
    }

    public function saveSalaryRecord(string $employeeId, string $monthKey, array $data): void {
        firebaseSet("salary/{$employeeId}_{$monthKey}", $data);
    }

    public function cleanupExpiredSlips(): int {
        $rows    = $this->getCollection('salary');
        $deleted = 0;
        $now     = time();
        foreach ($rows as $row) {
            $exp = strtotime($row['expires_at'] ?? '');
            if (!$exp || $exp > $now) continue;
            if (!empty($row['slip_url'])) {
                deleteFromFirebaseStorage($row['slip_url']);
                $deleted++;
            }
        }
        return $deleted;
    }

    private function getDocument(string $path): ?array {
        $res = firestoreRequest('GET', $path);
        if (isset($res['error']) || !isset($res['fields'])) return null;
        return fsDocToArray($res);
    }

    private function getCollection(string $collection): array {
        $res  = firestoreRequest('GET', $collection);
        $docs = [];
        foreach (($res['documents'] ?? []) as $doc) $docs[] = fsDocToArray($doc);
        return $docs;
    }
}
