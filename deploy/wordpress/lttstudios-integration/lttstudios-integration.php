<?php
/**
 * Plugin Name: LTT Studios Platform Integration
 * Description: Keeps marketing, legal and LTT AI Studio routes consistent.
 * Version: 1.0.2
 * Requires at least: 6.0
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) {
    exit;
}

const LTT_APP_ORIGIN = 'https://app.lttstudios.com';

/** Legacy static aliases. OAuth callback .html paths are intentionally absent. */
function ltt_legacy_route_map(): array {
    return [
        '/about.html' => '/about/',
        '/products.html' => '/products/',
        '/support.html' => '/faq/',
        '/contact.html' => '/contact/',
        '/download.html' => '/applications/',
        '/changelog.html' => '/resources/',
        '/architecture.html' => '/about/',
        '/transparency.html' => '/about/',
        '/compliance/meta.html' => '/privacy-policy/',
        '/compliance/tiktok.html' => '/privacy-policy/',
        '/legal/privacy.html' => '/privacy-policy/',
        '/legal/terms.html' => '/terms/',
        '/legal/data-deletion.html' => '/data-deletion/',
        '/legal/cookies.html' => '/privacy-policy/',
        '/legal/dpa.html' => '/privacy-policy/',
        '/legal/security.html' => '/report-abuse/',
        '/vi/' => '/',
        '/vi/about.html' => '/about/',
        '/vi/products.html' => '/products/',
        '/vi/support.html' => '/faq/',
        '/vi/contact.html' => '/contact/',
        '/vi/download.html' => '/applications/',
        '/vi/changelog.html' => '/resources/',
        '/vi/architecture.html' => '/about/',
        '/vi/transparency.html' => '/about/',
        '/vi/compliance/meta.html' => '/privacy-policy/',
        '/vi/compliance/tiktok.html' => '/privacy-policy/',
        '/vi/legal/privacy.html' => '/privacy-policy/',
        '/vi/legal/terms.html' => '/terms/',
        '/vi/legal/data-deletion.html' => '/data-deletion/',
        '/vi/legal/cookies.html' => '/privacy-policy/',
        '/vi/legal/dpa.html' => '/privacy-policy/',
        '/vi/legal/security.html' => '/report-abuse/',
    ];
}

add_action('template_redirect', static function (): void {
    $path = wp_parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    $map = ltt_legacy_route_map();
    if (isset($map[$path])) {
        wp_safe_redirect(home_url($map[$path]), 301, 'LTT Route Contract');
        exit;
    }
}, 0);

add_filter('login_url', static function (string $url): string {
    return LTT_APP_ORIGIN . '/login';
}, 20);

add_filter('register_url', static function (string $url): string {
    return LTT_APP_ORIGIN . '/register';
}, 20);

/* Standard WordPress links can be rewritten before the theme renders them. */
add_filter('home_url', static function (string $url, string $path): string {
    $normalized_path = '/' . trim($path, '/') . '/';
    if ($normalized_path === '/ltt-tools-ai/') {
        return LTT_APP_ORIGIN . '/';
    }
    return $url;
}, 20, 2);

/**
 * Route the custom Header V2 CTA to the app.
 *
 * LTT Core deliberately builds multilingual URLs from the raw `home` option,
 * bypassing WordPress' `home_url` filter. Limit the fallback rewrite to the
 * header CTA class so normal marketing links and content remain untouched.
 */
function ltt_rewrite_header_cta(string $html): string {
    $rewritten = preg_replace_callback(
        '/(<a\b(?=[^>]*\bltt-v2-header__cta\b)[^>]*\bhref=)(["\'])(.*?)(\2)/i',
        static function (array $matches): string {
            return $matches[1] . $matches[2] . LTT_APP_ORIGIN . '/' . $matches[4];
        },
        $html
    );

    return is_string($rewritten) ? $rewritten : $html;
}

add_action('template_redirect', static function (): void {
    if (
        is_admin()
        || wp_doing_ajax()
        || (defined('REST_REQUEST') && REST_REQUEST)
        || is_feed()
        || is_robots()
        || is_trackback()
    ) {
        return;
    }

    ob_start('ltt_rewrite_header_cta');
}, 100);

add_filter('wp_nav_menu_objects', static function (array $items): array {
    foreach ($items as $item) {
        $label = strtolower(trim(wp_strip_all_tags($item->title ?? '')));
        if (in_array($label, ['login', 'sign in'], true)) {
            $item->url = LTT_APP_ORIGIN . '/login';
        } elseif (in_array($label, ['open a tool', 'ltt tools ai'], true)) {
            $item->url = LTT_APP_ORIGIN . '/';
        } elseif (in_array($label, ['pricing', 'buy credits'], true)) {
            $item->url = LTT_APP_ORIGIN . '/nap';
        }
    }
    return $items;
}, 20);

/* Block content uses the old Tools landing URL outside WordPress menus. */
add_filter('render_block', static function (string $content): string {
    return str_replace(
        ['href="https://lttstudios.com/ltt-tools-ai/"', 'href="/ltt-tools-ai/"'],
        ['href="' . LTT_APP_ORIGIN . '/"', 'href="' . LTT_APP_ORIGIN . '/"'],
        $content
    );
}, 20);
