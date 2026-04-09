<?php
/**
 * Hype HR Management — Firebase REST API Helper
 * Uses Firebase REST API + Service Account JWT for server-side operations
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

// ─── Auth: Generate Firebase Access Token via Service Account ────────────────────
function getFirebaseAccessToken(): string {
    static $cachedToken = null;
    static $tokenExpiry = 0;

    if ($cachedToken && time() < $tokenExpiry - 60) {
        return $cachedToken;
    }

    $serviceAccount = json_decode(file_get_contents(SERVICE_ACCOUNT_PATH), true);
    $now     = time();
    $payload = [
        'iss'   => $serviceAccount['client_email'],
        'scope' => 'https://www.googleapis.com/auth/datastore https://www.googleapis.com/auth/devstorage.full_control',
        'aud'   => 'https://oauth2.googleapis.com/token',
        'iat'   => $now,
        'exp'   => $now + 3600,
    ];

    $header    = base64UrlEncode(json_encode(['alg' => 'RS256', 'typ' => 'JWT']));
    $claims    = base64UrlEncode(json_encode($payload));
    $signature = '';
    openssl_sign("$header.$claims", $signature, $serviceAccount['private_key'], 'SHA256');
    $jwt = "$header.$claims." . base64UrlEncode($signature);

    $ch = curl_init('https://oauth2.googleapis.com/token');
    curl_setopt_array($ch, [
        CURLOPT_POST       => true,
        CURLOPT_POSTFIELDS => http_build_query([
            'grant_type' => 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion'  => $jwt,
        ]),
        CURLOPT_RETURNTRANSFER => true,
    ]);
    $response = json_decode(curl_exec($ch), true);
    curl_close($ch);

    $cachedToken = $response['access_token'] ?? '';
    $tokenExpiry = $now + (int)($response['expires_in'] ?? 3600);
    return $cachedToken;
}

function base64UrlEncode(string $data): string {
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

// ─── Firestore helpers ──────────────────────────────────────────────────
function firestoreUrl(string $path): string {
    return 'https://firestore.googleapis.com/v1/projects/' .
           FIREBASE_PROJECT_ID . '/databases/(default)/documents/' . $path;
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
    ];
    if ($body) {
        $opts[CURLOPT_POSTFIELDS] = json_encode($body);
    }
    curl_setopt_array($ch, $opts);
    $result = curl_exec($ch);
    curl_close($ch);
    return json_decode($result, true);
}

function firestoreDocToArray(array $doc): array {
    $out = [];
    foreach ($doc['fields'] ?? [] as $key => $val) {
        $out[$key] = firestoreValue($val);
    }
    return $out;
}

function firestoreValue(array $val): mixed {
    if (isset($val['stringValue']))    return $val['stringValue'];
    if (isset($val['integerValue']))   return (int)$val['integerValue'];
    if (isset($val['doubleValue']))    return (float)$val['doubleValue'];
    if (isset($val['booleanValue']))   return (bool)$val['booleanValue'];
    if (isset($val['nullValue']))      return null;
    if (isset($val['arrayValue']))     return array_map('firestoreValue', $val['arrayValue']['values'] ?? []);
    if (isset($val['mapValue']))       return firestoreDocToArray($val['mapValue']);
    return null;
}

function arrayToFirestoreFields(array $data): array {
    $fields = [];
    foreach ($data as $key => $value) {
        $fields[$key] = phpToFirestoreValue($value);
    }
    return ['fields' => $fields];
}

function phpToFirestoreValue(mixed $value): array {
    if (is_null($value))    return ['nullValue' => null];
    if (is_bool($value))    return ['booleanValue' => $value];
    if (is_int($value))     return ['integerValue' => (string)$value];
    if (is_float($value))   return ['doubleValue' => $value];
    if (is_string($value))  return ['stringValue' => $value];
    if (is_array($value) && array_is_list($value)) {
        return ['arrayValue' => ['values' => array_map('phpToFirestoreValue', $value)]];
    }
    if (is_array($value)) {
        $fields = [];
        foreach ($value as $k => $v) $fields[$k] = phpToFirestoreValue($v);
        return ['mapValue' => ['fields' => $fields]];
    }
    return ['stringValue' => (string)$value];
}

function firebaseGet(string $path): ?array {
    $result = firestoreRequest('GET', $path);
    if (isset($result['error']) || !isset($result['fields'])) return null;
    return firestoreDocToArray($result);
}

function firebaseSet(string $path, array $data): void {
    firestoreRequest('PATCH', $path, arrayToFirestoreFields($data));
}

function firebaseUpdate(string $path, array $data): void {
    $fields = array_keys($data);
    $mask   = implode('&', array_map(fn($f) => "updateMask.fieldPaths=$f", $fields));
    $token  = getFirebaseAccessToken();
    $ch     = curl_init(firestoreUrl($path) . '?' . $mask);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST  => 'PATCH',
        CURLOPT_POSTFIELDS     => json_encode(arrayToFirestoreFields($data)),
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . $token,
            'Content-Type: application/json',
        ],
    ]);
    curl_exec($ch);
    curl_close($ch);
}

function firebaseQuery(string $collection, array $conditions = []): array {
    $filters = [];
    foreach ($conditions as [$field, $op, $value]) {
        $opMap = ['==' => 'EQUAL', '>=' => 'GREATER_THAN_OR_EQUAL', '<=' => 'LESS_THAN_OR_EQUAL',
                  '>' => 'GREATER_THAN', '<' => 'LESS_THAN'];
        $filters[] = [
            'fieldFilter' => [
                'field'  => ['fieldPath' => $field],
                'op'     => $opMap[$op] ?? 'EQUAL',
                'value'  => phpToFirestoreValue($value),
            ]
        ];
    }

    $query = ['structuredQuery' => [
        'from'  => [['collectionId' => $collection]],
        'where' => count($filters) === 1
            ? $filters[0]
            : ['compositeFilter' => ['op' => 'AND', 'filters' => $filters]],
    ]];

    $token  = getFirebaseAccessToken();
    $ch     = curl_init('https://firestore.googleapis.com/v1/projects/' .
                         FIREBASE_PROJECT_ID . '/databases/(default)/documents:runQuery');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => json_encode($query),
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . $token,
            'Content-Type: application/json',
        ],
    ]);
    $results = json_decode(curl_exec($ch), true) ?? [];
    curl_close($ch);

    $out = [];
    foreach ($results as $r) {
        if (isset($r['document']['fields'])) {
            $out[] = firestoreDocToArray($r['document']);
        }
    }
    return $out;
}

function uploadToFirebaseStorage(string $localPath, string $remotePath): string {
    $token  = getFirebaseAccessToken();
    $bucket = FIREBASE_STORAGE_BUCKET;
    $encoded = rawurlencode($remotePath);
    $url    = "https://storage.googleapis.com/upload/storage/v1/b/{$bucket}/o?uploadType=media&name={$encoded}";

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => file_get_contents($localPath),
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . $token,
            'Content-Type: application/pdf',
        ],
    ]);
    $result = json_decode(curl_exec($ch), true);
    curl_close($ch);

    $objectName = rawurlencode($remotePath);
    $aclUrl     = "https://storage.googleapis.com/storage/v1/b/{$bucket}/o/{$objectName}/acl";
    $aclCh      = curl_init($aclUrl);
    curl_setopt_array($aclCh, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => json_encode(['entity' => 'allUsers', 'role' => 'READER']),
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . $token,
            'Content-Type: application/json',
        ],
    ]);
    curl_exec($aclCh);
    curl_close($aclCh);

    return "https://storage.googleapis.com/{$bucket}/{$remotePath}";
}

function deleteFromFirebaseStorage(string $url): void {
    $token  = getFirebaseAccessToken();
    $bucket = FIREBASE_STORAGE_BUCKET;
    $path   = str_replace("https://storage.googleapis.com/{$bucket}/", '', $url);
    $encoded = rawurlencode($path);
    $ch = curl_init("https://storage.googleapis.com/storage/v1/b/{$bucket}/o/{$encoded}");
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST  => 'DELETE',
        CURLOPT_HTTPHEADER     => ['Authorization: Bearer ' . $token],
    ]);
    curl_exec($ch);
    curl_close($ch);
}
