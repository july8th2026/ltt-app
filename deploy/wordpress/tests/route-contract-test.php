<?php

declare(strict_types=1);

define('ABSPATH', __DIR__ . '/');
$registered_actions = [];

function add_action(string $hook, callable $callback, int $priority = 10, int $accepted_args = 1): void
{
    global $registered_actions;
    $registered_actions[] = compact('hook', 'priority', 'accepted_args');
}

function add_filter(string $hook, callable $callback, int $priority = 10, int $accepted_args = 1): void
{
    add_action($hook, $callback, $priority, $accepted_args);
}

require dirname(__DIR__) . '/lttstudios-integration/lttstudios-integration.php';

$contract_path = dirname(__DIR__, 3) . '/docs/lttstudios-website/route-map.json';
$contract = json_decode((string) file_get_contents($contract_path), true, 512, JSON_THROW_ON_ERROR);
$expected = [];
foreach ($contract['rules'] as $rule) {
    if (in_array($rule['disposition'], ['redirect', 'locale_fallback'], true)) {
        $expected[$rule['source']] = $rule['production'];
    }
}

$actual = ltt_legacy_route_map();
$failures = [];
if ($actual !== $expected) {
    $failures[] = 'Plugin aliases do not exactly match route-map.json.';
}
foreach (['/auth/fb-callback.html', '/legal/callback.html'] as $callback) {
    if (isset($actual[$callback])) {
        $failures[] = "OAuth callback {$callback} must not be redirected.";
    }
}
$route_priorities = [];
foreach ($registered_actions as $action) {
    if ($action['hook'] === 'template_redirect') {
        $route_priorities[] = $action['priority'];
    }
}
if (! in_array(-100, $route_priorities, true)) {
    $failures[] = 'Legacy aliases do not run before the retired /vi/ prefix redirect.';
}

echo json_encode([
    'status' => $failures === [] ? 'pass' : 'fail',
    'aliases' => count($actual),
    'oauth_callbacks_excluded' => true,
    'failures' => $failures,
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;

exit($failures === [] ? 0 : 1);
