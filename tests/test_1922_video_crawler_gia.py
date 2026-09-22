"""video_crawler — bảng giá MỘT nguồn theo thời lượng (`apps/video_crawler/gia.py`).

Nguồn: `docs/migrations/video_crawler/DANH_GIA_MVP.md` §3 (chốt chủ dự án 22/09): xem trước 0;
≤ 10 phút 3 credit; 10–30 phút 6; 30–60 phút 10; 60 phút – 3 giờ 15 credit/video. Giữ chỗ khi nộp job
luôn bằng bậc cao nhất (`GIA_GIU_CHO`); quyết toán bằng `gia_muc` theo thời lượng THẬT của mục đã tải
(`jobs.py`) — không có sàn ẩn (bài học memory "tiền và giá": không làm tròn lên để thu thêm).
"""
from __future__ import annotations

from itertools import pairwise

import pytest

from apps.video_crawler import gia


@pytest.mark.parametrize("giay,ky_vong", [
    (0, 3), (1, 3), (599, 3), (600, 3),            # <= 10 phút
    (601, 6), (1799, 6), (1800, 6),                # 10–30 phút
    (1801, 10), (3599, 10), (3600, 10),            # 30–60 phút
    (3601, 15), (10_799, 15), (10_800, 15),        # 60 phút – 3 giờ
])
def test_gia_muc_theo_bac_thoi_luong(giay, ky_vong):
    assert gia.gia_muc(giay) == ky_vong


def test_gia_muc_khong_ro_thoi_luong_dung_bac_re_nhat():
    """Adapter không báo thời lượng, hoặc mục đến trực tiếp từ danh sách id/url của khách (chưa qua khám
    phá) ⇒ bậc ≤ 10 phút — quyết định chủ dự án 22/09, không phải sàn giá cao nhất."""
    assert gia.gia_muc(None) == gia.BAC_GIA[0][1] == 3


def test_gia_muc_khong_am_va_khong_vuot_bac_cuoi_qua_3_gio():
    """Video > 3 giờ đã bị `qua_dai` chặn ở tầng adapter (_ytdlp.py:THOI_LUONG_TOI_DA_MAC_DINH = 3*3600)
    trước khi tới đây; đây chỉ là phòng hờ để giá không tăng vô hạn."""
    assert gia.gia_muc(-100) == 3
    assert gia.gia_muc(999_999) == 15


def test_gia_muc_kieu_du_lieu_la_khong_hop_le_dung_bac_re_nhat():
    assert gia.gia_muc("khong-phai-so") == 3


def test_giu_cho_la_bac_cao_nhat():
    assert gia.GIA_GIU_CHO == gia.BAC_GIA[-1][1] == 15


def test_bang_tra_du_bac_khong_am_khong_chong_cheo_khong_doi_trang_thai():
    bac = gia.bang()
    assert [b["gia"] for b in bac] == [3, 6, 10, 15]
    assert bac[0]["tu_s"] == 0
    for truoc, sau in pairwise(bac):
        assert truoc["den_s"] < sau["tu_s"]                # không hở, không chồng bậc
    assert gia.bang() == bac                                # đọc thuần, gọi lại không đổi kết quả
