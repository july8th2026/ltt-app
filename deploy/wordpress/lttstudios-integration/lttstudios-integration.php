<?php
/**
 * Plugin Name: LTT Studios Platform Integration
 * Description: Keeps marketing, legal and LTT AI Studio routes consistent.
 * Version: 1.1.0
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
        '/about.html' => '/en/about/',
        '/products.html' => '/en/products/',
        '/support.html' => '/en/faq/',
        '/contact.html' => '/en/contact/',
        '/download.html' => '/en/applications/',
        '/changelog.html' => '/en/resources/',
        '/architecture.html' => '/en/about/',
        '/transparency.html' => '/en/about/',
        '/compliance/meta.html' => '/en/privacy-policy/',
        '/compliance/tiktok.html' => '/en/privacy-policy/',
        '/legal/privacy.html' => '/en/privacy-policy/',
        '/legal/terms.html' => '/en/terms/',
        '/legal/data-deletion.html' => '/en/data-deletion/',
        '/legal/cookies.html' => '/en/privacy-policy/',
        '/legal/dpa.html' => '/en/privacy-policy/',
        '/legal/security.html' => '/en/report-abuse/',
        // Dieu khoan RIENG cua LTT VPS. Them 2026-08-26: hai alias nay DA
        // co trong `docs/lttstudios-website/route-map.json` nhung plugin
        // chua thuc hien, nen link cu toi dieu khoan VPS tra 404 tren
        // website. `test_127` bat duoc dieu do o luot pytest day du.
        '/vi/' => '/',
        '/vi/about.html' => '/gioi-thieu/',
        '/vi/products.html' => '/san-pham/',
        '/vi/support.html' => '/cau-hoi-thuong-gap/',
        '/vi/contact.html' => '/lien-he/',
        '/vi/download.html' => '/ung-dung/',
        '/vi/changelog.html' => '/tai-nguyen/',
        '/vi/architecture.html' => '/gioi-thieu/',
        '/vi/transparency.html' => '/gioi-thieu/',
        '/vi/compliance/meta.html' => '/chinh-sach-quyen-rieng-tu/',
        '/vi/compliance/tiktok.html' => '/chinh-sach-quyen-rieng-tu/',
        '/vi/legal/privacy.html' => '/chinh-sach-quyen-rieng-tu/',
        '/vi/legal/terms.html' => '/dieu-khoan-su-dung/',
        '/vi/legal/data-deletion.html' => '/xoa-du-lieu/',
        '/vi/legal/cookies.html' => '/chinh-sach-quyen-rieng-tu/',
        '/vi/legal/dpa.html' => '/chinh-sach-quyen-rieng-tu/',
        '/vi/legal/security.html' => '/bao-cao-lam-dung/',
    ];
}

add_action('template_redirect', static function (): void {
    $path = wp_parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    $map = ltt_legacy_route_map();
    if (isset($map[$path])) {
        wp_safe_redirect(home_url($map[$path]), 301, 'LTT Route Contract');
        exit;
    }
}, -100);

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
