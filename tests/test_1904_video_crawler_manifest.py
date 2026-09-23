"""
video_crawler — bản khai app + giá credit (spec §8, §12, §14, §26).

Mỗi phép kiểm dưới đây chốt một quyết định có lý do, ghi trong spec:
- requires=("api",) chứ không ("ffmpeg",): làn gpu+ffmpeg production chỉ có 1 worker (phản biện BLOCKER 1).
- `tai` có trần 7200 s riêng: tải + ghép video dài hơn trần 1800 s mặc định của lớp api.
- Khám phá miễn phí; tải giữ chỗ `gia.GIA_GIU_CHO` (bậc cao nhất) mỗi mục xin tải, quyết toán theo
  thời lượng thật của mục đã tải (`apps/video_crawler/gia.py` — bảng giá MỘT nguồn, DANH_GIA_MVP §3).
- Chưa mở bán: public=False, lifecycle development.
"""
from __future__ import annotations

from apps.video_crawler import gia
from apps.video_crawler.manifest import MANIFEST


def test_ban_khai_dung_hop_dong():
    m = MANIFEST
    assert m.slug == "video_crawler"
    assert m.route_prefix == "/video-crawler"
    assert set(m.job_types) == {"video_crawler.kham_pha", "video_crawler.tai"}
    assert m.requires == ("api",)
    assert m.max_runtime_s == {"video_crawler.tai": 7200}
    assert m.public is False
    assert m.lifecycle == "development"
    assert m.capabilities, "app customer không có catalog_parent phải khai capabilities (test_60:62-72)"


def test_kham_pha_mien_phi():
    assert MANIFEST.credit_cost({"nen_tang": "youtube", "che_do": "tu_khoa",
                                 "dau_vao": "meo", "so_luong": 20}) == 0


def test_tai_theo_danh_sach_giu_bac_cao_nhat_moi_muc():
    muc = [{"id": str(i), "url": f"https://www.youtube.com/watch?v={i}"} for i in range(3)]
    assert MANIFEST.credit_cost({"nen_tang": "youtube", "muc": muc}) == 3 * gia.GIA_GIU_CHO


def test_tai_theo_nguon_giu_cho_theo_so_luong():
    assert MANIFEST.credit_cost({"nen_tang": "youtube",
                                 "nguon": {"che_do": "kenh", "dau_vao": "@abc", "so_luong": 7}}) == 7 * gia.GIA_GIU_CHO


def test_gia_khong_bao_gio_am_hoac_vo_han():
    assert MANIFEST.credit_cost({"nen_tang": "youtube", "nguon": {"so_luong": -5}}) == 0
    assert MANIFEST.credit_cost({"nen_tang": "youtube", "nguon": {"so_luong": "x"}}) == 0
    assert MANIFEST.credit_cost({"nen_tang": "youtube", "nguon": {"so_luong": 10_000}}) == 20 * gia.GIA_GIU_CHO
