"""Read-only production crawl for WEB-003; no login or customer data."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "lttstudios-website" / "route-map.json"
ORIGIN = "https://lttstudios.com"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str, *, follow: bool = True) -> tuple[int, str, str]:
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "LTT-WEB-003-Audit/1.0"})
    try:
        with opener.open(req, timeout=15) as response:
            return response.status, response.geturl(), response.read(256_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location", ""), exc.read(256_000).decode("utf-8", "replace")
    except Exception as exc:
        return 0, "", type(exc).__name__


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    failures: list[str] = []
    checked_targets: set[str] = set()

    for rule in contract["rules"]:
        target = rule["production"]
        if target and target not in checked_targets:
            checked_targets.add(target)
            status, final, _ = fetch(urljoin(ORIGIN, target))
            expected = urljoin(ORIGIN, target)
            if status != 200 or final.rstrip("/") != expected.rstrip("/"):
                failures.append(f"target {target}: {status} -> {final}")

        source = rule["source"]
        disposition = rule["disposition"]
        if disposition in {"redirect", "locale_fallback"}:
            status, location, _ = fetch(urljoin(ORIGIN, source), follow=False)
            expected = urljoin(ORIGIN, target)
            actual = urljoin(ORIGIN, location) if location else ""
            if status not in {301, 308} or actual.rstrip("/") != expected.rstrip("/"):
                failures.append(f"alias {source}: {status} -> {actual or '-'}; expected {expected}")
        elif disposition == "oauth_callback":
            status, final, body = fetch(urljoin(ORIGIN, source))
            if status != 200 or not body.strip():
                failures.append(f"callback {source}: {status} -> {final}")

    for path in ("/robots.txt", "/sitemap_index.xml"):
        status, final, body = fetch(urljoin(ORIGIN, path))
        if status != 200 or not body.strip():
            failures.append(f"seo {path}: {status} -> {final}")

    home_status, home_final, home_body = fetch(ORIGIN + "/")
    home_lower = home_body.lower()
    if home_status != 200 or 'rel="canonical"' not in home_lower:
        failures.append(f"seo home canonical: {home_status} -> {home_final}")
    if 'name="viewport"' not in home_lower or "<html" not in home_lower:
        failures.append("seo home: missing viewport or html language shell")
    if "https://app.lttstudios.com" not in home_body:
        failures.append("content home: missing control-plane CTA")
    if "/wp-login.php" in home_body:
        failures.append("content home: WordPress login still exposed")

    missing_status, _, _ = fetch(ORIGIN + "/__ltt_audit_missing_20260803__")
    if missing_status != 404:
        failures.append(f"404 contract: expected 404, got {missing_status}")

    app_status, app_final, app_body = fetch("https://app.lttstudios.com/")
    if app_status != 200 or "LTT AI Studio" not in app_body:
        failures.append(f"control plane: {app_status} -> {app_final}")

    print(f"canonical targets: {len(checked_targets)}")
    print(f"failures: {len(failures)}")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
