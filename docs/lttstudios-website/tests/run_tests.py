#!/usr/bin/env python3
"""
LTTStudios Website — Comprehensive Test Suite

Tests 13 categories of website behavior. Runnable in 2 modes:
  Local mode:  Test files on disk (default — fast, run before deploy)
  Live mode:   Test deployed URLs (--live — run after deploy to verify production)

Usage:
    cd docs/lttstudios-website
    python -X utf8 tests/run_tests.py              # local mode
    python -X utf8 tests/run_tests.py --live       # live mode against lttstudios.com
    python -X utf8 tests/run_tests.py --live --base https://staging.lttstudios.com
    python -X utf8 tests/run_tests.py --verbose    # show all passing tests too
    python -X utf8 tests/run_tests.py --category seo  # run only SEO tests

Exit code 0 if all pass, 1 if any fail.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


# ── Config ──────────────────────────────────────────────────────────────────

BASE_URL_DEFAULT = 'https://lttstudios.com'
ROOT = Path(__file__).parent.parent.resolve()

UTIL_PAGES = {
    'auth/fb-callback.html',
    'legal/callback.html',
    '500.html',
    'vi/500.html',
}

NO_CSS_PAGES = {'auth/fb-callback.html', 'legal/callback.html'}
NO_JS_PAGES  = NO_CSS_PAGES | {'500.html', 'vi/500.html'}
NO_LANG_SWITCHER = UTIL_PAGES
NO_HREFLANG = UTIL_PAGES.copy()

# Intentional .top references (historical migration record)
INTENTIONAL_TOP_REFS = {'changelog.html', 'vi/changelog.html'}

# Required emails (anything else flagged as suspicious)
KNOWN_EMAILS = {
    'support@lttstudios.com', 'security@lttstudios.com',
    'licensing@lttstudios.com', 'akakenly.design@gmail.com',
    'letammeiu@gmail.com',
}


# ── Test framework ──────────────────────────────────────────────────────────

class TestResult:
    PASS = 'PASS'
    FAIL = 'FAIL'
    SKIP = 'SKIP'

class TestCase:
    def __init__(self, category: str, name: str):
        self.category = category
        self.name = name
        self.result = TestResult.PASS
        self.message = ''
        self.details: list[str] = []

    def fail(self, msg: str):
        self.result = TestResult.FAIL
        self.message = msg

    def add_detail(self, d: str):
        self.details.append(d)


class TestRunner:
    def __init__(self, mode: str, base_url: str, verbose: bool, category_filter: str | None):
        self.mode = mode
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.category_filter = category_filter
        self.results: list[TestCase] = []
        self.start_time = time.time()
        self._file_cache: dict[str, str] = {}
        self._all_files: set[str] = set()
        self._url_cache: dict[str, tuple[int, str]] = {}

        # Collect files for local mode
        for root, _, files in os.walk(ROOT):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), ROOT).replace(os.sep, '/')
                if not rel.startswith('tests/'):
                    self._all_files.add(rel)

    def add(self, tc: TestCase):
        self.results.append(tc)

    def has_file(self, rel: str) -> bool:
        return rel in self._all_files

    def read(self, rel: str) -> str:
        if rel not in self._file_cache:
            fp = ROOT / rel
            if not fp.exists():
                return ''
            self._file_cache[rel] = fp.read_text(encoding='utf-8', errors='replace')
        return self._file_cache[rel]

    def fetch(self, url: str) -> tuple[int, str]:
        if url in self._url_cache:
            return self._url_cache[url]
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'LTTStudios-TestRunner/1.0',
                'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            })
            with urllib.request.urlopen(req, timeout=12) as r:
                result = (r.status, r.read().decode('utf-8', errors='replace'))
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode('utf-8', errors='replace')
            except Exception:
                body = ''
            result = (e.code, body)
        except Exception as e:
            result = (0, str(e))
        self._url_cache[url] = result
        return result

    def get_html(self, rel: str) -> str | None:
        """Get HTML content for a page either from disk (local mode) or HTTP (live mode)."""
        if self.mode == 'local':
            if not self.has_file(rel):
                return None
            return self.read(rel)
        else:
            url = self.base_url + '/' + rel
            # / for index.html, /vi/ for vi/index.html
            if rel == 'index.html':
                url = self.base_url + '/'
            elif rel == 'vi/index.html':
                url = self.base_url + '/vi/'
            status, body = self.fetch(url)
            return body if status == 200 else None

    def category_pages(self) -> list[str]:
        """List all HTML pages (excluding assets)."""
        return sorted(f for f in self._all_files
                      if f.endswith('.html') and not f.startswith('assets/'))

    def should_run(self, category: str) -> bool:
        if not self.category_filter:
            return True
        return category.lower().startswith(self.category_filter.lower())


# ── Categories ──────────────────────────────────────────────────────────────

def cat_1_structure(r: TestRunner):
    """[1] FILE STRUCTURE — required files exist."""
    required = [
        'index.html', 'about.html', 'products.html', 'support.html',
        'contact.html', 'download.html', 'changelog.html',
        '404.html', '500.html', 'robots.txt', 'sitemap.xml',
        'manifest.json', '.well-known/security.txt',
        'auth/fb-callback.html',
        'legal/privacy.html', 'legal/terms.html', 'legal/data-deletion.html',
        'legal/cookies.html', 'legal/security.html', 'legal/dpa.html',
        'legal/callback.html',
        'vi/index.html', 'vi/about.html', 'vi/products.html', 'vi/support.html',
        'vi/contact.html', 'vi/download.html', 'vi/changelog.html',
        'vi/404.html', 'vi/500.html',
        'vi/legal/privacy.html', 'vi/legal/terms.html',
        'vi/legal/data-deletion.html', 'vi/legal/cookies.html',
        'vi/legal/security.html', 'vi/legal/dpa.html',
        'assets/css/main.css', 'assets/js/main.js',
        'assets/img/favicon.svg', 'assets/img/logo.svg',
        'assets/img/og-default.svg',
        # Phase 2 trust pages
        'architecture.html', 'vi/architecture.html',
        'compliance/meta.html', 'vi/compliance/meta.html',
        'compliance/tiktok.html', 'vi/compliance/tiktok.html',
        'transparency.html', 'vi/transparency.html',
    ]
    for fp in required:
        tc = TestCase('1.STRUCTURE', f'file exists: {fp}')
        if not r.has_file(fp):
            tc.fail(f'missing required file: {fp}')
        r.add(tc)


def cat_2_html_validity(r: TestRunner):
    """[2] HTML VALIDITY — DOCTYPE, lang, paired tags."""
    for fp in r.category_pages():
        tc = TestCase('2.HTML', f'valid HTML: {fp}')
        c = r.read(fp)
        if not c.startswith('<!DOCTYPE html>'):
            tc.fail('missing DOCTYPE')
        elif '<html lang=' not in c:
            tc.fail('missing <html lang>')
        elif c.count('<body>') != 1 or c.count('</body>') != 1:
            tc.fail(f'body tag count mismatch (open={c.count("<body>")} close={c.count("</body>")})')
        elif c.count('<div') != c.count('</div>'):
            tc.fail(f'div mismatch (open={c.count("<div")} close={c.count("</div>")})')
        elif c.count('<section') != c.count('</section>'):
            tc.fail(f'section mismatch')
        r.add(tc)


def cat_3_meta_tags(r: TestRunner):
    """[3] META TAGS — title, description, og, canonical."""
    for fp in r.category_pages():
        c = r.read(fp)

        tc = TestCase('3.META', f'title present: {fp}')
        m = re.search(r'<title>([^<]+)</title>', c)
        if not m:
            tc.fail('no <title>')
        elif len(m.group(1)) > 70:
            tc.fail(f'title too long ({len(m.group(1))} chars > 70)')
        elif len(m.group(1)) < 10:
            tc.fail(f'title too short')
        r.add(tc)

        tc = TestCase('3.META', f'description: {fp}')
        m = re.search(r'<meta name="description" content="([^"]+)"', c)
        if not m:
            tc.fail('no meta description')
        elif len(m.group(1)) > 165:
            tc.fail(f'description too long ({len(m.group(1))} chars > 165)')
        r.add(tc)

        if fp not in UTIL_PAGES and fp not in ('500.html', 'vi/500.html'):
            tc = TestCase('3.META', f'canonical: {fp}')
            if '<link rel="canonical"' not in c:
                tc.fail('no canonical')
            r.add(tc)

            tc = TestCase('3.META', f'og:title: {fp}')
            if 'og:title' not in c and fp not in ('404.html', 'vi/404.html'):
                tc.fail('no og:title')
            r.add(tc)


def cat_4_html_lang(r: TestRunner):
    """[4] HTML LANG attribute matches folder."""
    for fp in r.category_pages():
        tc = TestCase('4.LANG', f'<html lang>: {fp}')
        c = r.read(fp)
        expected = 'vi' if fp.startswith('vi/') else 'en'
        if f'<html lang="{expected}">' not in c:
            tc.fail(f'expected lang="{expected}"')
        r.add(tc)


def cat_5_internal_links(r: TestRunner):
    """[5] INTERNAL LINKS — all hrefs resolve."""
    for fp in r.category_pages():
        c = r.read(fp)
        broken = []
        for href in re.findall(r'href="(/[^"#?]*)"', c):
            t = href.lstrip('/').rstrip('/')
            if not t: t = 'index.html'
            elif not t.endswith('.html') and '.' not in os.path.basename(t):
                t += '/index.html'
            if t not in r._all_files:
                broken.append(href)
        tc = TestCase('5.LINKS', f'links resolve: {fp}')
        if broken:
            tc.fail(f'{len(broken)} broken: {broken[:3]}')
        r.add(tc)


def cat_6_assets(r: TestRunner):
    """[6] ASSETS — CSS/JS/images exist + correctly referenced."""
    for fp in r.category_pages():
        c = r.read(fp)

        tc = TestCase('6.ASSETS', f'CSS loads: {fp}')
        if fp not in NO_CSS_PAGES and 'href="/assets/css/main.css"' not in c:
            tc.fail('not loading main.css')
        r.add(tc)

        tc = TestCase('6.ASSETS', f'JS loads: {fp}')
        if fp not in NO_JS_PAGES and 'src="/assets/js/main.js"' not in c:
            tc.fail('not loading main.js')
        r.add(tc)

        # Verify all referenced assets exist
        broken = []
        for ref in re.findall(r'(?:src|href)="(/assets/[^"]+)"', c):
            if ref.lstrip('/') not in r._all_files:
                broken.append(ref)
        tc = TestCase('6.ASSETS', f'asset refs valid: {fp}')
        if broken:
            tc.fail(f'broken refs: {broken[:3]}')
        r.add(tc)


def cat_7_hreflang(r: TestRunner):
    """[7] HREFLANG — proper bilingual alternates."""
    for fp in r.category_pages():
        if fp in NO_HREFLANG: continue
        c = r.read(fp)

        tc = TestCase('7.HREFLANG', f'hreflang present: {fp}')
        m_en = re.search(r'<link rel="alternate" hreflang="en" href="([^"]+)"', c)
        m_vi = re.search(r'<link rel="alternate" hreflang="vi" href="([^"]+)"', c)
        if not m_en or not m_vi:
            tc.fail(f'missing hreflang ({"en" if not m_en else ""}{"vi" if not m_vi else ""})')
            r.add(tc)
            continue

        # Verify counterpart URL is correct
        base = fp[3:] if fp.startswith('vi/') else fp
        if base == 'index.html': base = ''
        exp_en = f'https://lttstudios.com/{base}' if base else 'https://lttstudios.com/'
        exp_vi = f'https://lttstudios.com/vi/{base}' if base else 'https://lttstudios.com/vi/'
        if m_en.group(1).rstrip('/') != exp_en.rstrip('/'):
            tc.fail(f'en URL wrong: {m_en.group(1)} (expected {exp_en})')
        elif m_vi.group(1).rstrip('/') != exp_vi.rstrip('/'):
            tc.fail(f'vi URL wrong: {m_vi.group(1)} (expected {exp_vi})')
        r.add(tc)


def cat_8_lang_switcher(r: TestRunner):
    """[8] LANG SWITCHER — present in nav + roundtrip works."""
    en_pages = [p for p in r.category_pages() if not p.startswith('vi/')]
    for en_fp in en_pages:
        if en_fp in NO_LANG_SWITCHER: continue

        tc = TestCase('8.SWITCHER', f'EN→VI roundtrip: {en_fp}')
        c = r.read(en_fp)
        nm = re.search(r'<nav class="nav-main"[^>]*>(.*?)</nav>', c, re.DOTALL)
        if not nm:
            tc.fail('no <nav class="nav-main">')
            r.add(tc); continue
        if 'lang-switch' not in nm.group(1):
            tc.fail('no lang-switch inside nav')
            r.add(tc); continue
        m = re.search(r'<a href="(/vi/[^"]*)" hreflang="vi"', c)
        if not m:
            tc.fail('no VI link in switcher')
            r.add(tc); continue
        vi_target = m.group(1).lstrip('/')
        if vi_target.endswith('/') or vi_target == 'vi':
            vi_target = vi_target.rstrip('/') + '/index.html'
        if vi_target not in r._all_files:
            tc.fail(f'VI link target missing: /{vi_target}')
            r.add(tc); continue

        # Now check VI page points back to EN
        vc = r.read(vi_target)
        m2 = re.search(r'<a href="(/[^"]*)" hreflang="en"', vc)
        if not m2:
            tc.fail(f'{vi_target}: no EN link back')
            r.add(tc); continue
        en_back = m2.group(1).lstrip('/')
        if not en_back: en_back = 'index.html'
        if en_back != en_fp:
            tc.fail(f'roundtrip mismatch: {en_fp}→/{vi_target}→/{en_back}')
        r.add(tc)


def cat_9_schema(r: TestRunner):
    """[9] SCHEMA.ORG JSON-LD validity."""
    for fp in r.category_pages():
        c = r.read(fp)
        for i, m in enumerate(re.finditer(
                r'<script type="application/ld\+json">(.*?)</script>', c, re.DOTALL)):
            tc = TestCase('9.SCHEMA', f'JSON-LD #{i+1}: {fp}')
            try:
                json.loads(m.group(1))
            except json.JSONDecodeError as e:
                tc.fail(f'invalid JSON: {e}')
            r.add(tc)


def cat_10_sitemap_robots(r: TestRunner):
    """[10] SITEMAP + ROBOTS — XML validity, all URLs exist."""
    tc = TestCase('10.SEO', 'sitemap.xml valid XML')
    if not r.has_file('sitemap.xml'):
        tc.fail('sitemap.xml missing'); r.add(tc); return
    try:
        tree = ET.fromstring(r.read('sitemap.xml'))
        urls = tree.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')
    except ET.ParseError as e:
        tc.fail(f'XML parse error: {e}'); r.add(tc); return
    r.add(tc)

    # All sitemap URLs map to files
    for u in urls:
        loc = u.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
        path = loc.replace('https://lttstudios.com/', '').rstrip('/')
        if not path: path = 'index.html'
        if not path.endswith('.html') and '.' not in os.path.basename(path):
            path += '/index.html'
        tc = TestCase('10.SEO', f'sitemap URL exists: {loc}')
        if path not in r._all_files:
            tc.fail(f'404 file: {path}')
        r.add(tc)

    tc = TestCase('10.SEO', 'robots.txt present')
    if not r.has_file('robots.txt'):
        tc.fail('missing')
    else:
        rc = r.read('robots.txt')
        if 'Sitemap:' not in rc:
            tc.fail('no Sitemap: directive')
        if 'User-agent' not in rc:
            tc.fail('no User-agent directive')
    r.add(tc)


def cat_11_manifest_security(r: TestRunner):
    """[11] MANIFEST.JSON + SECURITY.TXT."""
    tc = TestCase('11.PWA', 'manifest.json valid JSON')
    if r.has_file('manifest.json'):
        try:
            m = json.loads(r.read('manifest.json'))
            for k in ['name', 'short_name', 'start_url', 'display', 'icons']:
                if k not in m:
                    tc.fail(f'missing key: {k}')
                    break
        except json.JSONDecodeError as e:
            tc.fail(f'parse error: {e}')
    else:
        tc.fail('missing')
    r.add(tc)

    tc = TestCase('11.PWA', 'security.txt RFC 9116 compliant')
    if r.has_file('.well-known/security.txt'):
        sc = r.read('.well-known/security.txt')
        for required in ['Contact:', 'Expires:']:
            if required not in sc:
                tc.fail(f'missing: {required}')
                break
    else:
        tc.fail('missing')
    r.add(tc)


def cat_12_brand_consistency(r: TestRunner):
    """[12] BRAND — emails, names, dates consistent."""
    bad_brand = ['LtTStudios', 'lttSTUDIOS', 'ltt studios', 'LTT_STUDIOS']
    for fp in r.category_pages():
        c = r.read(fp)
        tc = TestCase('12.BRAND', f'brand name capitalization: {fp}')
        for bad in bad_brand:
            if bad in c:
                tc.fail(f'typo found: "{bad}"')
                break
        r.add(tc)

        tc = TestCase('12.BRAND', f'no unknown emails: {fp}')
        emails = set(re.findall(r'[\w.+-]+@[\w-]+\.\w+', c))
        unknown = [e for e in emails
                   if e not in KNOWN_EMAILS
                   and 'example' not in e
                   and 'reviewer-test' not in e]
        if unknown:
            tc.fail(f'unknown: {unknown[:3]}')
        r.add(tc)


def cat_13_accessibility(r: TestRunner):
    """[13] ACCESSIBILITY — aria, alt."""
    for fp in r.category_pages():
        c = r.read(fp)

        tc = TestCase('13.A11Y', f'nav-toggle aria-label: {fp}')
        if 'nav-toggle' in c:
            idx = c.find('nav-toggle')
            if 'aria-label' not in c[idx:idx+300]:
                tc.fail('nav-toggle missing aria-label')
        r.add(tc)

        tc = TestCase('13.A11Y', f'images have alt: {fp}')
        for m in re.finditer(r'<img[^>]+>', c):
            if 'alt=' not in m.group():
                tc.fail(f'<img> missing alt: {m.group()[:60]}')
                break
        r.add(tc)


def cat_14_stale_refs(r: TestRunner):
    """[14] STALE — no leftover .top references (except changelog history)."""
    for fp in r._all_files:
        if not fp.endswith(('.html', '.txt', '.xml', '.json', '.css', '.js')):
            continue
        if fp in INTENTIONAL_TOP_REFS:
            continue
        try:
            c = (ROOT / fp).read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        tc = TestCase('14.STALE', f'no .top refs: {fp}')
        if 'lttstudio.top' in c:
            tc.fail(f'contains lttstudio.top')
        r.add(tc)


def cat_15_content_parity(r: TestRunner):
    """[15] CONTENT PARITY — VI pages ≥ 40% size of EN counterpart."""
    en_pages = [p for p in r.category_pages() if not p.startswith('vi/')]
    en_sizes = {p: len(r.read(p)) for p in en_pages if p not in UTIL_PAGES}

    for vi_fp in r.category_pages():
        if not vi_fp.startswith('vi/') or vi_fp in UTIL_PAGES:
            continue
        en_fp = vi_fp[3:]
        if en_fp not in en_sizes:
            continue
        en_sz = en_sizes[en_fp]
        vi_sz = len(r.read(vi_fp))
        tc = TestCase('15.PARITY', f'VI content ≥40%: {vi_fp}')
        if vi_sz < en_sz * 0.4:
            tc.fail(f'VI {vi_sz}B vs EN {en_sz}B ({vi_sz/en_sz:.0%})')
        r.add(tc)


def cat_16_live_urls(r: TestRunner):
    """[16] LIVE URL TESTS — only in --live mode. HTTP 200, correct lang."""
    if r.mode != 'live':
        return
    test_urls = [
        (f'{r.base_url}/', 'en'),
        (f'{r.base_url}/about.html', 'en'),
        (f'{r.base_url}/products.html', 'en'),
        (f'{r.base_url}/support.html', 'en'),
        (f'{r.base_url}/contact.html', 'en'),
        (f'{r.base_url}/download.html', 'en'),
        (f'{r.base_url}/changelog.html', 'en'),
        (f'{r.base_url}/404.html', 'en'),
        (f'{r.base_url}/legal/privacy.html', 'en'),
        (f'{r.base_url}/legal/terms.html', 'en'),
        (f'{r.base_url}/legal/data-deletion.html', 'en'),
        (f'{r.base_url}/legal/cookies.html', 'en'),
        (f'{r.base_url}/legal/security.html', 'en'),
        (f'{r.base_url}/legal/dpa.html', 'en'),
        (f'{r.base_url}/vi/', 'vi'),
        (f'{r.base_url}/vi/about.html', 'vi'),
        (f'{r.base_url}/vi/products.html', 'vi'),
        (f'{r.base_url}/vi/legal/privacy.html', 'vi'),
        (f'{r.base_url}/vi/legal/data-deletion.html', 'vi'),
        (f'{r.base_url}/sitemap.xml', None),
        (f'{r.base_url}/robots.txt', None),
        (f'{r.base_url}/manifest.json', None),
        (f'{r.base_url}/assets/css/main.css', None),
        (f'{r.base_url}/assets/js/main.js', None),
    ]
    for url, lang in test_urls:
        tc = TestCase('16.LIVE', f'GET {url}')
        status, body = r.fetch(url)
        if status != 200:
            tc.fail(f'HTTP {status}')
            r.add(tc); continue
        if lang:
            m = re.search(r'<html[^>]*lang="([a-z]+)"', body)
            if not m or m.group(1) != lang:
                tc.fail(f'lang attribute mismatch (expected {lang}, got {m.group(1) if m else "none"})')
        r.add(tc)


# ── Runner ──────────────────────────────────────────────────────────────────

CATEGORIES = [
    ('1', cat_1_structure),
    ('2', cat_2_html_validity),
    ('3', cat_3_meta_tags),
    ('4', cat_4_html_lang),
    ('5', cat_5_internal_links),
    ('6', cat_6_assets),
    ('7', cat_7_hreflang),
    ('8', cat_8_lang_switcher),
    ('9', cat_9_schema),
    ('10', cat_10_sitemap_robots),
    ('11', cat_11_manifest_security),
    ('12', cat_12_brand_consistency),
    ('13', cat_13_accessibility),
    ('14', cat_14_stale_refs),
    ('15', cat_15_content_parity),
    ('16', cat_16_live_urls),
]


def main():
    p = argparse.ArgumentParser(description='LTTStudios website test suite')
    p.add_argument('--live', action='store_true',
                   help='Test live URLs instead of local files')
    p.add_argument('--base', default=BASE_URL_DEFAULT,
                   help='Base URL when --live (default: %(default)s)')
    p.add_argument('--verbose', '-v', action='store_true',
                   help='Print passing tests too')
    p.add_argument('--category', '-c', default=None,
                   help='Run only categories matching prefix (e.g., "3" or "seo")')
    args = p.parse_args()

    mode = 'live' if args.live else 'local'
    r = TestRunner(mode=mode, base_url=args.base,
                   verbose=args.verbose, category_filter=args.category)

    print('=' * 78)
    print(f'  LTTSTUDIOS WEBSITE TEST SUITE')
    print(f'  Mode:        {mode.upper()}')
    if mode == 'live':
        print(f'  Base URL:    {r.base_url}')
    print(f'  Root:        {ROOT}')
    if args.category:
        print(f'  Category:    {args.category}')
    print('=' * 78)
    print()

    for cat_num, fn in CATEGORIES:
        if args.category and not str(cat_num).startswith(args.category):
            continue
        sys.stdout.write(f'Running category {cat_num} — {fn.__doc__.split("—")[0].strip("[]")}... ')
        sys.stdout.flush()
        before = len(r.results)
        try:
            fn(r)
        except Exception as e:
            tc = TestCase(f'{cat_num}.RUNNER', f'category {cat_num} crashed')
            tc.fail(f'unhandled exception: {e}')
            r.add(tc)
        added = r.results[before:]
        pass_count = sum(1 for t in added if t.result == TestResult.PASS)
        fail_count = sum(1 for t in added if t.result == TestResult.FAIL)
        if fail_count:
            print(f'❌ {pass_count} pass / {fail_count} FAIL ({len(added)} total)')
        else:
            print(f'✅ {pass_count} pass ({len(added)} total)')

    print()

    # Report failures grouped by category
    by_cat = defaultdict(list)
    for t in r.results:
        if t.result == TestResult.FAIL:
            by_cat[t.category].append(t)

    if by_cat:
        print('=' * 78)
        print('  FAILURES')
        print('=' * 78)
        for cat in sorted(by_cat.keys()):
            print(f'\n[{cat}] {len(by_cat[cat])} failure(s):')
            for t in by_cat[cat]:
                print(f'  ❌ {t.name}')
                print(f'     {t.message}')
        print()

    # Verbose: also list passes
    if args.verbose:
        print('=' * 78)
        print('  PASSING TESTS')
        print('=' * 78)
        by_pass = defaultdict(list)
        for t in r.results:
            if t.result == TestResult.PASS:
                by_pass[t.category].append(t)
        for cat in sorted(by_pass.keys()):
            print(f'\n[{cat}] {len(by_pass[cat])} pass:')
            for t in by_pass[cat][:5]:
                print(f'  ✅ {t.name}')
            if len(by_pass[cat]) > 5:
                print(f'  ... and {len(by_pass[cat]) - 5} more')

    # Summary
    elapsed = time.time() - r.start_time
    total = len(r.results)
    passed = sum(1 for t in r.results if t.result == TestResult.PASS)
    failed = sum(1 for t in r.results if t.result == TestResult.FAIL)

    print('=' * 78)
    print('  SUMMARY')
    print('=' * 78)
    print(f'  Total tests: {total}')
    print(f'  ✅ Passed:    {passed}')
    print(f'  ❌ Failed:    {failed}')
    print(f'  Elapsed:     {elapsed:.2f}s')
    print()

    if failed == 0:
        print('🎉 ALL TESTS PASS — site is production-ready')
        return 0
    else:
        print(f'❌ {failed} test(s) failed — review output above')
        return 1


if __name__ == '__main__':
    sys.exit(main())
