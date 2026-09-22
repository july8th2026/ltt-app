"""Phân loại lỗi yt-dlp thành LoiCao (spec §19).

Port tín hiệu từ donor `web_app.py:4926-4963` và `cutclipshort/adapters/downloader.py:299-303`.
Thứ tự xét là có chủ đích (khớp đầu tiên thắng, như donor `W:4677`):
- tuổi trước bot-check: "Sign in to confirm your age" chứa "Sign in to confirm";
- bot-check trước riêng tư: donor downloader coi "sign in" là riêng tư, nhưng câu bot-check cũng có "Sign in";
- LTT siết "age" trần của donor (khớp nhầm "webpage", "message") thành các cụm cụ thể.
Thông điệp khách là câu cố định — không bao giờ chứa văn bản thô (URL, cookie, token).
"""
from __future__ import annotations

from apps.video_crawler.adapters.base import LoiCao

#: (mã, các tín hiệu viết thường, tam_thoi, thông điệp khách) — xét theo thứ tự.
_BANG: tuple[tuple[str, tuple[str, ...], bool, str], ...] = (
    ("gioi_han_tuoi",
     ("confirm your age", "age-restricted", "age restricted", "inappropriate for some users"),
     False, "Video bị giới hạn tuổi, không tải được."),
    ("yt_bot", ("sign in to confirm", "not a bot"),
     True, "YouTube tạm chặn truy cập tự động. Vui lòng thử lại sau."),
    ("chi_la_anh", ("no video formats found",),
     False, "Bài đăng này không có video (chỉ có ảnh)."),
    ("url_khong_ho_tro", ("unsupported url", "no suitable extractor"),
     False, "Link không được hỗ trợ cho nền tảng này."),
    ("yt_403", ("unable to download video data", "http error 403"),
     True, "YouTube từ chối tải video này lúc này. Vui lòng thử lại sau."),
    ("rieng_tu", ("private", "members-only", "members only", "join this channel", "sign in"),
     False, "Video ở chế độ riêng tư hoặc chỉ dành cho thành viên."),
    ("khong_ton_tai", ("unavailable", "has been removed", "removed by", "does not exist",
                       "no longer available", "http error 404", "been terminated"),
     False, "Video không tồn tại hoặc đã bị gỡ."),
    ("mang", ("timed out", "timeout", "connection reset", "connection refused", "connection aborted",
              "forcibly closed", "getaddrinfo failed", "name resolution", "network is unreachable",
              "remote end closed", "incompleteread", "network connection error"),
     True, "Lỗi mạng khi kết nối tới nền tảng. Vui lòng thử lại sau."),
)

_KHAC = "Không tải được video do lỗi không xác định. Vui lòng thử lại sau."


def phan_loai(thong_diep: str) -> LoiCao:
    """Văn bản lỗi yt-dlp ⇒ LoiCao có mã, cờ tạm thời và câu báo khách an toàn."""
    low = (thong_diep or "").lower()
    if "fragment" in low and "403" in low:        # donor W:4930
        return LoiCao("yt_403", _BANG[4][3], tam_thoi=True)
    for ma, tin_hieu, tam_thoi, cau in _BANG:
        if any(t in low for t in tin_hieu):
            return LoiCao(ma, cau, tam_thoi=tam_thoi)
    return LoiCao("loi_khac", _KHAC, tam_thoi=True)
