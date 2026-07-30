# LTTStudios Website — Test Suite

Comprehensive automated test suite covering 16 categories. **607 tests** passing
in **~70ms**. Zero dependencies (Python stdlib only).

## Quick start

```bash
cd docs/lttstudios-website
python -X utf8 tests/run_tests.py
```

**Expected output**: `🎉 ALL TESTS PASS — site is production-ready`

## Modes

### Local mode (default) — tests files on disk
Use this **before deploy** to verify the build.
```bash
python -X utf8 tests/run_tests.py
```

### Live mode — tests deployed URLs
Use this **after deploy** to verify the live site.
```bash
python -X utf8 tests/run_tests.py --live
# Or against a different base URL:
python -X utf8 tests/run_tests.py --live --base https://staging.lttstudios.com
```

## Options

| Flag | Effect |
|---|---|
| `--live` | Test live HTTP URLs instead of local files |
| `--base URL` | Override base URL for live mode (default `https://lttstudios.com`) |
| `--verbose` / `-v` | Print passing tests too |
| `--category N` / `-c N` | Run only categories matching prefix (e.g., `-c 3` for META) |

## 16 Test Categories

| # | Category | What it tests | Test count |
|---|---|---|---|
| 1 | **STRUCTURE** | Required files exist (41 expected files) | 41 |
| 2 | **HTML VALIDITY** | DOCTYPE, lang attr, paired tags (`<div>`, `<section>`, `<body>`) | 32 |
| 3 | **META TAGS** | `<title>`, `<meta description>`, canonical, `og:title` per page | 120 |
| 4 | **HTML LANG** | `<html lang="en">` for EN, `<html lang="vi">` for VI | 32 |
| 5 | **INTERNAL LINKS** | Every `href="/..."` resolves to an existing file | 32 |
| 6 | **ASSETS** | CSS/JS load, all `/assets/...` refs exist | 96 |
| 7 | **HREFLANG** | EN ↔ VI alternate links present + URL correct | 28 |
| 8 | **LANG SWITCHER** | Switcher in nav + EN→VI→EN roundtrip same page | 14 |
| 9 | **SCHEMA.ORG** | JSON-LD parses validly | 3 |
| 10 | **SITEMAP + ROBOTS** | Sitemap XML valid, all URLs map to files, robots.txt has `Sitemap:` + `User-agent:` | 28 |
| 11 | **MANIFEST + SECURITY** | manifest.json valid PWA, security.txt RFC 9116 compliant | 2 |
| 12 | **BRAND** | No capitalization typos, no unknown email addresses | 64 |
| 13 | **ACCESSIBILITY** | `nav-toggle` has `aria-label`, all `<img>` have `alt` | 64 |
| 14 | **STALE REFS** | No leftover `lttstudio.top` (except intentional changelog history) | 37 |
| 15 | **CONTENT PARITY** | VI pages have ≥40% file size of EN counterpart | 14 |
| 16 | **LIVE URLS** | (Live mode only) HTTP 200 + correct `lang` attribute on 24 key URLs | 0/24 |

**Total**: 607 tests local mode, 631 tests live mode.

## Output

The runner prints:
1. **Per-category summary line** (✅ pass count or ❌ fail count)
2. **Failures detail** grouped by category (with reason for each failure)
3. **Summary**: total / passed / failed / elapsed time
4. Exit code **0** if all pass, **1** if any fail

Example successful run:
```
==============================================================================
  LTTSTUDIOS WEBSITE TEST SUITE
  Mode:        LOCAL
==============================================================================

Running category 1 — 1] FILE STRUCTURE ... ✅ 41 pass (41 total)
Running category 2 — 2] HTML VALIDITY ... ✅ 32 pass (32 total)
Running category 3 — 3] META TAGS ... ✅ 120 pass (120 total)
...

==============================================================================
  SUMMARY
==============================================================================
  Total tests: 607
  ✅ Passed:    607
  ❌ Failed:    0
  Elapsed:     0.07s

🎉 ALL TESTS PASS — site is production-ready
```

## When to run

| Moment | Mode | Why |
|---|---|---|
| Before commit | `python tests/run_tests.py` | Catch regressions before merge |
| Before deploy | `python tests/run_tests.py` | Verify build state is OK |
| After deploy | `python tests/run_tests.py --live` | Confirm live URLs are correct |
| After CDN cache purge | `python tests/run_tests.py --live` | Verify cache served the new version |
| Periodic health check | `python tests/run_tests.py --live` (cron) | Detect domain expiry, host issues |

## CI/CD integration

For GitHub Actions / GitLab CI:

```yaml
# .github/workflows/website-tests.yml
name: Website tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - run: cd docs/lttstudios-website && python -X utf8 tests/run_tests.py
```

For Cron live health-check (Linux):
```bash
# Daily 8am Asia/Ho_Chi_Minh, email on failure
0 8 * * * cd /path/to/website && python tests/run_tests.py --live || mail -s "lttstudios.com health check failed" team@lttstudios.com
```

## Adding new tests

Tests are categorized functions named `cat_N_xxx(r: TestRunner)`. Each test creates
a `TestCase` and appends to `r.results`:

```python
def cat_17_my_check(r: TestRunner):
    """[17] MY CHECK — short description."""
    for fp in r.category_pages():
        tc = TestCase('17.MYCHECK', f'something: {fp}')
        c = r.read(fp)
        if 'badthing' in c:
            tc.fail('found badthing')
        r.add(tc)
```

Then add to `CATEGORIES` list at the bottom:
```python
CATEGORIES = [
    ...
    ('17', cat_17_my_check),
]
```

That's it. The runner handles discovery, reporting, exit codes.

## Exit codes

- **0** — All tests passed → safe to deploy
- **1** — Some tests failed → review FAILURES section above the summary

## Performance

| Mode | Tests | Time | Notes |
|---|---|---|---|
| Local | 607 | ~70ms | File system only, no network |
| Live | 631 | ~5-15s | HTTP fetches against live URLs |
| `-c 3` (single category) | 120 | ~10ms | Filter for fast iteration |

## Dependencies

**None.** Pure Python 3.10+ stdlib:
- `argparse`, `json`, `os`, `re`, `sys`, `time`
- `urllib.request`, `urllib.error`
- `xml.etree.ElementTree`
- `collections.defaultdict`
- `pathlib.Path`
