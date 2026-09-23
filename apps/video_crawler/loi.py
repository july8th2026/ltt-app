"""Phân loại lỗi yt-dlp thành LoiCao (spec §19).

Port tín hiệu từ donor `web_app.py:4926-4963` và `cutclipshort/adapters/downloader.py:299-303`.
Thứ tự xét là có chủ đích (khớp đầu tiên thắng, như donor `W:4677`):
- tuổi trước bot-check: "Sign in to confirm your age" chứa "Sign in to confirm";
- bot-check trước riêng tư: donor downloader coi "sign in" là riêng tư, nhưng câu bot-check cũng có "Sign in";
- LTT siết "age" trần của donor (khớp nhầm "webpage", "message") thành các cụm cụ thể.
Thông điệp khách là câu cố định — không bao giờ chứa văn bản thô (URL, cookie, token).
"""
from __future__ import annotations

import logging

from platform_core.i18n import N_

from apps.video_crawler.adapters.base import LoiCao

#: (mã, các tín hiệu viết thường, tam_thoi, thông điệp khách) — xét theo thứ tự.
#: Thông điệp khai báo lúc nạp module ⇒ `N_()` (đánh dấu để trích, dịch lúc hiển thị
#: — xem `manifest.py`/`platform_core/i18n.py`), không phải `_()`.
_BANG: tuple[tuple[str, tuple[str, ...], bool, str], ...] = (
    ("gioi_han_tuoi",
     ("confirm your age", "age-restricted", "age restricted", "inappropriate for some users"),
     False, N_("Video bị giới hạn tuổi, không tải được.")),
    ("yt_bot", ("sign in to confirm", "not a bot"),
     True, N_("YouTube tạm chặn truy cập tự động. Vui lòng thử lại sau.")),
    # Smoke mạng thật 22/09 (Instagram, Douyin): thử lại ẩn danh không bao giờ khỏi ⇒ tam_thoi=False.
    ("can_dang_nhap", ("login required", "fresh cookies", "cookies for the authentication"),
     False, N_("Nền tảng yêu cầu đăng nhập — thêm phiên ở mục Đăng nhập nền tảng rồi thử lại.")),
    # Smoke thật 22/09 (Bilibili 412 = risk control với truy cập ẩn danh từ máy chủ).
    ("nen_chan", ("http error 412", "precondition failed", "http error 461"),
     False, N_("Nền tảng đang chặn truy cập ẩn danh từ máy chủ — thêm phiên ở mục Đăng nhập nền tảng rồi thử lại.")),
    # N8: extractor yt-dlp hỏng khi nền đổi trang (facebook "Cannot parse data", tiktok "Unexpected response from
    # webpage request"). Tạm thời: một lượt thử lại (features.SO_LAN_THU = 2), rồi chờ bản yt-dlp mới.
    # Xét TRƯỚC rieng_tu/khong_ton_tai: id/URL trong câu thô có thể chứa "private", "sign in"...
    ("trich_xuat_hong", ("cannot parse data", "unexpected response from webpage request"),
     True, N_("Nền tảng vừa đổi cấu trúc trang, công cụ đang chờ cập nhật. Vui lòng thử lại sau.")),
    # Sự cố nghiệm thu production 23/09: worker (LocalSystem) không thấy ffmpeg ⇒ MỌI lượt tải hỏng với
    # "lỗi không xác định". Đây là lỗi CẤU HÌNH MÁY CHỦ: khách không sửa được, thử lại cũng hỏng y hệt.
    ("thieu_ffmpeg", ("but ffmpeg is not installed", "ffmpeg not found", "ffprobe and ffmpeg not found",
                      "ffmpeg is not installed"),
     False, N_("Máy chủ chưa sẵn sàng ghép video. Chúng tôi đã ghi nhận — vui lòng thử lại sau.")),
    ("chi_la_anh", ("no video formats found",),
     False, N_("Bài đăng này không có video (chỉ có ảnh).")),
    ("url_khong_ho_tro", ("unsupported url", "no suitable extractor"),
     False, N_("Link không được hỗ trợ cho nền tảng này.")),
    ("yt_403", ("unable to download video data", "http error 403"),
     True, N_("YouTube từ chối tải video này lúc này. Vui lòng thử lại sau.")),
    ("rieng_tu", ("private", "members-only", "members only", "join this channel", "sign in"),
     False, N_("Video ở chế độ riêng tư hoặc chỉ dành cho thành viên.")),
    ("khong_ton_tai", ("unavailable", "has been removed", "removed by", "does not exist",
                       "no longer available", "http error 404", "been terminated"),
     False, N_("Video không tồn tại hoặc đã bị gỡ.")),
    ("mang", ("timed out", "timeout", "connection reset", "connection refused", "connection aborted",
              "forcibly closed", "getaddrinfo failed", "name resolution", "network is unreachable",
              "remote end closed", "incompleteread", "network connection error"),
     True, N_("Lỗi mạng khi kết nối tới nền tảng. Vui lòng thử lại sau.")),
)

_LOG = logging.getLogger(__name__)

_KHAC = N_("Không tải được video do lỗi không xác định. Vui lòng thử lại sau.")


def phan_loai(thong_diep: str) -> LoiCao:
    """Văn bản lỗi yt-dlp ⇒ LoiCao có mã, cờ tạm thời và câu báo khách an toàn."""
    low = (thong_diep or "").lower()
    if "fragment" in low and "403" in low:        # donor W:4930 — tra theo MÃ, không theo vị trí (review lần 2)
        cau = next(c for ma, _t, _tt, c in _BANG if ma == "yt_403")
        return LoiCao("yt_403", cau, tam_thoi=True)
    for ma, tin_hieu, tam_thoi, cau in _BANG:
        if any(t in low for t in tin_hieu):
            return LoiCao(ma, cau, tam_thoi=tam_thoi)
    # ⛔ Không nuốt: một lỗi CHƯA phân loại mà im lặng thì mọi lỗi mới trông giống hệt nhau (23/09). Văn bản gốc
    # chỉ vào LOG VẬN HÀNH; câu cho khách vẫn là câu chung.
    _LOG.warning("video_crawler: loi chua phan loai duoc: %s", (thong_diep or "")[:500])
    return LoiCao("loi_khac", _KHAC, tam_thoi=True)


def cho_khach(error: str | None) -> str:
    """`Job.error` ⇒ câu được phép hiện cho KHÁCH (đã dịch). Một nguồn: `platform_core.jobs.loi_cho_khach`.

    Trước W4 hàm này giữ BẢNG SO KHỚP NGUYÊN VĂN của riêng app — câu có biến (kho tài khoản: "{ten} tạm không
    khả dụng…") không bao giờ khớp nên khách nhận câu chung. Nay nền tảng đánh dấu `LoiNguoiGoi(<lớp>): …` ngay
    lúc ngoại lệ còn sống (`jobs.mo_ta_loi`), nên mọi câu app CỐ Ý viết cho khách đều tới đúng, còn lỗi hệ thống
    vẫn thành câu chung.
    """
    from types import SimpleNamespace

    from platform_core.jobs import loi_cho_khach
    from platform_core.models import JOB_ERROR
    return loi_cho_khach(SimpleNamespace(status=JOB_ERROR, error=error))
