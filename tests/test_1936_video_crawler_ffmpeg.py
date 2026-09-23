"""
video_crawler — worker phải TÌM ĐƯỢC ffmpeg, và lỗi lạ phải để lại dấu vết (nghiệm thu production 23/09/2026).

🔴 Sự cố thật: sau khi deploy, MỌI lượt tải YouTube trên production hỏng sau ~10 s với câu "Không tải được video
do lỗi không xác định" (`loi_khac`), tiền hoàn đủ nên không ai mất gì — nhưng cũng không ai biết vì sao. Chạy lại
đúng mã production bằng tài khoản CỦA TÔI thì XANH; chạy dưới `SYSTEM` (tài khoản dịch vụ worker) mới đỏ. Lỗi gốc:

    ERROR: You have requested merging of multiple formats but ffmpeg is not installed. Aborting due to --abort-on-error

Hai khoảng trống, hai mệnh đề ở đây:
1. yt-dlp cần ffmpeg để GHÉP luồng hình + tiếng. `shutil.which("ffmpeg")` chạy được trong phiên người dùng nhưng
   KHÔNG lên tới dịch vụ nssm chạy dưới `LocalSystem` ⇒ phải truyền `ffmpeg_location` qua `platform_core.media`
   (đúng bộ định vị mà `transcript` đã dùng: env `LTT_FFMPEG` → PATH → gợi ý Windows → WinGet Links).
2. Câu "không xác định" của `loi.phan_loai` KHÔNG được nuốt văn bản gốc: lỗi chưa phân loại phải vào log vận hành,
   nếu không thì mọi lỗi mới đều trông giống nhau và không ai lần ra được.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest


def test_tuy_chon_goc_truyen_ffmpeg_location(monkeypatch, tmp_path):
    from platform_core import media

    from apps.video_crawler.adapters.youtube import YoutubeAdapter
    gia = tmp_path / "ffmpeg.exe"
    gia.write_bytes(b"x")
    monkeypatch.setattr(media, "ffmpeg_bin", lambda: str(gia))
    o = YoutubeAdapter.tuy_chon_goc(tmp_path)
    assert o["ffmpeg_location"] == str(gia)


def test_khong_co_ffmpeg_thi_khong_vo_tuy_chon(monkeypatch, tmp_path):
    """Máy chưa có ffmpeg: dựng tuỳ chọn vẫn chạy (yt-dlp tự báo lỗi rõ ở lượt tải), không ném lúc dựng."""
    from platform_core import media

    from apps.video_crawler.adapters.youtube import YoutubeAdapter

    def _khong_co():
        raise media.MediaError("khong thay ffmpeg")
    monkeypatch.setattr(media, "ffmpeg_bin", _khong_co)
    o = YoutubeAdapter.tuy_chon_goc(tmp_path)
    assert "ffmpeg_location" not in o


@pytest.mark.parametrize("thong_diep", [
    "ERROR: You have requested merging of multiple formats but ffmpeg is not installed. "
    "Aborting due to --abort-on-error",
    "ERROR: ffprobe and ffmpeg not found. Please install or provide the path using --ffmpeg-location",
])
def test_thieu_ffmpeg_co_ma_rieng_khong_phai_loi_khac(thong_diep):
    """Thiếu ffmpeg là lỗi CẤU HÌNH MÁY CHỦ, không phải lỗi của khách và không phải 'không xác định'."""
    from apps.video_crawler import loi
    e = loi.phan_loai(thong_diep)
    assert e.ma == "thieu_ffmpeg"
    assert e.tam_thoi is False
    assert "ffmpeg" not in e.thong_diep.lower()        # câu cho khách không nói tên công cụ nội bộ


def test_loi_chua_phan_loai_duoc_GHI_LOG_van_ban_goc(caplog):
    """`loi_khac` mà im lặng = sự cố 23/09 lặp lại: mọi lỗi mới trông giống nhau, không lần ra được."""
    from apps.video_crawler import loi
    with caplog.at_level(logging.WARNING, logger="apps.video_crawler.loi"):
        e = loi.phan_loai("ERROR: mot loi hoan toan moi tu nen tang X")
    assert e.ma == "loi_khac"
    assert any("mot loi hoan toan moi" in r.getMessage() for r in caplog.records), \
        "văn bản gốc phải vào log vận hành"


def test_da_phan_loai_thi_khong_spam_log(caplog):
    from apps.video_crawler import loi
    with caplog.at_level(logging.WARNING, logger="apps.video_crawler.loi"):
        loi.phan_loai("ERROR: Video unavailable")
    assert not caplog.records


def test_san_pham_that_co_ffmpeg_tren_may_nay():
    """Đối chứng môi trường: máy A có ffmpeg qua `platform_core.media` (nếu đỏ thì máy chủ thiếu thật)."""
    from platform_core import media
    assert media.has_ffmpeg(), "máy này không có ffmpeg — worker sẽ không ghép được video"
    assert Path(media.ffmpeg_bin()).is_file()
