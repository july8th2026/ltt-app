"""test_4700 — `gop_khe` ĐIỀU KHIỂN THẬT: luật gộp, bất biến `ban_ke`, nhãn ngắn.

⭐ Bộ kiểm này chạy ⛔ KHÔNG cần một lượt LLM, TTS, GPU hay ASV nào: mọi thứ nó
chạm đều là hàm thuần, và bảng ký tự/giây đo trên **bằng chứng đã commit**
(`docs/auto_scan_video_final/bang_chung/{b1_chep_loi_moi,b2_dich_nen}`).

## Sáu phép nghiệm thu (brief `b2-gop-khe`, 25/09/2026)

    1  hai đoạn cách 0,4 s, câu chưa kết thúc      -> GỘP
    2  hai đoạn cách 0,9 s                         -> ⛔ KHÔNG gộp (> 0,6 s)
    3  năm đoạn đủ điều kiện                       -> gộp tối đa 4
    4  khe gộp -> `ban_ke` có dòng cho MỌI `ma` -> `lap_ke_hoach` ⛔ không ném
    5  đoạn quá NGẮN -> trạng thái/ghi chú ⛔ không nói "co giãn"
    6  ký tự/giây trước/sau trên dữ liệu thật — bảng số
"""
from __future__ import annotations

import json
import pathlib
import statistics as st

import pytest

from apps.auto_scan_video import nan_cho_vua, nan_thoi_luong as nt, phu_de, thoi_gian

TRAN = 1.15                     # `thoi_gian.TRAN_TANG_TOC`
BC = (pathlib.Path(__file__).resolve().parents[1] / "docs"
      / "auto_scan_video_final" / "bang_chung")


def _khe(ma: str, bat: float, dai: float, am: int, chu: str = "x",
         moc_sau: float | None = None) -> nt.Khe:
    ket = bat + dai
    return nt.Khe(ma=ma, bat=bat, ket=ket,
                  moc_sau=ket if moc_sau is None else moc_sau,
                  am_tiet=am, chu=chu)


# ── 1–3: LUẬT GỘP, mượn `localize._nhom_gop_capcut()` ────────────────────────

def test_4700_gop_khi_khe_giua_0_4s_va_cau_CHUA_ket_thuc():
    """Phép 1. Khe giữa 0,4 s ≤ `TRAN_KHE_GIUA_S` (0,6) ⇒ gộp."""
    a = _khe("a", 0.0, 1.0, 20, "mot cau chua het")     # 20 âm tiết / 1 s: chật
    b = _khe("b", 1.4, 6.0, 4, "roi het")
    ra = nt.gop_khe([a, b], tran_tang_toc=TRAN)
    assert [k.ma for k in ra] == ["a"], "hai doan phai thanh MOT khe"
    assert ra[0].am_tiet == 24
    assert ra[0].ket == pytest.approx(7.4)


def test_4700_KHONG_gop_khi_khe_giua_0_9s():
    """Phép 2. 0,9 s > `TRAN_KHE_GIUA_S` ⇒ ⛔ không gộp, dù mọi điều kiện khác đủ.

    🔑 Đây là con số của bot Viral (`DUB_GOP_KHE = 0,6 s`), và nó phân biệt *"hai
       câu trong cùng một hơi"* với *"hai cảnh khác nhau"*: gộp qua một khoảng
       lặng 0,9 s là dán khoảng lặng ấy vào GIỮA một lượt đọc liền mạch.
    """
    a = _khe("a", 0.0, 1.0, 20, "mot cau chua het")
    b = _khe("b", 1.9, 6.0, 4, "roi het")
    ra = nt.gop_khe([a, b], tran_tang_toc=TRAN)
    assert [k.ma for k in ra] == ["a", "b"]


def test_4700_gop_toi_da_BON_doan_doan_thu_nam_sang_khe_moi():
    """Phép 3. `TRAN_GOP_KHE = 4` (Viral `DUB_GOP_MAX`) ⇒ đoạn thứ năm sang nhóm mới."""
    assert nt.TRAN_GOP_KHE == 4, "tran gop phai la 4 (Viral DUB_GOP_MAX)"
    khes = [_khe(f"s{i}", i * 1.0, 1.0, 20, "cau chua het") for i in range(5)]
    nhom = nt.nhom_chi_so(khes, tran_tang_toc=TRAN)
    assert [len(g) for g in nhom] == [4, 1]
    assert nhom[0] == [0, 1, 2, 3] and nhom[1] == [4]


def test_4700_cau_DA_KET_THUC_thi_dung_lai():
    """`con_tiep` (Viral `_con_tiep`): ⛔ không gộp qua một dấu kết câu.

    ⚠️ Đo trên dữ liệu thật: **64/185 cặp** bị chặn đúng ở đây — điều kiện có
       hiệu lực NHẤT trong bốn điều kiện mượn về
       (`bang_chung/b2_gop_khe/ket_qua_vi_sao.json`).
    """
    assert nt.con_tiep("con tiep") is True
    assert nt.con_tiep("da het.") is False
    assert nt.con_tiep('da het."') is False, "dau ngoac sau dau cau khong doi gi"
    assert nt.con_tiep("") is False, "doan rong: 'khong biet' != 'con tiep'"

    a = _khe("a", 0.0, 1.0, 20, "mot cau da het.")
    b = _khe("b", 1.0, 6.0, 4, "cau sau")
    assert [k.ma for k in nt.gop_khe([a, b], tran_tang_toc=TRAN)] == ["a", "b"]


def test_4700_moi_hang_so_gop_TU_KHAI_NGUON():
    """⭐ Bốn hằng số đều mượn từ một hệ ĐÃ CHẠY THẬT, và nói ra điều đó.

    ⛔ Ai đổi một con số mà ⛔ không đổi nguồn trong chú thích thì phép kiểm này đỏ.
    """
    doc = nt.__doc__ or ""
    import inspect
    ma_nguon = inspect.getsource(nt)
    for ten, nguon in (("TRAN_GOP_KHE", "DUB_GOP_MAX"),
                       ("TRAN_KHE_GIUA_S", "DUB_GOP_KHE"),
                       ("TRAN_KY_TU_GOP", "DUB_GOP_KYTU")):
        i = ma_nguon.index(f"{ten} = ")
        khoi = ma_nguon[max(0, i - 2000):i]
        assert nguon in khoi, f"{ten} khong khai nguon {nguon}"
    assert "MAX_MERGE_COUNT" in ma_nguon, "thieu nguon doc lap VideoLingo"
    assert doc


# ── 4: BẤT BIẾN `ban_ke` — không một `ma` nào biến mất ───────────────────────

def _muc(ma: str, bat: float, ket: float, chu: str) -> dict:
    return {"ma": ma, "bat": bat, "ket": ket, "chu": chu, "goc": chu}


def test_4700_khe_gop_van_co_mot_dong_ban_ke_cho_MOI_ma_goc():
    """Phép 4a. `no_ban_ke` phủ kín nhóm, và tổng `giay` = độ dài THẬT của tệp."""
    tv = [_muc("a", 0.0, 1.0, "mot hai ba"),        # 3 âm tiết
          _muc("b", 1.0, 2.0, "bon nam"),           # 2
          _muc("c", 2.0, 3.0, "sau")]               # 1
    dong = nt.no_ban_ke({"ma": "a", "khoa": "k/a.wav", "giay": 6.0,
                         "chu": "mot hai ba bon nam sau"}, tv)
    assert [d["ma"] for d in dong] == ["a", "b", "c"]
    assert sum(float(d["giay"]) for d in dong) == pytest.approx(6.0)
    # chia THEO ÂM TIẾT, ⛔ không chia đều
    assert [round(float(d["giay"]), 3) for d in dong] == [3.0, 2.0, 1.0]
    # dòng đầu SỞ HỮU tệp, hai dòng sau ĐI THEO — hai loại phân biệt được
    assert dong[0][nt.KHOA_GOP] == ["a", "b", "c"]
    assert dong[0][nt.KHOA_GIAY_TEP] == pytest.approx(6.0)
    assert not nt.la_dong_theo_sau(dong[0])
    assert all(nt.la_dong_theo_sau(d) for d in dong[1:])
    assert all(d["khoa"] == "k/a.wav" for d in dong), "cung MOT tep"


def test_4700_nhom_MOT_thanh_vien_cung_mot_hinh_dang():
    """⛔ Không hai hình dạng cho câu hỏi *"dòng này phủ những `ma` nào"*."""
    dong = nt.no_ban_ke({"ma": "a", "khoa": "k.wav", "giay": 2.0, "chu": "mot"},
                        [_muc("a", 0.0, 1.0, "mot")])
    assert len(dong) == 1
    assert dong[0][nt.KHOA_GOP] == ["a"]
    assert not nt.la_dong_theo_sau(dong[0])


def test_4700_lap_ke_hoach_KHONG_NEM_tren_mot_khe_da_gop():
    """Phép 4b. 🔴 Chính bất biến `giai_doan_thoi_gian.py:88-89`.

    `content.json` được ghi TRƯỚC và ĐỘC LẬP với `voice_synthesis`: mọi `ma` của
    nó phải có một dòng `giay` trong `ban_ke.json`, nếu không `thoi_gian.py` ném
    `ThoiGianError('Doan {ma} chua co tieng.')` trên **mọi** lượt chạy có gộp.
    """
    muc = [_muc("a", 0.0, 1.0, "mot hai ba"),
           _muc("b", 1.0, 2.0, "bon nam"),
           _muc("c", 2.0, 3.0, "sau"),
           _muc("d", 4.0, 8.0, "mot minh mot khe.")]
    dong = nt.no_ban_ke({"ma": "a", "khoa": "k/a.wav", "giay": 3.0,
                         "chu": "mot hai ba bon nam sau"}, muc[:3])
    dong += nt.no_ban_ke({"ma": "d", "khoa": "k/d.wav", "giay": 3.5,
                          "chu": "mot minh mot khe."}, muc[3:])
    ban_ke = {"schema": 1, "doan": dong}

    do_dai = {str(d["ma"]): float(d["giay"]) for d in dong}
    assert set(do_dai) == {"a", "b", "c", "d"}, "khong mot `ma` nao bien mat"

    ke = thoi_gian.lap_ke_hoach(muc, do_dai, tong_giay=12.0,
                                nhom_gop=nt.nhom_theo_ma(ban_ke))
    assert [d["ma"] for d in ke["doan"]] == ["a", "b", "c", "d"]


def test_4700_cac_ma_DI_THEO_dat_LIEN_NHAU_khong_chen_lai_khoang_lang():
    """⭐ Tiếng của nhóm là MỘT khối liền: `b` phải bắt đầu đúng ở chỗ `a` hết.

    ⛔ Nếu `b` bị đặt ở mốc gốc của nó thì phụ đề hiện **trễ** so với tiếng —
       đúng khoảng lặng mà phép gộp vừa mượn.
    """
    muc = [_muc("a", 0.0, 1.0, "mot hai"), _muc("b", 1.5, 2.5, "ba bon")]
    dong = nt.no_ban_ke({"ma": "a", "khoa": "k.wav", "giay": 2.0,
                         "chu": "mot hai ba bon"}, muc)
    ke = thoi_gian.lap_ke_hoach(
        muc, {d["ma"]: float(d["giay"]) for d in dong}, tong_giay=10.0,
        nhom_gop=nt.nhom_theo_ma({"doan": dong}))
    a, b = ke["doan"]
    assert b["dat_tai_ms"] == a["dat_tai_ms"] + a["dai_ms"]
    assert b["dat_tai_ms"] < 1500, "⛔ khong duoc quay ve moc goc 1,5 s"
    # MỘT hệ số cho cả tệp — hai số khác nhau là hai mốc không thể cùng đúng
    assert a["he_so_toc"] == b["he_so_toc"]


def test_4700_khong_nhom_gop_thi_ke_hoach_KHONG_DOI_mot_mili_giay():
    """⛔ Lượt chạy không gộp gì phải cho **đúng** kế hoạch của bản trước."""
    muc = [_muc("a", 0.0, 1.0, "mot"), _muc("b", 1.5, 2.5, "hai")]
    do_dai = {"a": 0.9, "b": 1.1}
    assert (thoi_gian.lap_ke_hoach(muc, do_dai, tong_giay=10.0)
            == thoi_gian.lap_ke_hoach(muc, do_dai, tong_giay=10.0, nhom_gop={}))


def test_4700_MOT_cho_khai_cho_anh_xa_ma_toi_tep():
    """🔴 `tep_theo_ma` chỉ trả những dòng SỞ HỮU tệp.

    ⛔ Bốn chỗ hạ nguồn (`_dung_ban_phoi`, `ban_dung`, `qc_do_luong`, `qc`) đều
       hỏi câu này; một chỗ tự viết dict comprehension sẽ đặt **cùng một tệp
       2–4 lần** — nghe thành tiếng vang, ⛔ không ném, ⛔ không log.
    """
    dong = nt.no_ban_ke({"ma": "a", "khoa": "k.wav", "giay": 2.0, "chu": "x y"},
                        [_muc("a", 0, 1, "x"), _muc("b", 1, 2, "y")])
    ban_ke = {"doan": dong}
    assert nt.tep_theo_ma(ban_ke) == {"a": "k.wav"}, "chi MOT chu so huu tep"
    assert nt.nhom_theo_ma(ban_ke) == {"b": "a"}


def test_4700_bon_cho_ha_nguon_DEU_di_qua_tep_theo_ma():
    """⛔ Bánh cóc: một chỗ hạ nguồn viết lại phép ánh xạ `ma -> khoa` thì đỏ."""
    import inspect

    from apps.auto_scan_video import (ban_dung, giai_doan_qc_do_luong,
                                      giai_doan_thoi_gian)
    for mo, ten in ((giai_doan_thoi_gian, "tep_theo_ma"),
                    (ban_dung, "tep_theo_ma"),
                    (giai_doan_qc_do_luong, "la_dong_theo_sau")):
        src = inspect.getsource(mo)
        assert f"nan_thoi_luong.{ten}" in src, (
            f"{mo.__name__} khong di qua nan_thoi_luong.{ten}")


# ── 5: NHÃN chiều NGẮN ───────────────────────────────────────────────────────

def test_4700_doan_qua_NGAN_khong_con_bi_goi_la_CO_GIAN():
    """Phép 5. 🔴 Nhãn cũ (`CO_GIAN`, `he_so = 1.0`, *"co giãn nhẹ là đủ"*) SAI
    NGHĨA: `co_gian_du_khong` có đường tắt trả `(True, 1.0)` cho **mọi** câu ngắn
    hơn khe, nên ⛔ không có gì được co giãn cả.
    """
    khe = 4.0
    giay = 1.0                                  # lệch −0,75 < −DUNG_SAI_NGAN
    assert nan_cho_vua.can_nan(giay, khe) is True
    assert nan_cho_vua.nen_viet_lai(giay, khe) is False

    kq = nan_cho_vua.ket_luan("m", chu="ngan", giay=giay, khe=khe, so_vong=0)
    assert kq.trang_thai == nan_cho_vua.NGAN
    assert kq.trang_thai != nan_cho_vua.CO_GIAN
    assert kq.he_so_co_gian == 1.0
    ly_do = str(kq.ghi_chu.get("ly_do") or "")
    assert "co gian" not in ly_do or "khong co gian" in ly_do, ly_do
    assert "nuot" in ly_do, "ghi chu phai noi ra SU THAT: khoang lang bi nuot"
    assert kq.dat is True, "doan ngan van GIAO DUOC, ⛔ khong phai CAN_SUA"


def test_4700_chieu_DAI_van_vao_CO_GIAN_nhu_cu():
    """⛔ Không đổi nghĩa nấc 3: câu DÀI hơn khe trong trần vẫn là `CO_GIAN`.

    ⚠️ Khe 4 s, tiếng 4,4 s: vượt 0,4 s > `dung_sai_giay(4) = 0,32` (một khe 1 s
       thì **sàn** 0,256 s đã nuốt cả 0,1 s — đó là bước 1, ⛔ không phải ca này).
    """
    kq = nan_cho_vua.ket_luan("m", chu="dai", giay=4.4, khe=4.0, so_vong=0)
    assert kq.trang_thai == nan_cho_vua.CO_GIAN
    assert kq.he_so_co_gian > 1.0


def test_4700_NGAN_co_mat_trong_bao_cao_va_KHONG_bi_dem_la_can_sua():
    kq_ngan = nan_cho_vua.ket_luan("m1", chu="x", giay=1.0, khe=4.0, so_vong=0)
    kq_vua = nan_cho_vua.ket_luan("m2", chu="y", giay=1.0, khe=1.0, so_vong=0)
    tt = nan_cho_vua.tom_tat([kq_ngan, kq_vua])
    assert tt["so_ngan"] == 1 and tt["so_vua"] == 1
    assert tt["so_co_gian"] == 0 and tt["so_can_sua"] == 0


# ── 6: CÁI GIÁ — ký tự/giây của phụ đề, trên dữ liệu THẬT ────────────────────

def _bang_ky_tu_moi_giay() -> dict:
    return json.loads((BC / "b2_gop_khe" / "ket_qua.json")
                      .read_text(encoding="utf-8"))


def test_4700_ky_tu_moi_giay_KHONG_VUOT_tran_Netflix_truoc_va_sau():
    """Phép 6. Bảng số đã commit, và mệnh đề nó chốt.

    🔑 **Ô phụ đề dài đúng bằng thời gian máy đọc chính văn bản của ô đó**
       (`phu_de.su_kien_tu_ke_hoach`: `end = dat_tai + dai_ms`). Nên ký tự/giây
       của phụ đề là một tính chất của GIỌNG, ⛔ không phải của phép gộp — và bảng
       phải cho hai dòng ĐÚNG BẰNG NHAU. Nếu chúng khác nhau thì thiết kế đã
       trượt: phép gộp đã bò sang phụ đề.
    """
    b = _bang_ky_tu_moi_giay()["tong"]["ky_tu_moi_giay"]
    truoc, sau = b["1_truoc"], b["2_sau_o_van_tach"]
    assert truoc["p95"] <= 20.0 and sau["p95"] <= 20.0
    assert truoc["so_vuot_20"] == 0 and sau["so_vuot_20"] == 0
    assert (truoc["p50"], truoc["p95"], truoc["max"]) == \
           (sau["p50"], sau["p95"], sau["max"]), (
        "phep gop DA bo sang phu de - xem no_ban_ke")


def test_4700_vi_sao_KHONG_gop_ca_O_PHU_DE_bang_SO():
    """🔴 Cái giá thật ⛔ KHÔNG nằm ở ký tự/giây mà ở BỐ CỤC ô.

    Trần bố cục của ta là `SO_DONG_TOI_DA x KY_TU_MOI_DONG` = 84 ký tự; trần gộp
    mượn của Viral là 220 — **2,6 lần** rộng hơn, vì 220 là trần của một LƯỢT
    ĐỌC, ⛔ không phải của một ô chữ. Đo trên 188 ô thật: gộp cả ô đẩy tỉ lệ ô
    vượt trần từ 15,4 % lên 42,9 %.

    ⚠️ Và con số 15,4 % **trước** gộp là một khiếm khuyết CÓ SẴN, ⛔ không do
       lượt này gây ra — ghi lại, ⛔ không sửa ở đây (ngoài phạm vi).
    """
    assert phu_de.SO_DONG_TOI_DA * phu_de.KY_TU_MOI_DONG < nt.TRAN_KY_TU_GOP
    bc = _bang_ky_tu_moi_giay()["tong"]["bo_cuc_o"]
    assert bc["1_truoc"]["ti_le_vuot_tran_o"] > 0, (
        "khiem khuyet co san: mot so o DA vuot 2 dong x 42")
    assert (bc["3_phan_thuc_gop_ca_o"]["ti_le_vuot_tran_o"]
            > 2 * bc["1_truoc"]["ti_le_vuot_tran_o"])


def test_4700_gop_khe_HA_so_doan_bi_phan_quyet_duoi_MOT_AM_TIET():
    """⭐ Cái lợi, trên đúng dữ liệu đã có: 119/188 (63,3 %) -> 44/126 (34,9 %).

    ⚠️ Và cái lợi KHÔNG phải là *"tỉ lệ khe không vừa"*: con số ấy chỉ đi từ
       71,8 % xuống 67,5 %. Cái giảm thật là **SỐ lượt gọi model**: 135 -> 85.
    """
    t = _bang_ky_tu_moi_giay()["tong"]
    truoc, sau = t["duoi_mot_am_tiet_truoc"], t["duoi_mot_am_tiet_sau"]
    assert sau["ti_le"] < truoc["ti_le"] * 0.7
    assert t["khong_vua_sau"]["k"] < t["khong_vua_truoc"]["k"] * 0.7
    assert t["so_nhom"] < t["so_khe"]


def test_4700_bang_so_do_LAI_DUOC_tu_du_lieu_da_commit():
    """⛔ Một bảng số chép tay là một bảng không tự biết nó đã cũ.

    ⇒ Chạy lại chính bộ đo trên dữ liệu đã commit và đối chiếu với tệp kết quả.
    """
    import importlib.util

    duong = BC / "b2_gop_khe" / "do_ky_tu_moi_giay.py"
    spec = importlib.util.spec_from_file_location("_do_b2_gop_khe", duong)
    mo = importlib.util.module_from_spec(spec)
    import sys
    sys.modules["_do_b2_gop_khe"] = mo
    spec.loader.exec_module(mo)
    mo.BC = BC
    moi = mo.chay()["tong"]
    cu = _bang_ky_tu_moi_giay()["tong"]
    for khoa in ("so_khe", "so_nhom", "so_nhom_da_gop"):
        assert moi[khoa] == cu[khoa], f"{khoa}: do lai ra {moi[khoa]}, tep ghi {cu[khoa]}"
    assert moi["ky_tu_moi_giay"]["1_truoc"]["p50"] == \
           cu["ky_tu_moi_giay"]["1_truoc"]["p50"]
    assert st.median([1.0]) == 1.0      # bộ đo dùng `statistics`, giữ import thật


def test_4700_MOT_khoa_MOT_chu_so_huu_trong_bao_cao_voice():
    """🔴 Từ 25/09 *"số `ma` của `content.json`"* và *"số khe đọc"* là **hai** con
    số khác nhau — `gop_khe` đọc một lượt cho 2–4 `ma`.

    Bản đầu của lượt này viết `"so_doan": len(muc_goc)` **cạnh**
    `**nan_cho_vua.tom_tat(...)`, và vì phép spread đứng sau nên nó **thắng**: khoá
    `so_doan` âm thầm mang một nghĩa thứ hai. ⇒ Mỗi khoá đúng một chủ:

        so_doan          `nan_cho_vua.tom_tat`  — số KHE ĐỌC (= số tệp tiếng)
        so_ma_noi_dung   `giai_doan_giong`      — số `ma` của `content.json`
        so_khe_da_gop    `giai_doan_giong`      — bao nhiêu nhóm thật sự đã gộp
    """
    import inspect

    from apps.auto_scan_video import giai_doan_giong

    tt = nan_cho_vua.tom_tat([])
    assert "so_doan" in tt, "khoa gop cu ⛔ khong duoc bien mat (test_476)"
    src = inspect.getsource(giai_doan_giong.chay)
    assert '"so_ma_noi_dung": len(muc_goc)' in src
    assert '"so_doan"' not in src, (
        "`giai_doan_giong` ⛔ khong duoc ghi de khoa `so_doan` cua nan_cho_vua")


def test_4700_chia_giay_KHONG_BAO_GIO_tra_ve_0_khi_tep_co_do_dai():
    """🔴 Ranh giới GIÂY ↔ MILI GIÂY, ⛔ không phải một nhánh "cho chắc".

    `thoi_gian.lap_ke_hoach` đổi sang mili-giây (`_ms`) và **ném**
    `ThoiGianError('Doan {ma} chua co tieng.')` khi `dai <= 0`. Một thành viên 1
    âm tiết trong một nhóm rất dài làm tròn xuống `0 ms` ⇒ ⛔ chết cả lượt chạy vì
    một phép chia.
    """
    phan = nt.chia_giay(1.0, [1, 100000])
    assert all(p > 0 for p in phan), phan
    assert sum(phan) == pytest.approx(1.0, abs=1e-3)

    muc = [_muc("a", 0.0, 0.5, "mot"),
           _muc("b", 0.5, 30.0, " ".join(["x"] * 3000))]
    dong = nt.no_ban_ke({"ma": "a", "khoa": "k.wav", "giay": 1.0, "chu": "..."},
                        muc)
    ke = thoi_gian.lap_ke_hoach(
        muc, {d["ma"]: float(d["giay"]) for d in dong}, tong_giay=60.0,
        nhom_gop=nt.nhom_theo_ma({"doan": dong}))
    assert [d["ma"] for d in ke["doan"]] == ["a", "b"]

    # tệp dài 0 thì ⛔ không bịa ra thời lượng
    assert nt.chia_giay(0.0, [1, 2]) == [0.0, 0.0]


def test_4700_THIEU_tep_tieng_van_NEM_chu_KHONG_bi_gop_che_mat():
    """🔴 Hai chuyện khác hẳn nhau, và chỉ MỘT được phép im lặng.

        đi theo (`gop_vao`) -> tệp của nhóm đã có một lớp  -> bỏ qua, bình thường
        thiếu `khoa`        -> một đoạn tiếng bị mất       -> phải NÉM

    ⛔ Lọc bằng *"vắng mặt khỏi `tep_theo_ma`"* gộp hai chuyện thành một, và biến
       cái thứ hai thành một đoạn tiếng bị vứt **âm thầm**.
    """
    import inspect

    from apps.auto_scan_video import ban_dung, giai_doan_thoi_gian

    for mo in (giai_doan_thoi_gian, ban_dung):
        src = inspect.getsource(mo)
        assert "nhom_theo_ma" in src, (
            f"{mo.__name__} phai loc bang truong TUONG MINH `gop_vao`, "
            "⛔ khong bang su vang mat cua `khoa`")
    # cửa "thiếu tệp tiếng" vẫn còn nguyên ở cả hai chỗ
    assert "chua co tep tieng" in inspect.getsource(giai_doan_thoi_gian)
    assert "không có tệp tiếng" in inspect.getsource(ban_dung)
