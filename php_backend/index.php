<?php
/**
 * Hype HR Management — PHP Backend Entry Point
 * Health check + manual trigger endpoint
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

header('Content-Type: application/json');

$action = $_GET['action'] ?? $_POST['action'] ?? '';

switch ($action) {
    case 'health':
        echo json_encode([
            'status'   => 'ok',
            'app'      => APP_NAME,
            'dev'      => DEV_NAME,
            'github'   => DEV_GITHUB,
            'support'  => SUPPORT_MAIL,
            'time'     => date('Y-m-d H:i:s'),
        ]);
        break;

    case 'trigger_salary':
        // Manually trigger salary generation (admin use only)
        $secret = $_POST['secret'] ?? '';
        if ($secret !== (getenv('CRON_SECRET') ?: 'change_me_in_env')) {
            http_response_code(403);
            echo json_encode(['error' => 'Unauthorized']);
            break;
        }
        ob_start();
        require_once __DIR__ . '/cron_job.php';
        $output = ob_get_clean();
        echo json_encode(['status' => 'done', 'output' => $output]);
        break;

    default:
        echo json_encode([
            'app'     => APP_NAME,
            'version' => '1.0.0',
            'dev'     => DEV_NAME . ' | Nexuzy Lab',
            'support' => SUPPORT_MAIL,
            'github'  => DEV_GITHUB,
            'docs'    => 'See README.md for setup instructions',
        ]);
}
