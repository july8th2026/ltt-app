"""Nguồn lời thoại mặc định là **ASR** — luồng chính chạy thật lần đầu (Task 5).

## Vì sao đổi mặc định

🔴 Chủ dự án chốt 24/09: sản phẩm là **lồng tiếng voice→voice**; hardsub chỉ để
**đối chiếu**.

⛔ Đo B0: cả **4** phim mẫu có hardsub Hán 98,8–100 % ⇒ với `auto` thì **cả bốn** đi
đường `ocr`. Xác nhận lại ở lượt A/B/C 24/09 trên phim `v3`:

```
transcribe  nguon_loi = "ocr"   engine = rapidocr/3.9.2+PP-OCRv6_small
            dinh_tuyen = {che_do: "auto", ly_do: ["khong_co_phu_de_nhung"]}
```

⇒ Đường `asr` — **luồng chính** — **chưa từng chạy thật một lần nào**, và mọi con số
của ba lượt nghiệm thu đều nói về đường phụ.

## ⛔ Nộp form KHÔNG phải bằng chứng — phải đọc lại hồ sơ ĐÃ LƯU

Điều kiện điều phối đặt cho Task 5, và nó có lý do cụ thể trong sổ lỗi: **G-01** —
`dich_vu_tao.dung_cai_dat` từng **duyệt** `nguon_loi` rồi **không ghi vào hồ sơ trả
về**, nên khách ép `embedded`/`ocr`/`asr` vẫn chạy `auto`, **im lặng**. Không phép
kiểm đơn lẻ nào kêu được, vì mỗi phép chỉ hỏi **một mắt xích** và `auto` là một kết
quả hợp lệ.

⇒ Nên tệp này chốt **đường dây**: ép một giá trị vào cửa, rồi **đọc lại hồ sơ đã
lưu** và so. ⛔ Không chốt bằng "cửa nhận giá trị mà không báo lỗi".
"""
from __future__ import annotations

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong


def test_mac_dinh_la_ASR_vi_san_pham_la_long_tieng_voice_to_voice():
    """🔴 Chủ dự án chốt 24/09: sản phẩm là lồng tiếng voice→voice."""
    from apps.auto_scan_video import nguon_loi

    assert nguon_loi.CHE_DO_MAC_DINH == nguon_loi.ASR


def test_auto_van_con_la_mot_lua_chon_hop_le():
    """Đổi mặc định, ⛔ KHÔNG xoá `auto` — khách vẫn chọn được.

    ⚠️ Đây là phép kiểm chống **sửa quá tay**: cách dễ nhất để làm bài trên xanh là
       xoá `auto` khỏi miền giá trị, và nó sẽ lấy đi một lựa chọn của khách.
    """
    from apps.auto_scan_video import nguon_loi

    assert nguon_loi.chuan_che_do("auto") == nguon_loi.AUTO
    assert nguon_loi.AUTO in nguon_loi.CHE_DO_HOP_LE


def test_moi_che_do_van_ep_duoc_chu_khong_chi_mac_dinh():
    """Bốn chế độ vẫn là bốn — đổi mặc định không được thu hẹp miền giá trị."""
    from apps.auto_scan_video import nguon_loi

    for ma in (nguon_loi.AUTO, nguon_loi.EMBEDDED, nguon_loi.OCR, nguon_loi.ASR):
        assert nguon_loi.chuan_che_do(ma) == ma


# ══════════════════════════════════════════════════════════════════════════════
#  G-01: ĐỌC LẠI HỒ SƠ ĐÃ LƯU — nộp form không phải bằng chứng
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ep", ["asr", "ocr", "embedded", "auto"])
def test_ep_nguon_loi_thi_HO_SO_DA_LUU_mang_dung_gia_tri_do(moi_truong, ep):  # noqa: F811
    """⛔ **Đường dây**, không phải một mắt xích.

    🔴 G-01: `dung_cai_dat` **duyệt** `nguon_loi` rồi **không đặt vào hồ sơ trả về**
       ⇒ khách ép `asr` vẫn chạy `auto`, im lặng. Cửa không báo lỗi, phép kiểm của
       cửa xanh, phép kiểm của `nguon_loi` xanh — và sản phẩm vẫn sai.

    ⇒ Bài này ép **qua chính `dung_cai_dat`** rồi **đọc lại** giá trị trong hồ sơ.
    """
    import platform_core.db as dbmod

    from apps.auto_scan_video import dich_vu_tao
    from platform_core.models import User

    db = next(dbmod.get_session())
    try:
        chu = db.query(User).order_by(User.id).first()
        assert chu is not None
        ho_so = dich_vu_tao.dung_cai_dat(
            db, owner_id=chu.id,
            tho={"che_do_giong": "AUTO_MATCH", "nguon_loi": ep})
    finally:
        db.close()

    # ⛔ Đọc qua `tu_ho_so` — ĐƯỜNG GIẢI MÃ THẬT — chứ không `ho_so.get(...)` thô.
    #
    # 🔑 `chuan_hoa` **bỏ** khoá khi nó bằng `CHE_DO_HO_SO_CU` (`auto`), có chủ ý:
    #    hồ sơ (và vân tay) của mọi lần chạy trước 22/09 giữ nguyên hình dạng. Nên
    #    một phép kiểm đọc dict thô sẽ báo `None` cho `auto` và người đọc sẽ tưởng
    #    G-01 tái phát — trong khi đó là luật `KHOA_THUA` đang làm đúng việc.
    from apps.auto_scan_video import cai_dat as cai_dat_mod

    doc_lai = cai_dat_mod.tu_ho_so(ho_so).nguon_loi
    assert doc_lai == ep, (
        f"ep `nguon_loi={ep}` nhung doc lai duoc {doc_lai!r} — dung hinh dang "
        f"G-01: cua DUYET gia tri roi KHONG GHI")


def test_khong_ep_gi_thi_HO_SO_mang_ASR_chu_khong_mang_auto(moi_truong):  # noqa: F811
    """Mặc định mới phải đi **tới hồ sơ**, không dừng ở hằng số.

    ⚠️ Một hằng `CHE_DO_MAC_DINH = ASR` mà hồ sơ vẫn ghi `auto` là đúng lớp lỗi
       G-01, chỉ ở chiều ngược lại.
    """
    import platform_core.db as dbmod

    from apps.auto_scan_video import dich_vu_tao, nguon_loi
    from platform_core.models import User

    db = next(dbmod.get_session())
    try:
        chu = db.query(User).order_by(User.id).first()
        ho_so = dich_vu_tao.dung_cai_dat(db, owner_id=chu.id,
                                         tho={"che_do_giong": "AUTO_MATCH"})
    finally:
        db.close()

    from apps.auto_scan_video import cai_dat as cai_dat_mod

    assert cai_dat_mod.tu_ho_so(ho_so).nguon_loi == nguon_loi.ASR


# ══════════════════════════════════════════════════════════════════════════════
#  ⛔ Cái bẫy Task 5 suýt giẫm: một hằng số làm BA việc
# ══════════════════════════════════════════════════════════════════════════════

def test_HAI_hang_so_RIENG_cho_hai_nghia_khac_nhau():
    """🔴 Trước 24/09 một hằng làm **ba** việc cùng lúc:

        1. mặc định cho một **yêu cầu mới** khi khách không chọn gì;
        2. nghĩa của **khoá vắng mặt** khi ĐỌC một hồ sơ đã lưu (`cai_dat:136`);
        3. giá trị bị **bỏ đi** khi GHI (`cai_dat:203`, luật `KHOA_THUA`).

    ⛔ Lật một mình nó sẽ **viết lại nghĩa của mọi hồ sơ đã lưu**: một lần chạy lưu
       với `auto` (khoá bị bỏ vì nó là mặc định) sẽ được đọc lại thành `asr`. Và
       chính chú thích ở `cai_dat.py` — *"Hồ sơ cũ không có khoá = `auto`"* — trở
       thành **SAI** ngay khoảnh khắc đó, không gì kêu lên.

    ⭐ Cùng họ với bài học *"hai trạng thái gộp thành một giá trị"*: **vắng mặt**
       nghĩa là **mặc định**, và mặc định là một mục tiêu **di động**. Tách ra thì
       nó đứng yên.
    """
    from apps.auto_scan_video import nguon_loi

    assert nguon_loi.CHE_DO_MAC_DINH == nguon_loi.ASR, "yeu cau moi"
    assert nguon_loi.CHE_DO_HO_SO_CU == nguon_loi.AUTO, "khoa vang mat, DONG BANG"
    assert nguon_loi.CHE_DO_MAC_DINH != nguon_loi.CHE_DO_HO_SO_CU


def test_HO_SO_CU_khong_co_khoa_van_doc_ra_AUTO():
    """⛔ Hồ sơ lưu **trước** 24/09 không mang khoá `nguon_loi` (vì hồi đó `auto` là
    mặc định nên bị `KHOA_THUA` bỏ). Nó phải vẫn đọc ra `auto`.

    Đây là phép kiểm **chống hồi quy dữ liệu**, không phải phép kiểm hành vi: nó
    hỏi *"ta có vừa đổi nghĩa của thứ đã nằm trên đĩa không"*.
    """
    from apps.auto_scan_video import cai_dat as cai_dat_mod
    from apps.auto_scan_video import nguon_loi

    ho_so_cu = {"timing_mode": "fit_original", "preset": "localize_preserve_picture"}
    assert "nguon_loi" not in ho_so_cu
    assert cai_dat_mod.tu_ho_so(ho_so_cu).nguon_loi == nguon_loi.AUTO


def test_auto_van_bi_BO_khi_GHI_de_van_tay_ho_so_cu_khong_doi():
    """`auto` vẫn bị bỏ khi ghi ⇒ vân tay của hồ sơ cũ **không đổi**.

    ⚠️ Nếu dòng bỏ-khoá bám theo mặc định **hiện hành** thì từ 24/09 `asr` bị bỏ và
       `auto` được ghi — tức **mọi** hồ sơ cũ đổi hình dạng, `thi_hanh.van_tay` đổi
       theo, và `jobs._vo_hieu_giai_doan_da_lech` **đặt lại** `media_prepare`,
       `audio_prepare`, `transcribe`, `edit_plan` của chúng. Đúng 133 giây mà lượt A
       của `NEN_V3` đã đốt, lần này đốt cho mọi lần chạy đã có.
    """
    from apps.auto_scan_video import cai_dat as cai_dat_mod
    from apps.auto_scan_video import nguon_loi

    goc = {"timing_mode": "fit_original", "preset": "localize_preserve_picture"}
    assert "nguon_loi" not in cai_dat_mod.chuan_hoa(dict(goc, nguon_loi="auto"))
    assert cai_dat_mod.chuan_hoa(dict(goc, nguon_loi="asr"))["nguon_loi"] == "asr"
    # Luỹ đẳng — bất biến `chuan_hoa(chuan_hoa(x)) == chuan_hoa(x)`.
    mot = cai_dat_mod.chuan_hoa(dict(goc, nguon_loi=nguon_loi.ASR))
    assert cai_dat_mod.chuan_hoa(mot) == mot
