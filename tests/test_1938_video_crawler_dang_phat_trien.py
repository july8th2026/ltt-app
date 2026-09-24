"""
video_crawler — nền CHƯA CHẠY ĐƯỢC phải nói ra, và "không có kết quả" không được im lặng (23/09/2026).

🔴 Đo thật trên production 23/09 bằng kho tài khoản hệ thống (`nguon_phien: "kho"`, cookie đã dùng thật):
- **Douyin**: job `kham_pha` "xong" sau 1,3 s với `muc: []` — nền trả RỖNG, không lỗi. Giao diện có nói
  ("Không tìm thấy video nào." — đo lại 23/09; lần đo đầu tôi kết luận nhầm là im lặng vì chỉ đếm số mục),
  nhưng câu đó ĐỔ LỖI CHO TỪ KHOÁ trong khi thật ra cả nền chưa chạy được — khách sẽ thử lại vô ích.
- **TikTok**: `ERROR: No working app info is available` (yt-dlp) ⇒ "lỗi không xác định".
- **Xiaohongshu**: chưa có tài khoản nào trong kho.

Chủ dự án chốt 23/09: các nền chưa chạy được thì **ghim "Đang phát triển"**, làm sau. Ba mệnh đề ở đây:
1. trạng thái ghim nằm ở REGISTRY (một nguồn) — không rải chuỗi trong template hay route;
2. nền đang phát triển bị từ chối NGAY ở cửa vào với câu cho khách, không nhận job rồi trả rỗng;
3. nền ĐANG CHẠY mà xem trước ra 0 mục vẫn phải nói "Không tìm thấy video nào" (giữ nguyên hành vi đã có).
"""
from __future__ import annotations

import pytest

_DNS = lambda host: ["1.2.3.4"]  # noqa: E731


def test_registry_ghim_dang_phat_trien_dung_ba_nen_da_do():
    from apps.video_crawler import nen_tang
    dpt = {n.id for n in nen_tang.cac_nen_bat() if n.dang_phat_trien}
    assert dpt == {"douyin", "tiktok", "xiaohongshu"}, dpt
    assert nen_tang.lay("youtube").dang_phat_trien is False


def test_moi_nen_dang_phat_trien_co_LY_DO_doc_duoc():
    """Ghim mà không nói vì sao thì lần sau không ai biết nên gỡ ghim khi nào."""
    from apps.video_crawler import nen_tang
    for n in nen_tang.cac_nen_bat():
        if n.dang_phat_trien:
            assert n.ly_do_dpt and len(n.ly_do_dpt) > 15, n.id


@pytest.mark.parametrize("nen_id, che_do", [
    ("douyin", "tu_khoa"), ("douyin", "kenh"), ("tiktok", "tu_khoa"), ("xiaohongshu", "tu_khoa"),
])
def test_nen_dang_phat_trien_bi_tu_choi_o_CUA_VAO(nen_id, che_do):
    from apps.video_crawler import features
    with pytest.raises(features.LoiDauVao, match="phát triển"):
        features.dung_params_kham_pha(owner_id="u1", nen_tang=nen_id, che_do=che_do, dau_vao="meo",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS, db=None)


def test_nen_dang_phat_trien_cung_khong_tai_duoc():
    from apps.video_crawler import features
    with pytest.raises(features.LoiDauVao, match="phát triển"):
        features.dung_params_tai(owner_id="u1", nen_tang="douyin",
                                 muc=[{"id": "1" * 19}], phan_giai=_DNS)


def test_nen_dang_chay_KHONG_bi_chan():
    """Đối chứng: ghim không được rộng tay — YouTube vẫn phải đi qua."""
    from apps.video_crawler import features
    p = features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="tu_khoa", dau_vao="meo con",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS, db=None)
    assert p["nen_tang"] == "youtube"


def test_giao_dien_ghim_nhan_tren_chip_nen():
    from apps.video_crawler import nen_tang
    goc = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "apps" / "video_crawler" / "templates" / "video_crawler.html").read_text(encoding="utf-8")
    assert "dang_phat_trien" in goc, "template phải đọc cờ từ registry, không khai tay danh sách nền"
    assert "Đang phát triển" in goc
    for n in nen_tang.cac_nen_bat():           # không nền nào bị viết cứng tên trong template
        assert f'"{n.id}" ==' not in goc


def test_xem_truoc_KHONG_CO_KET_QUA_phai_noi():
    """Bánh cóc giữ hành vi đã đúng: 0 mục vẫn phải có câu, đừng để ai bỏ nhánh `{% if not muc %}` đi."""
    goc = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "apps" / "video_crawler" / "templates" / "vc_ket_qua.html").read_text(encoding="utf-8")
    assert "Không tìm thấy video nào" in goc
