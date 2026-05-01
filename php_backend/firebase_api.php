<?php
/**
 * Hype HR Management — Firebase REST API helper
 * Uses Firebase REST API (no Admin SDK required on shared hosting).
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

/**
 * Get a Firestore document as a flat PHP array.
 */
function firebase_get_document(string $docPath): array {
    $url = "https://firestore.googleapis.com/v1/projects/" . FIREBASE_PROJECT_ID
         . "/databases/(default)/documents/{$docPath}?key=" . FIREBASE_API_KEY;
    $raw = @file_get_contents($url);
    if (!$raw) return [];
    $data = json_decode($raw, true);
    return firestore_fields_to_array($data['fields'] ?? []);
}

/**
 * Set / update a Firestore document.
 */
function firebase_set_document(string $docPath, array $fields): bool {
    $url = "https://firestore.googleapis.com/v1/projects/" . FIREBASE_PROJECT_ID
         . "/databases/(default)/documents/{$docPath}?key=" . FIREBASE_API_KEY;
    $body = json_encode(['fields' => array_to_firestore_fields($fields)]);
    $ctx  = stream_context_create(['http' => [
        'method'  => 'PATCH',
        'header'  => "Content-Type: application/json\r\n",
        'content' => $body,
        'ignore_errors' => true,
    ]]);
    $result = @file_get_contents($url, false, $ctx);
    return $result !== false;
}

/**
 * Query a Firestore collection with a single whereEqualTo filter.
 */
function firebase_query_collection(string $collection, string $field, $value): array {
    $url = "https://firestore.googleapis.com/v1/projects/" . FIREBASE_PROJECT_ID
         . "/databases/(default)/documents:runQuery?key=" . FIREBASE_API_KEY;

    $fType = is_bool($value) ? 'booleanValue' : (is_int($value)||is_float($value) ? 'doubleValue' : 'stringValue');

    $query = [
        'structuredQuery' => [
            'from'  => [['collectionId' => $collection]],
            'where' => ['fieldFilter' => [
                'field' => ['fieldPath' => $field],
                'op'    => 'EQUAL',
                'value' => [$fType => $value],
            ]],
        ],
    ];
    $ctx = stream_context_create(['http' => [
        'method'  => 'POST',
        'header'  => "Content-Type: application/json\r\n",
        'content' => json_encode($query),
        'ignore_errors' => true,
    ]]);
    $raw = @file_get_contents($url, false, $ctx);
    if (!$raw) return [];
    $results = json_decode($raw, true);
    $docs = [];
    foreach ((array)$results as $item) {
        if (isset($item['document']['fields'])) {
            $docs[] = firestore_fields_to_array($item['document']['fields']);
        }
    }
    return $docs;
}

/**
 * Upload file to Firebase Storage via REST.
 */
function upload_to_firebase_storage(string $localPath, string $storagePath): ?string {
    if (!file_exists($localPath)) return null;
    $bucket  = FIREBASE_PROJECT_ID . '.appspot.com';
    $encoded = rawurlencode($storagePath);
    $url     = "https://storage.googleapis.com/upload/storage/v1/b/{$bucket}/o?uploadType=media&name={$encoded}&key=" . FIREBASE_API_KEY;
    $content = file_get_contents($localPath);
    $ctx = stream_context_create(['http' => [
        'method'  => 'POST',
        'header'  => "Content-Type: application/pdf\r\nContent-Length: " . strlen($content) . "\r\n",
        'content' => $content,
        'ignore_errors' => true,
    ]]);
    $raw  = @file_get_contents($url, false, $ctx);
    $data = json_decode($raw, true);
    if (empty($data['name'])) return null;
    return "https://storage.googleapis.com/" . $bucket . "/" . rawurlencode($data['name']) . "?alt=media";
}

// ─────────── Firestore field conversion helpers ─────────────
function firestore_fields_to_array(array $fields): array {
    $result = [];
    foreach ($fields as $key => $val) {
        $result[$key] = array_values($val)[0];
    }
    return $result;
}
function array_to_firestore_fields(array $data): array {
    $fields = [];
    foreach ($data as $key => $value) {
        if (is_bool($value))              $fields[$key] = ['booleanValue' => $value];
        elseif (is_int($value)||is_float($value)) $fields[$key] = ['doubleValue' => $value];
        elseif (is_null($value))          $fields[$key] = ['nullValue' => null];
        else                              $fields[$key] = ['stringValue' => (string)$value];
    }
    return $fields;
}
