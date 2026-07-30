"""
PA-3 — preflight column validation tests.

Guards docs/AUDIT_REPORT.md finding B3: a one-word column-name mismatch
(`schedule_time_fb_dai` vs `schedule_time`) took a live run down mid-flight,
and a second mismatch (`error_message_dai`) silently disabled error
write-back with no symptom at all.
"""
from __future__ import annotations

from core.preflight import Severity, check_columns

# Header set taken from a real tab observed during the audit.
REAL_HEADERS = [
    "binh_luan_video", "dang_ky_kenh", "diem", "dsp_chinh", "error_message",
    "fb_video_id", "link_kenh_youtube", "make_status", "mo_ta",
    "schedule_time", "status", "status_clip_short", "status_fb",
    "ten_video_upload", "tieu_de", "tieu_de_seo", "time_tiktok",
    "titok_status", "tu_khoa_chinh", "upload_duration_s", "uploaded_at",
    "video_goc", "video_short", "video_url_fb",
]


def _config(**overrides) -> dict:
    base = {
        "col_schedule_time": "schedule_time",
        "col_status":        "status_fb",
        "col_video_drive":   "video_goc",
        "col_error":         "error_message",
        "col_fb_link":       "video_url_fb",
        "col_title":         "tieu_de_seo",
    }
    base.update(overrides)
    return base


def test_fully_matching_config_has_no_findings():
    result = check_columns(_config(), REAL_HEADERS, tab="T")
    assert result.findings == []
    assert result.ok is True
    assert "✅" in result.format()


def test_missing_mandatory_column_is_an_error_and_blocks_run():
    result = check_columns(
        _config(col_schedule_time="schedule_time_fb_dai"), REAL_HEADERS, tab="T",
    )
    assert result.ok is False
    assert len(result.errors) == 1
    assert result.errors[0].config_key == "col_schedule_time"


def test_the_real_audit_case_suggests_the_correct_header():
    """The exact mismatch that broke the live run must be auto-diagnosed."""
    result = check_columns(
        _config(col_schedule_time="schedule_time_fb_dai"), REAL_HEADERS, tab="T",
    )
    assert result.errors[0].suggestion == "schedule_time"


def test_missing_error_column_is_a_warning_that_does_not_block():
    result = check_columns(
        _config(col_error="error_message_dai"), REAL_HEADERS, tab="T",
    )
    assert result.ok is True                      # run still possible
    assert len(result.warnings) == 1
    w = result.warnings[0]
    assert w.config_key == "col_error"
    assert w.suggestion == "error_message"
    # The consequence must be spelled out — silent loss is the whole bug.
    assert "KHÔNG được ghi" in w.consequence


def test_unset_column_is_reported_not_skipped():
    result = check_columns(_config(col_schedule_time=""), REAL_HEADERS, tab="T")
    assert result.ok is False
    assert result.errors[0].configured == "(chưa đặt)"


def test_unrelated_name_gets_no_misleading_suggestion():
    result = check_columns(
        _config(col_schedule_time="zzz_completely_unrelated_xyz"), REAL_HEADERS, tab="T",
    )
    assert result.errors[0].suggestion == ""


def test_severity_split_is_correct():
    result = check_columns(
        _config(col_schedule_time="nope_missing", col_error="also_missing"),
        REAL_HEADERS, tab="T",
    )
    assert {f.severity for f in result.errors} == {Severity.ERROR}
    assert {f.severity for f in result.warnings} == {Severity.WARNING}


def test_headers_are_whitespace_normalised():
    result = check_columns(_config(), ["  schedule_time  ", "status_fb",
                                      "video_goc", "error_message",
                                      "video_url_fb", "tieu_de_seo"], tab="T")
    assert result.ok is True


def test_empty_sheet_reports_every_column_missing():
    result = check_columns(_config(), [], tab="Empty")
    assert result.ok is False
    assert len(result.errors) == 2      # both mandatory columns
    assert len(result.warnings) == 4    # all important columns
