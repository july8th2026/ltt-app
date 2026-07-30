"""
W3 — manual publish validation and job plumbing.

The validation rules are ported from `gui/operation_tab.py::_validate` /
`_validate_tiktok`. These tests pin the *ported* behaviour so the web
rejects what the desktop rejected, with the same wording — and pin the two
places where the web must differ (uploaded file instead of a local path,
background job instead of a blocking call).
"""
from __future__ import annotations

import os

import pytest

from server.services import ui_constants as UI
from server.services.manual_publish import (
    PublishRegistry,
    safe_upload_name,
    temp_video_dir,
    validate_facebook,
    validate_tiktok,
)


def _video(tmp_path, name="clip.mp4", size=2048):
    p = tmp_path / name
    p.write_bytes(b"\x00" * size)
    return str(p)


def _fb(**over):
    base = {
        "account": "My Account", "page": "My Page", "video_path": "",
        "title": "Tiêu đề hợp lệ", "description": "", "thumbnail": "",
        "schedule": "",
    }
    base.update(over)
    return base


def _tt(**over):
    base = {"account": "TikTok User", "video_path": "",
            "title": "Tiêu đề hợp lệ", "description": ""}
    base.update(over)
    return base


# ─── Facebook validation, in the desktop's order ──────────────────────────────

def test_fb_requires_account():
    err = validate_facebook(**_fb(account=""))
    assert "chọn tài khoản" in err


def test_fb_requires_page():
    err = validate_facebook(**_fb(page=""))
    assert "chọn Page đăng" in err


def test_fb_rejects_the_no_page_placeholder():
    """The desktop's page dropdown falls back to a literal placeholder
    string; publishing with it selected must fail."""
    err = validate_facebook(**_fb(page="(Chưa có page — vào tab Tài khoản FB)"))
    assert "chọn Page đăng" in err


def test_fb_requires_video(tmp_path):
    err = validate_facebook(**_fb(video_path=""))
    assert "chọn file video" in err


def test_fb_rejects_missing_file():
    err = validate_facebook(**_fb(video_path=r"C:\nope\missing.mp4"))
    assert "không tồn tại" in err


def test_fb_rejects_directory(tmp_path):
    err = validate_facebook(**_fb(video_path=str(tmp_path)))
    assert "thư mục" in err


def test_fb_rejects_empty_file(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path, size=0)))
    assert "rỗng" in err


def test_fb_rejects_bad_extension(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path, "clip.txt")))
    assert "đuôi video hợp lệ" in err


def test_fb_accepts_every_documented_extension(tmp_path):
    for ext in UI.VIDEO_EXTS_FB:
        err = validate_facebook(**_fb(video_path=_video(tmp_path, f"c{ext}")))
        assert err is None, f"{ext} should be accepted, got: {err}"


def test_fb_requires_title(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path), title="  "))
    assert "nhập tiêu đề" in err


def test_fb_title_limit_is_100(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path), title="x" * 101))
    assert "Tiêu đề quá dài" in err and "100" in err


def test_fb_description_limit_is_5000(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path),
                                  description="x" * 5001))
    assert "Mô tả quá dài" in err and "5000" in err


def test_fb_rejects_past_schedule(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path),
                                  schedule="01/01/2020 08:00"))
    assert "quá khứ" in err


def test_fb_rejects_malformed_schedule(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path),
                                  schedule="2020-01-01 08:00"))
    assert "DD/MM/YYYY HH:MM" in err


def test_fb_accepts_future_schedule(tmp_path):
    err = validate_facebook(**_fb(video_path=_video(tmp_path),
                                  schedule="01/01/2099 08:00"))
    assert err is None


def test_fb_rejects_bad_thumbnail(tmp_path):
    thumb = tmp_path / "not_an_image.txt"
    thumb.write_text("x", encoding="utf-8")
    err = validate_facebook(**_fb(video_path=_video(tmp_path),
                                  thumbnail=str(thumb)))
    assert "không phải ảnh hợp lệ" in err


def test_fb_happy_path(tmp_path):
    assert validate_facebook(**_fb(video_path=_video(tmp_path))) is None


# ─── TikTok validation ────────────────────────────────────────────────────────

def test_tt_requires_account():
    err = validate_tiktok(**_tt(account="(Chưa kết nối TikTok)"))
    assert "Chưa có tài khoản TikTok" in err


def test_tt_rejects_formats_facebook_allows(tmp_path):
    """The desktop's file picker offered .avi/.mkv on the TikTok tab and then
    rejected them. The web must reject them too — but ideally never offer
    them (the template's accept= list is narrower)."""
    for ext in (".avi", ".mkv", ".wmv", ".flv", ".m4v"):
        err = validate_tiktok(**_tt(video_path=_video(tmp_path, f"c{ext}")))
        assert err is not None and "định dạng" in err.lower() or "đuôi" in err.lower()


def test_tt_accepts_its_three_formats(tmp_path):
    for ext in UI.VIDEO_EXTS_TT:
        err = validate_tiktok(**_tt(video_path=_video(tmp_path, f"c{ext}")))
        assert err is None, f"{ext} should be accepted, got: {err}"


def test_tt_caption_limit_is_2200(tmp_path):
    err = validate_tiktok(**_tt(video_path=_video(tmp_path), title="x" * 2201))
    assert "2200" in err


def test_tt_title_plus_description_share_the_2200_budget(tmp_path):
    """This is the rule the desktop's character counter got wrong — it showed
    Facebook's 100/5000 on the TikTok tab."""
    err = validate_tiktok(**_tt(video_path=_video(tmp_path),
                                title="x" * 1500, description="y" * 800))
    assert err is not None
    assert "tổng cộng" in err


def test_tt_happy_path(tmp_path):
    assert validate_tiktok(**_tt(video_path=_video(tmp_path))) is None


# ─── Upload naming and storage ────────────────────────────────────────────────

def test_upload_name_strips_client_path():
    name = safe_upload_name(r"C:\Users\victim\..\..\evil.mp4")
    assert "\\" not in name and "/" not in name and ".." not in name
    assert name.endswith(".mp4")


def test_upload_name_is_unique_per_call():
    a = safe_upload_name("clip.mp4")
    b = safe_upload_name("clip.mp4")
    assert a != b


def test_upload_name_keeps_extension_because_validation_needs_it():
    assert safe_upload_name("movie.MOV").endswith(".mov")


def test_upload_name_survives_a_nameless_upload():
    assert safe_upload_name("")


def test_temp_video_dir_is_created(tmp_path):
    target = str(tmp_path / "vids")
    got = temp_video_dir({"temp_video_dir": target})
    assert got == target and os.path.isdir(got)


# ─── Job registry ─────────────────────────────────────────────────────────────

def test_registry_tracks_and_finds_jobs():
    r = PublishRegistry()
    job = r.create("facebook")
    assert r.get(job.id) is job
    assert r.latest("facebook") is job
    assert r.latest("tiktok") is None


def test_registry_is_bounded():
    r = PublishRegistry()
    for _ in range(70):
        r.create("facebook")
    assert len(r._jobs) <= 50


def test_job_dict_is_json_safe():
    import json
    r = PublishRegistry()
    job = r.create("tiktok")
    json.dumps(job.to_dict())
