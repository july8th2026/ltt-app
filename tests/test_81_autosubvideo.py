"""
Đợt B — app `autosubvideo` (khắc phụ đề). Kiểm: giá credit, registry nạp sạch,
parse transcript đa định dạng, cost qua manifest, media locate/probe an toàn,
run_with_progress phân tích tiến độ ffmpeg. Không cần ffmpeg thật cho phần lõi.
"""
from __future__ import annotations

import json
import io

import pytest


# ── Giá credit ────────────────────────────────────────────────────────────────

def test_cost_theo_phut_va_chat_luong():
    from apps.autosubvideo import cost
    assert cost.uoc_luong_credit(0, "standard") == cost.MIN_CREDIT      # sàn 1
    assert cost.uoc_luong_credit(60, "standard") == 5                   # 1 phút × 5
    assert cost.uoc_luong_credit(120, "standard") == 10                 # 2 phút × 5
    assert cost.uoc_luong_credit(60, "draft") == 3                      # 5 × 0.6
    assert cost.uoc_luong_credit(60, "high") == 8                       # ceil(5 × 1.5)=8
    # quality lạ → coi như standard
    assert cost.uoc_luong_credit(60, "xx") == 5


def test_cost_lam_tron_len():
    from apps.autosubvideo import cost
    # 30s standard = 0.5 phút × 5 = 2.5 → ceil = 3
    assert cost.uoc_luong_credit(30, "standard") == 3


# ── Registry: app nạp sạch, đúng chủ job_type ────────────────────────────────

def test_app_nap_sach_va_dung_handler():
    from platform_core.registry import discover, job_type_owners
    apps = {a.manifest.slug: a for a in discover()}
    a = apps.get("autosubvideo")
    assert a is not None and a.error == "" and a.router is not None
    assert a.manifest.requires == ("ffmpeg",)
    assert job_type_owners().get("autosubvideo.render") == "autosubvideo"


def test_manifest_cost_dung_client_duration():
    from apps.autosubvideo.manifest import MANIFEST
    # 180s high = 3 phút × 5 × 1.5 = 22.5 → 23
    assert MANIFEST.credit_cost({"duration_s": 180, "quality": "high"}) == 23
    assert MANIFEST.credit_cost({"duration_s": 0, "quality": "standard"}) == 1


def test_browser_r2_direct_upload_mac_dinh_tat_den_khi_cors_duoc_gate(monkeypatch):
    from apps.autosubvideo.routes import _browser_direct_upload_enabled
    monkeypatch.delenv("LTT_R2_BROWSER_UPLOAD_ENABLED", raising=False)
    assert _browser_direct_upload_enabled() is False
    monkeypatch.setenv("LTT_R2_BROWSER_UPLOAD_ENABLED", "1")
    assert _browser_direct_upload_enabled() is True


def test_video_range_stream_supports_non_seekable_r2_body():
    from apps.autosubvideo.routes import _iter_storage_range
    class Body:
        def __init__(self): self.data=io.BytesIO(b"0123456789");self.closed=False
        def read(self,size=-1): return self.data.read(size)
        def seek(self,_position): raise io.UnsupportedOperation("seek")
        def close(self): self.closed=True
    body=Body()
    assert b"".join(_iter_storage_range(body,2,4))==b"2345"
    assert body.closed is True


# ── Parse transcript đa định dạng ─────────────────────────────────────────────

def test_parse_srt():
    from apps.autosubvideo.parsers import parse_transcript
    srt = ("1\n00:00:00,000 --> 00:00:02,000\nDong mot\n\n"
           "2\n00:00:02,000 --> 00:00:04,500\nDong hai\n").encode("utf-8")
    segs = parse_transcript("a.srt", srt)
    assert len(segs) == 2
    assert segs[0]["start"] == 0.0 and segs[0]["end"] == 2.0
    assert segs[0]["text"] == "Dong mot" and segs[0]["type"] == "speech"
    assert segs[1]["end"] == 4.5


def test_parse_json():
    from apps.autosubvideo.parsers import parse_transcript
    raw = json.dumps([{"start": 0, "end": 1.5, "text": "hi"},
                      {"start": 1.5, "end": 3, "text": "bye"}]).encode("utf-8")
    segs = parse_transcript("b.json", raw)
    assert len(segs) == 2 and segs[1]["text"] == "bye"


def test_parse_dinh_dang_la_nem():
    from apps.autosubvideo.parsers import parse_transcript
    with pytest.raises(ValueError):
        parse_transcript("c.txt", b"noi dung")


# ── media: locate + probe an toàn ────────────────────────────────────────────

def test_media_locate_override_khong_ton_tai_thi_nem(monkeypatch):
    from platform_core import media
    monkeypatch.setenv("LTT_FFPROBE", r"Z:\khong-ton-tai\ffprobe.exe")
    monkeypatch.setattr(media.shutil, "which", lambda *_: None)
    with pytest.raises(media.MediaError):
        media.ffprobe_bin()


def test_media_locate_override_ton_tai(tmp_path, monkeypatch):
    from platform_core import media
    fake = tmp_path / "ffmpeg.exe"
    fake.write_bytes(b"x")
    monkeypatch.setenv("LTT_FFMPEG", str(fake))
    assert media.ffmpeg_bin() == str(fake)


def test_media_duration_file_hong_tra_0():
    from platform_core import media
    assert media.duration_seconds(r"Z:\khong\co\video.mp4") == 0.0


def test_media_progress_parse(monkeypatch):
    """run_with_progress đọc `out_time_us=`/`progress=end` từ stdout giả lập."""
    from platform_core import media

    class _FakeProc:
        returncode = 0

        def __init__(self):
            self.stdout = iter(["out_time_us=5000000\n", "progress=continue\n",
                                "progress=end\n"])
            self.stderr = _Empty()

        def wait(self, timeout=None):
            return 0

    class _Empty:
        def read(self):
            return ""

    monkeypatch.setattr(media.subprocess, "Popen", lambda *a, **k: _FakeProc())
    seen = []
    media.run_with_progress(["ffmpeg"], total_duration=10.0,
                            on_progress=lambda p: seen.append(p))
    assert 50.0 in seen          # 5s / 10s = 50%
    assert seen[-1] == 100.0     # progress=end → 100


def test_media_progress_loi_thi_nem(monkeypatch):
    from platform_core import media

    class _FakeProc:
        returncode = 1

        def __init__(self):
            self.stdout = iter([])
            self.stderr = _Err()

        def wait(self, timeout=None):
            return 1

    class _Err:
        def read(self):
            return "boom\nfatal error"

    monkeypatch.setattr(media.subprocess, "Popen", lambda *a, **k: _FakeProc())
    with pytest.raises(media.MediaError):
        media.run_with_progress(["ffmpeg"], total_duration=0)


def test_autosub_burn_kills_ffmpeg_when_progress_callback_cancels(monkeypatch):
    from apps.autosubvideo import burn

    class _FakeProc:
        def __init__(self):
            self.stdout = iter(["out_time_us=1000000\n"])
            self.stderr = iter([])
            self.returncode = None
            self.killed = False
        def poll(self):
            return None if not self.killed else -9
        def kill(self):
            self.killed = True; self.returncode = -9
        def wait(self, timeout=None):
            self.returncode = self.returncode or 0
            return self.returncode

    process = _FakeProc()
    monkeypatch.setattr(burn.subprocess, "Popen", lambda *_a, **_k: process)
    class _Cancelled(Exception):
        pass
    def cancel(_percent):
        raise _Cancelled()
    with pytest.raises(_Cancelled):
        burn._run_with_cleanup(["ffmpeg"], total_duration=10,
            on_progress=cancel, timeout=30, cwd=".")
    assert process.killed
