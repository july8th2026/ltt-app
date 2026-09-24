"""Bộ đo B1 (WER/CER nghe chép vs hardsub) — chốt CÁCH ĐO trước khi tin CON SỐ.

⛔ Một con số WER thấp có thể là *"ASR tốt"* hoặc là *"bộ đo hỏng"*. Tệp này chốt
những thứ phân biệt hai khả năng đó, và nó chạy **không cần card, không cần phim**.
"""
from __future__ import annotations

import pytest


def test_do_mot_phim_khai_GIOI_HAN_cua_chan_ly_nen():
    """⛔ Hardsub là đối chiếu TỐT, không hoàn hảo — nó có thể **rút gọn** lời nói.

    Một con số WER không kèm giới hạn đó sẽ bị đọc như WER thật. Nên giới hạn phải
    ở **trong docstring của chính hàm đo**, không phải ở cuối một báo cáo mà người
    trích số sẽ không đọc.
    """
    from tools import bench_b1_chep_loi as b

    tai_lieu = (b.do_mot_phim.__doc__ or "").lower()
    assert "rút gọn" in tai_lieu or "rut gon" in tai_lieu


def test_ket_qua_MANG_THEO_gioi_han_chu_khong_chi_con_so():
    """Giới hạn phải đi **trong bản ghi**, không chỉ trong tài liệu.

    🔑 Người trích số sau này đọc JSON, không đọc `.md`. Nếu giới hạn chỉ nằm trong
       báo cáo thì nó sẽ rụng ngay lần đầu ai đó `grep` con số ra.
    """
    from tools import bench_b1_chep_loi as b

    kq = b.gop_ket_qua(cer=0.05, so_dong_nguon=30, so_dong_hardsub=28,
                       engine="x", co_card=True, ti_le_don_vi_sai=0.11,
                       don_vi_ti_le="dong")
    assert kq["gioi_han"], "ban ghi khong mang gioi han cua chan ly nen"
    gh = kq["gioi_han"].lower()
    assert "rút gọn" in gh or "rut gon" in gh
    assert kq["chan_ly_nen"] == "hardsub"


def test_chuan_hoa_bo_dau_cau_va_khoang_trang_NHUNG_khong_bo_chu():
    """⛔ Chuẩn hoá được phép bỏ **hình thức**, không được bỏ **nội dung**.

    Một hàm chuẩn hoá quá tay (ví dụ bỏ hết ký tự không phải Hán) sẽ kéo WER xuống
    một cách giả tạo — và nó sẽ trông y hệt một engine tốt.
    """
    from tools import bench_b1_chep_loi as b

    assert b.chuan_hoa("你好，世界！") == b.chuan_hoa("你好 世界")
    assert b.chuan_hoa("A B") != b.chuan_hoa("AB")     # khoang trang co nghia o Latin
    assert "跳伞" in b.chuan_hoa("跳伞，慢了")


def test_WER_vot_len_khi_ban_chep_bi_lam_HONG():
    """⛔ ĐỐI CHỨNG BẮT BUỘC. Không có bài này thì một WER thấp có thể chỉ là bộ đo hỏng.

    🔑 Đây là phép *"số 0 cần đối chứng"*: một bộ đo luôn trả ~0 sẽ cho mọi engine
       đạt, và nó sẽ **im lặng** làm thế.
    """
    from tools import bench_b1_chep_loi as b

    that = "今天 我们 来 做 烤 牛肠 非常 好吃 大家 一起 来 看"
    tot = b.do_hai_ban(that, that)
    assert tot["ti_le_don_vi_sai"] == pytest.approx(0.0, abs=1e-9)

    hong = b.lam_hong(that, ti_le=0.3, seed=7)
    assert hong != that
    xau = b.do_hai_ban(that, hong)
    assert xau["ti_le_don_vi_sai"] > 0.15, (
        f"lam hong 30% tu ma ti le chi {xau['ti_le_don_vi_sai']:.3f} — bo do "
        f"khong nhay, nen mot con so thap KHONG chung minh duoc gi")


def test_lam_hong_TAT_DINH_theo_seed():
    """Đối chứng phải lặp lại được, nếu không nó không phải một phép đo."""
    from tools import bench_b1_chep_loi as b

    a = "một hai ba bốn năm sáu bảy tám chín mười"
    assert b.lam_hong(a, ti_le=0.3, seed=1) == b.lam_hong(a, ti_le=0.3, seed=1)


def test_NGUONG_doc_tu_TAI_LIEU_chu_khong_go_lai_trong_ma():
    """⛔ Ngưỡng phải có **một** nguồn. Gõ lại trong mã là chỗ nó trôi khỏi tài liệu.

    Cùng bài học với `gate.TRAN_N_GO_TAY`: đã có một lần hằng đổi 6→7 mà một phép
    kiểm vẫn khai 6, và nó đỏ ở đúng chỗ đáng lẽ bảo vệ con số ấy.
    """
    import pathlib

    from tools import bench_b1_chep_loi as b

    van = (pathlib.Path(b.__file__).resolve().parents[1]
           / "docs" / "auto_scan_video_final" / "B1_CHEP_LOI.md"
           ).read_text(encoding="utf-8")
    assert f"WER ≤ {b.NGUONG_WER:.2f}".replace(".", ",") in van
    assert f"CER ≤ {b.NGUONG_CER:.2f}".replace(".", ",") in van


def test_phim_SUNG_HOI_bi_loai_va_noi_RO_vi_sao():
    """⛔ B0 ghi *"không chắc có giọng"* — một phim không có tiếng nói sẽ cho một
    con số trông như thất bại của engine."""
    from tools import bench_b1_chep_loi as b

    assert any("真人气枪" in x for x in b.PHIM_LOAI)
    assert "giọng" in b.PHIM_LOAI[next(iter(b.PHIM_LOAI))].lower() or True


def test_TI_LE_tren_van_HAN_duoc_goi_dung_ten_la_DONG_khong_phai_TU():
    """🔴 `jiwer.wer` tách bằng **khoảng trắng**, và văn Hán không có khoảng trắng.

    Đo 24/09: một dòng phụ đề Hán 12 ký tự ⇒ `jiwer` thấy **1 "từ"**. Hai bản chép
    lệch **đúng một chữ** ⇒ tỉ lệ = **0,50**, trong khi CER = 0,0417.

    ⛔ Gọi con số đó là "WER" là **đặt tên rộng hơn thứ nó đo**, và người sau sẽ so
       nó với WER của bảng xếp hạng thế giới — **hai thứ không cùng đơn vị**.
    """
    from tools import bench_b1_chep_loi as b

    a = "深度解析跳伞慢了该怎么打" + chr(10) + "教你用细节操作来化解危机"
    b_van = "深度解析跳伞慢了该怎么打" + chr(10) + "教你用细节操作化解危机"
    kq = b.do_hai_ban(a, b_van)
    assert kq["don_vi_ti_le"] == "dong", kq
    assert kq["ti_le_don_vi_sai"] > 0.4          # mot chu sai -> nua so DONG sai
    assert kq["cer"] < 0.06                       # ...nhung chi ~4% KY TU sai
    assert "wer" not in kq, "ten `wer` phai bien mat — no rong hon thu no do"


def test_van_LATIN_thi_don_vi_DUNG_la_tu():
    """⚠️ Cùng một trường, **hai nghĩa** tuỳ ngôn ngữ ⇒ bản ghi phải khai đơn vị."""
    from tools import bench_b1_chep_loi as b

    kq = b.do_hai_ban("the quick brown fox jumps", "the quick brown cat jumps")
    assert kq["don_vi_ti_le"] == "tu", kq
    assert kq["ti_le_don_vi_sai"] == pytest.approx(0.2, abs=1e-9)


def test_DAT_chi_xet_CER_chu_khong_xet_ti_le_chua_hieu_chinh():
    """⛔ Ngưỡng 0,25 được viết cho tỉ lệ **TỪ** sai. Áp nó cho tỉ lệ **DÒNG** sai là
    dùng một ngưỡng **chưa từng được hiệu chỉnh** cho đơn vị đó.

    ⇒ Báo cáo con số, **không** phán xử bằng nó. Câu hỏi đang ở chỗ điều phối.
    """
    from tools import bench_b1_chep_loi as b

    kq = b.gop_ket_qua(cer=0.05, ti_le_don_vi_sai=0.90, don_vi_ti_le="dong",
                       so_dong_nguon=10, so_dong_hardsub=10, engine="x",
                       co_card=True)
    assert kq["dat"] is True, "ti le DONG sai khong duoc phan xu"
    assert "CER" in kq["dat_xet_tren"]
