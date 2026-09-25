"""test_2062 — `apps/auto_scan_video/nan_thoi_luong.py`: `gop_khe` (D5).

⭐ Bộ kiểm này chạy ⛔ KHÔNG cần một lượt LLM, TTS hay GPU nào: `gop_khe` và
`xep_bac` đều là hàm thuần.

🔴 25/09: ba "cần gạt" khác từng ở đây (`can_gat_1_rut_gon`, `can_gat_2_phan_phoi`,
`can_gat_3_he_so`) + `con_khong_vua` đã **XOÁ** — trùng hoặc chết so với bậc
thang bốn nấc ĐANG CHẠY của `nan_cho_vua.py` (xem docstring đầu
`nan_thoi_luong.py`). Test cho `can_gat_3_he_so` (kẹp hệ số vào trần) không
mất phủ: `tests/test_441_asv_v4_nan_cho_vua.py::test_co_gian_bi_chan_boi_TRAN_da_khai`
kiểm đúng hành vi đó trên `nan_cho_vua.co_gian_du_khong`.
"""
from __future__ import annotations

from apps.auto_scan_video import nan_thoi_luong
from apps.auto_scan_video.nan_thoi_luong import (AM_TIET_MOI_GIAY, BacNan, Khe,
                                                 TRAN_KY_TU_MOT_LUOT,
                                                 gop_khe, xep_bac)

TRAN = 1.15


def _khe(ma: str, bat: float, dai: float, am: int, chu: str = "x") -> Khe:
    return Khe(ma=ma, bat=bat, ket=bat + dai, moc_sau=bat + dai, am_tiet=am, chu=chu)


def test_2062_gop_khe_keo_khe_CHAT_ve_VUA_bang_khe_RONG_ke_ben():
    """Khe chật + khe rộng liền sau ⇒ gộp lại thì vừa. ⛔ Không chạm bản dịch."""
    chat = _khe("a", 0.0, 2.0, 20)      # cần ~6,1 s, chỉ có 2 s
    rong = _khe("b", 2.0, 8.0, 5)       # cần ~1,5 s, có 8 s
    assert xep_bac(chat, tran_tang_toc=TRAN) == BacNan.QUA_NHANH

    ra = gop_khe([chat, rong], tran_tang_toc=TRAN)
    assert len(ra) == 1, "hai khe phai thanh MOT"
    assert ra[0].am_tiet == 25
    # ⭐ "VUA" = `<= BINH_THUONG`, ⛔ khong phai `== BINH_THUONG`: mot khe rong
    #    rai cho `QUA_CHAM` (-1), va do VAN la vua. Cung vi the ma
    #    `can_gat_1_rut_gon` loc bang `> BacNan.BINH_THUONG`.
    assert xep_bac(ra[0], tran_tang_toc=TRAN) <= BacNan.BINH_THUONG


def test_2062_gop_khe_KHONG_dong_vao_khe_da_vua():
    """⛔ Không báo động giả: khe đã vừa thì ⛔ không bị gộp với ai."""
    a = _khe("a", 0.0, 10.0, 5)
    b = _khe("b", 10.0, 10.0, 5)
    ra = gop_khe([a, b], tran_tang_toc=TRAN)
    assert [k.ma for k in ra] == ["a", "b"]


def test_2062_TIEM_ban_SUY_BIEN_gop_tu_do_bi_TRAN_KY_TU_chan():
    """🔴 Chốt đã CỨU một lần thật (25/09).

    Bỏ trần ký tự thì phép gộp nhồi **74 khe vào MỘT**, văn bản **3.535 ký tự**
    — vượt `TRAN_MOI_LUOT_SINH = 1500` ⇒ máy đọc **từ chối**. Một bản suy biến
    đeo mặt một kết quả tốt (p95 1,171 so với 1,559).

    ⇒ Phép kiểm đòi: trần ký tự **chặn** được nó, và ⛔ không khe nào vượt trần.
    """
    # 200 khe chật liên tiếp, mỗi khe 60 ký tự ⇒ gộp vô hạn sẽ vượt xa 1500
    khes = [_khe(f"s{i}", i * 1.0, 1.0, 30, "y" * 60) for i in range(200)]

    ra = gop_khe(khes, tran_tang_toc=TRAN, tran_gop=10 ** 6)
    assert all(len(k.chu) <= TRAN_KY_TU_MOT_LUOT for k in ra), (
        "tran ky tu KHONG chan duoc ban suy bien")
    assert len(ra) > 1, "gop tat ca vao MOT khe la ban suy bien"


def test_2062_gop_khe_ton_trong_TRAN_GOP():
    """⛔ Không gộp quá `tran_gop` khe, kể cả khi vẫn chưa vừa."""
    khes = [_khe(f"s{i}", i * 1.0, 1.0, 30) for i in range(20)]
    ra = gop_khe(khes, tran_tang_toc=TRAN, tran_gop=3)
    # mỗi khe ra gộp nhiều nhất 3 khe vào ⇒ tổng âm tiết <= 3 × 30
    assert max(k.am_tiet for k in ra) <= 90
    assert len(ra) >= len(khes) // 3


def test_2062_BA_can_gat_TRUNG_da_XOA_khong_song_lai():
    """25/09: `can_gat_1_rut_gon`/`can_gat_2_phan_phoi`/`can_gat_3_he_so` +
    `con_khong_vua` đã xoá (trùng/chết so với `nan_cho_vua.py`).

    ⭐ Canh chỗ trống: một tên nào trong bốn tên này sống lại mà ⛔ không đối
       chiếu lại với `nan_cho_vua.py` là đúng cái bẫy "hai chỗ khai cùng một
       điều" kho này đã trả giá — xem docstring đầu `nan_thoi_luong.py`.
    """
    for ten in ("can_gat_1_rut_gon", "can_gat_2_phan_phoi", "can_gat_3_he_so",
                "con_khong_vua"):
        assert not hasattr(nan_thoi_luong, ten), f"{ten} đã xoá nhưng sống lại"


def test_2062_toc_do_noi_la_so_DO_DUOC_khong_phai_so_muon():
    """⭐ `AM_TIET_MOI_GIAY` đo trên 18 đoạn TTS thật, dải [3,00 ; 3,71].

    ⛔ Ai thay nó bằng một hằng số mượn của dự án khác thì phép kiểm này đỏ.
    """
    assert 3.0 <= AM_TIET_MOI_GIAY <= 3.71
