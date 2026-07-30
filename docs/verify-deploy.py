"""
verify-deploy.py — Sau khi deploy lttstudios-website lên hosting,
chạy script này để confirm mọi URL trả 200 + content đúng ngôn ngữ.

Usage:
    cd "C:\\Users\\Administrator\\Desktop\\BOT UP FB + TikTok\\BOT UP Facebook\\docs"
    python -X utf8 verify-deploy.py
"""
import urllib.request, urllib.error, re, sys
from collections import defaultdict

BASE = 'https://lttstudios.com'

# All URLs that should exist after deploy
URLS = {
    # EN content
    f'{BASE}/':                                 {'lang': 'en', 'must_have': ['LTT Studios', 'Bulk-publish']},
    f'{BASE}/about.html':                       {'lang': 'en', 'must_have': ['Built by creators']},
    f'{BASE}/products.html':                    {'lang': 'en', 'must_have': ['VideoBot', 'Feature breakdown']},
    f'{BASE}/support.html':                     {'lang': 'en', 'must_have': ['Frequently Asked Questions']},
    f'{BASE}/contact.html':                     {'lang': 'en', 'must_have': ['Get in touch']},
    f'{BASE}/download.html':                    {'lang': 'en', 'must_have': ['Download', 'Windows']},
    f'{BASE}/changelog.html':                   {'lang': 'en', 'must_have': ['Release history']},
    f'{BASE}/404.html':                         {'lang': 'en', 'must_have': ['404']},
    f'{BASE}/500.html':                         {'lang': 'en', 'must_have': ['500']},

    # EN legal
    f'{BASE}/legal/privacy.html':               {'lang': 'en', 'must_have': ['Privacy Policy', 'data we access']},
    f'{BASE}/legal/terms.html':                 {'lang': 'en', 'must_have': ['Terms of Service']},
    f'{BASE}/legal/data-deletion.html':         {'lang': 'en', 'must_have': ['Data Deletion', 'self-service']},
    f'{BASE}/legal/cookies.html':               {'lang': 'en', 'must_have': ['Cookie Policy']},
    f'{BASE}/legal/security.html':              {'lang': 'en', 'must_have': ['Security']},
    f'{BASE}/legal/dpa.html':                   {'lang': 'en', 'must_have': ['Data Processing Agreement']},

    # VI content
    f'{BASE}/vi/':                              {'lang': 'vi', 'must_have': ['Đăng video', 'creator']},
    f'{BASE}/vi/about.html':                    {'lang': 'vi', 'must_have': ['Câu chuyện']},
    f'{BASE}/vi/products.html':                 {'lang': 'vi', 'must_have': ['Sản phẩm', 'VideoBot']},
    f'{BASE}/vi/support.html':                  {'lang': 'vi', 'must_have': ['Câu hỏi thường gặp']},
    f'{BASE}/vi/contact.html':                  {'lang': 'vi', 'must_have': ['Liên hệ']},
    f'{BASE}/vi/download.html':                 {'lang': 'vi', 'must_have': ['Tải về', 'Windows']},
    f'{BASE}/vi/changelog.html':                {'lang': 'vi', 'must_have': ['Lịch sử release']},
    f'{BASE}/vi/404.html':                      {'lang': 'vi', 'must_have': ['Không tìm thấy']},
    f'{BASE}/vi/500.html':                      {'lang': 'vi', 'must_have': ['Lỗi server']},

    # VI legal
    f'{BASE}/vi/legal/privacy.html':            {'lang': 'vi', 'must_have': ['Quyền riêng tư']},
    f'{BASE}/vi/legal/terms.html':              {'lang': 'vi', 'must_have': ['Điều khoản Dịch vụ']},
    f'{BASE}/vi/legal/data-deletion.html':      {'lang': 'vi', 'must_have': ['Xoá Dữ liệu']},
    f'{BASE}/vi/legal/cookies.html':            {'lang': 'vi', 'must_have': ['Cookie']},
    f'{BASE}/vi/legal/security.html':           {'lang': 'vi', 'must_have': ['Bảo mật']},
    f'{BASE}/vi/legal/dpa.html':                {'lang': 'vi', 'must_have': ['Xử lý Dữ liệu']},

    # Utility (don't check content)
    f'{BASE}/auth/fb-callback.html':            {'lang': None, 'must_have': []},
    f'{BASE}/legal/callback.html':              {'lang': None, 'must_have': []},

    # Technical
    f'{BASE}/sitemap.xml':                      {'lang': None, 'must_have': ['lttstudios.com', 'urlset']},
    f'{BASE}/robots.txt':                       {'lang': None, 'must_have': ['User-agent', 'Sitemap']},
    f'{BASE}/manifest.json':                    {'lang': None, 'must_have': ['LTTStudios']},
    f'{BASE}/.well-known/security.txt':         {'lang': None, 'must_have': ['Contact:']},

    # Assets
    f'{BASE}/assets/css/main.css':              {'lang': None, 'must_have': ['--c-primary']},
    f'{BASE}/assets/js/main.js':                {'lang': None, 'must_have': ['DOMContentLoaded']},
    f'{BASE}/assets/img/favicon.svg':           {'lang': None, 'must_have': ['<svg']},
    f'{BASE}/assets/img/logo.svg':              {'lang': None, 'must_have': ['<svg']},
    f'{BASE}/assets/img/og-default.svg':        {'lang': None, 'must_have': ['<svg']},
}


def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 Chrome/120'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return 'ERR', str(e)


def main():
    print('=' * 75)
    print(f'  VERIFY DEPLOY: {BASE}')
    print('=' * 75)
    print(f'  Testing {len(URLS)} URLs...\n')

    stats = defaultdict(int)
    failures = []
    warnings = []

    for url, cfg in URLS.items():
        status, body = fetch(url)

        # 1. HTTP status check
        if status != 200:
            stats['fail'] += 1
            failures.append(f'  ❌ HTTP {status}: {url}')
            continue

        # 2. lang attribute check
        if cfg['lang']:
            m = re.search(r'<html[^>]*lang="([a-z]+)"', body)
            actual_lang = m.group(1) if m else None
            if actual_lang != cfg['lang']:
                stats['warn'] += 1
                warnings.append(f'  ⚠️  lang mismatch (expected {cfg["lang"]}, got {actual_lang}): {url}')

        # 3. content sanity check
        missing = [s for s in cfg['must_have'] if s not in body]
        if missing:
            stats['warn'] += 1
            warnings.append(f'  ⚠️  missing content {missing!r}: {url}')

        stats['ok'] += 1

    # Lang switcher roundtrip check
    print('=== Lang switcher roundtrip ===')
    rt_ok = rt_err = 0
    pairs = [
        ('/', '/vi/'),
        ('/about.html', '/vi/about.html'),
        ('/products.html', '/vi/products.html'),
        ('/support.html', '/vi/support.html'),
        ('/contact.html', '/vi/contact.html'),
        ('/legal/privacy.html', '/vi/legal/privacy.html'),
    ]
    for en, vi in pairs:
        _, en_body = fetch(BASE + en)
        m = re.search(r'<a href="(/vi/[^"]*)" hreflang="vi"', en_body)
        if not m:
            rt_err += 1
            print(f'  ❌ EN {en}: no VI link in switcher')
            continue
        vi_target = m.group(1)
        expected_vi = vi if vi != '/vi/index.html' else '/vi/'
        if vi_target.rstrip('/') != expected_vi.rstrip('/'):
            rt_err += 1
            print(f'  ❌ EN {en}: VI link is {vi_target}, expected {expected_vi}')
            continue
        _, vi_body = fetch(BASE + vi)
        m2 = re.search(r'<a href="(/[^"]*)" hreflang="en"', vi_body)
        if not m2:
            rt_err += 1
            print(f'  ❌ VI {vi}: no EN link in switcher')
            continue
        en_target = m2.group(1)
        if en_target.rstrip('/') != en.rstrip('/'):
            rt_err += 1
            print(f'  ❌ VI {vi}: EN link is {en_target}, expected {en}')
            continue
        rt_ok += 1
        print(f'  ✅ {en} ↔ {vi}')

    # Summary
    print()
    print('=' * 75)
    print(f'  SUMMARY')
    print('=' * 75)
    print(f'  URL checks: {stats["ok"]} OK, {stats["fail"]} fail, {stats["warn"]} warn')
    print(f'  Lang switcher: {rt_ok}/{rt_ok+rt_err} roundtrips OK')
    print()

    if failures:
        print('🔴 FAILURES:')
        for f in failures:
            print(f)
        print()

    if warnings:
        print(f'🟡 WARNINGS ({len(warnings)}):')
        for w in warnings[:10]:
            print(w)
        if len(warnings) > 10:
            print(f'    ... and {len(warnings)-10} more')
        print()

    if stats['fail'] == 0 and rt_err == 0:
        print('✅ DEPLOY VERIFIED — site is production-ready')
        return 0
    else:
        print('❌ DEPLOY HAS ISSUES — review failures above')
        return 1


if __name__ == '__main__':
    sys.exit(main())
