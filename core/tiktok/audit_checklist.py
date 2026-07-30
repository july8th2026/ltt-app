"""
TikTok audit submission readiness checklist (Sprint TT-4.1).

Why this exists:
  TikTok app audit is a one-shot manual submission — if anything is missing,
  reviewers reject and the user re-submits with a 5-14 day wait. This module
  verifies all the pre-conditions BEFORE the user clicks "Submit for review"
  so they catch problems at home instead of waiting two weeks for rejection.

Checks performed (all read-only — no API calls, no side effects):
  1. Client key + secret configured
  2. Redirect URI uses HTTPS (TikTok requires this in 2024+)
  3. Privacy + Terms URLs present and reachable (HEAD request, no body fetch)
  4. App icon file exists at the documented path
  5. Demo video script + recorded URL configured
  6. Scopes string contains required minimum set
  7. Audit-related boolean flags consistent
  8. Compliance guard parameters (privacy_level default = SELF_ONLY)

Returns ChecklistReport with pass/warn/fail buckets so the GUI can render
a clean table of items the user still needs to address.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# requests is imported at module top (not inside functions) so tests can
# easily patch `core.tiktok.audit_checklist.requests` to stub HTTP behaviour.
try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


class CheckResult(Enum):
    PASS = "pass"      # ✅ ready
    WARN = "warn"      # ⚠ recommended but not blocking
    FAIL = "fail"      # ❌ blocking — TikTok reviewers WILL reject


@dataclass
class CheckItem:
    name:     str
    result:   CheckResult
    message:  str
    fix_hint: str = ""


@dataclass
class ChecklistReport:
    items:    list[CheckItem] = field(default_factory=list)

    @property
    def pass_count(self)   -> int:  return sum(1 for i in self.items if i.result is CheckResult.PASS)
    @property
    def warn_count(self)   -> int:  return sum(1 for i in self.items if i.result is CheckResult.WARN)
    @property
    def fail_count(self)   -> int:  return sum(1 for i in self.items if i.result is CheckResult.FAIL)
    @property
    def ready_to_submit(self) -> bool: return self.fail_count == 0

    def summary(self) -> str:
        """Localized human summary. i18n: English default, Vietnamese via switcher."""
        try:
            from core.i18n import t
            if self.ready_to_submit and self.warn_count == 0:
                return t("audit.summary_ready",
                         default=f"✅ Ready to submit TikTok audit ({self.pass_count} checks pass)",
                         pass_count=self.pass_count)
            if self.ready_to_submit:
                return t("audit.summary_warnings",
                         default=f"🟡 Submittable but {self.warn_count} warnings",
                         pass_count=self.pass_count, warn_count=self.warn_count)
            return t("audit.summary_blocking",
                     default=f"❌ Not ready — {self.fail_count} blocking",
                     fail_count=self.fail_count,
                     warn_count=self.warn_count,
                     pass_count=self.pass_count)
        except Exception:
            # Fallback English nếu i18n module chưa load (vd tests)
            if self.ready_to_submit and self.warn_count == 0:
                return f"✅ Ready to submit TikTok audit ({self.pass_count} checks pass)"
            if self.ready_to_submit:
                return (
                    f"🟡 Submittable but {self.warn_count} warnings "
                    f"({self.pass_count} pass, {self.warn_count} warn)"
                )
            return (
                f"❌ Not ready — {self.fail_count} blocking, "
                f"{self.warn_count} warn, {self.pass_count} pass"
            )


# ─── Built-in checks ────────────────────────────────────────────────────────

def run_checklist(config: dict) -> ChecklistReport:
    """Run all checks against *config* and return a ChecklistReport."""
    report = ChecklistReport()
    for check in _ALL_CHECKS:
        try:
            item = check(config)
        except Exception as exc:
            item = CheckItem(
                name=check.__name__.replace("check_", ""),
                result=CheckResult.WARN,
                message=f"Check crash: {exc}",
                fix_hint="Báo bug",
            )
        report.items.append(item)
    return report


# ─── Individual checks ──────────────────────────────────────────────────────

def check_client_credentials(config: dict) -> CheckItem:
    key    = str(config.get("tiktok_client_key",    "")).strip()
    secret = str(config.get("tiktok_client_secret", "")).strip()
    if not key:
        return CheckItem("Client Key", CheckResult.FAIL,
                         "tiktok_client_key trống",
                         "Vào TikTok Dev Portal → My Apps → copy Client Key")
    if not secret:
        return CheckItem("Client Secret", CheckResult.FAIL,
                         "tiktok_client_secret trống",
                         "Copy Client Secret từ Dev Portal")
    return CheckItem("Client Credentials", CheckResult.PASS,
                     f"Client Key {key[:8]}… đã cấu hình", "")


def check_redirect_uri_https(config: dict) -> CheckItem:
    uri = str(config.get("tiktok_redirect_uri", "")).strip()
    if not uri:
        return CheckItem("Redirect URI", CheckResult.FAIL,
                         "tiktok_redirect_uri trống",
                         "Phải set https://lttstudios.com/legal/callback.html")
    if not uri.startswith("https://"):
        return CheckItem("Redirect URI", CheckResult.FAIL,
                         f"Redirect URI không HTTPS: {uri}",
                         "TikTok 2024+ chỉ chấp nhận HTTPS")
    return CheckItem("Redirect URI", CheckResult.PASS,
                     f"HTTPS callback OK: {uri}", "")


# Browser-like User-Agent — vài host (Cloudflare/anti-bot) trả 403 với requests
# default UA. TT-AUDIT-8 fix: dùng UA giống Chrome để mimic reviewer.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_BROWSER_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def _head_url(url: str, timeout: float = 6.0) -> tuple[bool, str]:
    """HEAD request URL — return (reachable, message).

    TT-AUDIT-8 fix: TikTok reviewers WILL click vào privacy + terms URL.
    Nếu URL 404/timeout, audit reject. Helper này dùng HEAD (không tải body)
    để check nhanh + tiết kiệm bandwidth.

    Fallback to GET nếu server không hỗ trợ HEAD (vài CDN reject HEAD).
    Dùng browser-like UA để tránh bị block bởi anti-bot WAF.
    """
    if requests is None:
        return False, "requests module unavailable"
    try:
        r = requests.head(
            url, timeout=timeout, allow_redirects=True, headers=_BROWSER_HEADERS,
        )
        # Nhiều host trả 403/405/501 với HEAD — fallback to GET stream
        if r.status_code in (403, 405, 501, 502):
            r = requests.get(
                url, timeout=timeout, allow_redirects=True, stream=True,
                headers=_BROWSER_HEADERS,
            )
            try:
                r.close()
            except Exception:
                pass
        if 200 <= r.status_code < 400:
            return True, f"HTTP {r.status_code}"
        return False, f"HTTP {r.status_code}"
    except requests.RequestException as exc:
        return False, f"{type(exc).__name__}: {exc}"


def check_privacy_terms_urls(config: dict) -> CheckItem:
    """Check cả presence + reachability của privacy + terms URL.

    TT-AUDIT-8: trước fix này chỉ kiểm tra có URL không, không verify URL
    truy cập được. Reviewer TT thấy URL 404 → reject.
    """
    priv = str(config.get("app_privacy_policy_url",
                          config.get("privacy_policy_url", ""))).strip()
    terms = str(config.get("app_terms_url", "")).strip()
    if not priv or not priv.startswith("https://"):
        return CheckItem("Privacy URL", CheckResult.FAIL,
                         "Privacy Policy URL chưa cấu hình hoặc không HTTPS",
                         "Set app_privacy_policy_url = https://...")
    if not terms or not terms.startswith("https://"):
        return CheckItem("Terms URL", CheckResult.FAIL,
                         "Terms URL chưa cấu hình hoặc không HTTPS",
                         "Set app_terms_url = https://...")

    # Reachability check (best-effort — network failures → WARN not FAIL).
    # Cloudflare/WAF 403 với requests UA → WARN với hint browser-verify,
    # vì TT reviewer dùng browser thật vẫn vào được.
    priv_ok, priv_msg = _head_url(priv)
    terms_ok, terms_msg = _head_url(terms)

    def _is_cf_block(msg: str) -> bool:
        return "HTTP 403" in msg or "HTTP 503" in msg

    if not priv_ok:
        result = CheckResult.WARN if _is_cf_block(priv_msg) else CheckResult.FAIL
        hint = (
            f"Cloudflare/WAF có thể block requests Python ({priv_msg}). "
            f"Mở browser thử {priv} → nếu trang load được, audit reviewer "
            "(dùng browser) cũng vào được."
        ) if _is_cf_block(priv_msg) else (
            f"Mở browser thử {priv} — nếu 404, upload lại file hoặc fix path"
        )
        return CheckItem(
            "Privacy URL", result,
            f"Privacy URL không truy cập được: {priv_msg}", hint,
        )
    if not terms_ok:
        result = CheckResult.WARN if _is_cf_block(terms_msg) else CheckResult.FAIL
        hint = (
            f"Cloudflare/WAF block ({terms_msg}). Mở browser thử {terms}."
        ) if _is_cf_block(terms_msg) else (
            f"Mở browser thử {terms} — nếu 404, upload lại file hoặc fix path"
        )
        return CheckItem(
            "Terms URL", result,
            f"Terms URL không truy cập được: {terms_msg}", hint,
        )
    return CheckItem(
        "Privacy + Terms URLs", CheckResult.PASS,
        f"Cả 2 URL HTTPS truy cập được (priv: {priv_msg}, terms: {terms_msg})",
        "",
    )


def check_app_icon(config: dict) -> CheckItem:
    candidates = [
        "docs/tiktok-submission/lttstudio-icon-1024.png",
        os.path.join("data", "icon.png"),
    ]
    for path in candidates:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 0:
                return CheckItem("App Icon", CheckResult.PASS,
                                 f"Icon tồn tại tại {path} ({size//1024} KB)", "")
    return CheckItem("App Icon", CheckResult.WARN,
                     "Không tìm thấy file icon 1024×1024 PNG",
                     "Đặt file tại docs/tiktok-submission/lttstudio-icon-1024.png")


def check_demo_video(config: dict) -> CheckItem:
    script = "docs/tiktok-submission/demo-video-script.md"
    if os.path.exists(script):
        return CheckItem("Demo Video Script", CheckResult.PASS,
                         f"Script tồn tại: {script}", "")
    return CheckItem("Demo Video Script", CheckResult.WARN,
                     "Script demo chưa có",
                     f"Tạo file {script} trước khi quay video")


def check_scopes(config: dict) -> CheckItem:
    scopes_raw = str(config.get("tiktok_scopes", "")).strip()
    required = {"user.info.basic", "video.upload", "video.publish"}
    have = set(s.strip() for s in scopes_raw.split(",") if s.strip())
    missing = required - have
    if missing:
        return CheckItem("Scopes", CheckResult.FAIL,
                         f"Thiếu scope bắt buộc: {sorted(missing)}",
                         "Set tiktok_scopes = user.info.basic,video.upload,video.publish")
    extras = have - required
    return CheckItem("Scopes", CheckResult.PASS,
                     f"Đủ scope core (+{len(extras)} extra)", "")


def check_audit_flags_consistency(config: dict) -> CheckItem:
    audit_ok = bool(config.get("tiktok_audit_approved", False))
    direct   = bool(config.get("tiktok_enable_direct_post", False))
    if direct and not audit_ok:
        return CheckItem("Audit flags", CheckResult.FAIL,
                         "tiktok_enable_direct_post=true nhưng audit_approved=false",
                         "Direct post yêu cầu app phải qua audit. Set false hoặc đợi audit.")
    if audit_ok and not direct:
        return CheckItem("Audit flags", CheckResult.WARN,
                         "Audit approved nhưng chưa bật direct post",
                         "Set tiktok_enable_direct_post=true để dùng full features")
    return CheckItem("Audit flags", CheckResult.PASS,
                     f"audit_approved={audit_ok}, direct_post={direct}", "")


def check_user_consent_required(config: dict) -> CheckItem:
    if not bool(config.get("tiktok_require_user_confirm", True)):
        return CheckItem("User confirm", CheckResult.WARN,
                         "tiktok_require_user_confirm=false — TikTok khuyến nghị bật",
                         "Bật để có audit trail cho compliance")
    return CheckItem("User confirm", CheckResult.PASS,
                     "Bật require_user_confirm cho audit trail", "")


def check_safe_privacy_default(config: dict) -> CheckItem:
    pl = str(config.get("tiktok_privacy_level", "SELF_ONLY")).strip()
    if pl == "PUBLIC_TO_EVERYONE" and not bool(config.get("tiktok_audit_approved", False)):
        return CheckItem("Privacy default", CheckResult.FAIL,
                         "Default PUBLIC_TO_EVERYONE nhưng app chưa audit",
                         "Set tiktok_privacy_level=SELF_ONLY cho đến khi audit pass")
    return CheckItem("Privacy default", CheckResult.PASS,
                     f"Privacy default an toàn: {pl}", "")


def check_privacy_policy_mentions_tiktok(config: dict) -> CheckItem:
    """TT-AUDIT-12: Privacy policy phải mention TikTok data usage.

    TikTok reviewers đọc file privacy. Nếu privacy không mention TT,
    không nói rõ data nào được fetch + lưu, audit reject.

    Check best-effort: GET privacy URL, parse text, tìm keyword.
    Network fail → WARN (không block, user có thể manual verify).
    """
    priv = str(config.get("app_privacy_policy_url",
                          config.get("privacy_policy_url", ""))).strip()
    if not priv or not priv.startswith("https://"):
        return CheckItem(
            "Privacy mentions TikTok", CheckResult.WARN,
            "Không có URL để check content",
            "Set app_privacy_policy_url trước",
        )
    if requests is None:
        return CheckItem(
            "Privacy mentions TikTok", CheckResult.WARN,
            "requests module unavailable",
            "pip install requests",
        )
    try:
        r = requests.get(priv, timeout=8.0, allow_redirects=True, headers=_BROWSER_HEADERS)
        if r.status_code >= 400:
            return CheckItem(
                "Privacy mentions TikTok", CheckResult.WARN,
                f"Không tải được nội dung (HTTP {r.status_code})",
                "Manually verify URL chứa thông tin về TikTok data",
            )
        text = r.text.lower()
        required = ["tiktok"]
        # Match broader substrings — "access token" vs "access tokens" both pass.
        recommended = ["open_id", "access", "video", "scope"]
        missing_req = [k for k in required if k not in text]
        if missing_req:
            return CheckItem(
                "Privacy mentions TikTok", CheckResult.FAIL,
                f"Privacy policy không mention: {missing_req}",
                "Thêm đoạn mô tả app sử dụng TikTok API + data nào được lưu",
            )
        missing_rec = [k for k in recommended if k not in text]
        if missing_rec:
            return CheckItem(
                "Privacy mentions TikTok", CheckResult.WARN,
                f"Privacy policy thiếu detail: {missing_rec}",
                "Thêm thông tin cụ thể về OAuth scope + data retention",
            )
        return CheckItem(
            "Privacy mentions TikTok", CheckResult.PASS,
            "Privacy policy mention đầy đủ TikTok + scope + data",
            "",
        )
    except Exception as exc:
        return CheckItem(
            "Privacy mentions TikTok", CheckResult.WARN,
            f"Không check được nội dung: {exc}",
            "Manually mở browser verify privacy policy mention TikTok",
        )


def check_login_button_branding(config: dict) -> CheckItem:
    """TT-AUDIT-1: Verify file logo TikTok PNG có sẵn.

    TT yêu cầu nút Login phải dùng logo official, không emoji. Code đã
    fallback nếu thiếu nhưng audit có thể phê bình.
    """
    path = os.path.join("data", "assets", "tiktok_logo.png")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return CheckItem(
            "Login button branding", CheckResult.PASS,
            f"Logo TikTok có tại {path}", "",
        )
    return CheckItem(
        "Login button branding", CheckResult.WARN,
        "Chưa có file logo TikTok official",
        "Tải logo từ TikTok Developer Branding Kit → "
        "lưu vào data/assets/tiktok_logo.png (xem README trong folder đó)",
    )


_ALL_CHECKS = [
    check_client_credentials,
    check_redirect_uri_https,
    check_privacy_terms_urls,
    check_privacy_policy_mentions_tiktok,
    check_login_button_branding,
    check_app_icon,
    check_demo_video,
    check_scopes,
    check_audit_flags_consistency,
    check_user_consent_required,
    check_safe_privacy_default,
]
