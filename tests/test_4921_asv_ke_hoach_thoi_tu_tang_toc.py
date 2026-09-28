"""test_4921 — B13-A4: `lap_ke_hoach` thôi tự tăng tốc để trả nợ.

⭐ Hàm thuần hoàn toàn: ⛔ không model, ⛔ không LLM/TTS/GPU, ⛔ không CSDL, ⛔ không
một tệp âm thanh nào.

## Quyết định sản phẩm đang được thi hành ở đây

Chủ dự án chốt 28/09: *"dùng khoảng lặng trước; cho tiếng dàn trong đoạn; **chỉ
tăng tốc như phương án cuối**; và chặn trần để giọng không méo."* Nấc cuối ấy đã
có chủ — bậc thang nắn (`nan_cho_vua.co_gian_du_khong`, mẫu số `ngan_sach` từ
B13-A2). Máy tăng tốc **thứ hai** trong `lap_ke_hoach` (`_tang_toc_can`, kẹp
`TRAN_TANG_TOC`) đi ngược lời chốt ⇒ **BỎ**.

## ⚠️ Số liệu ở đây là gì, và ⛔ KHÔNG là gì

Lượt `asvr_47327a869a8f4597960048f09064740` đo được `so_doan_tang_toc = 12`,
`he_so_toc_lon_nhat = 1,15`, và 12 `ma` ấy là `MA_12_DOAN` dưới đây. ⛔ **Nhưng
artifact của lượt đó CHƯA được commit** (đối chiếu: `grep` cả `docs/` chỉ ra đúng
một tệp — chính bản plan). ⇒ **Mốc thời gian trong bộ kiểm này là DỰNG LẠI, chỉ
HÌNH DẠNG là đã đo**: một bài nói dồn làm kế hoạch tự tăng tốc, trong khi bản
phối áp `1,0`. `ma` lấy đúng của lượt thật để một người đọc `outputs` của lượt sau
đối chiếu được từng tên. ⛔ Đừng đọc các con số `ms` ở đây như số đo sản phẩm.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import (giai_doan_thoi_gian as gt, nan_cho_vua,
                                  thoi_gian as tg)

#: 12 `ma` mà lượt thật báo `he_so_toc > 1,0` (kế hoạch), trong khi bản phối áp
#: `1,0` cho tất cả — tức 12 đoạn tiếng DÀI HƠN chỗ kế hoạch chừa.
MA_12_DOAN = ("seg_0012", "seg_0013", "seg_0019", "seg_0020", "seg_0032",
              "seg_0033", "seg_0034", "seg_0035", "seg_0037", "seg_0041",
              "seg_0045", "seg_0048")


def _muc_noi_don(mas, *, cach_giay: float = 1.0, noi_giay: float = 1.0):
    """Các `ma` ĐÃ CHO, nói dồn — hình dạng làm kế hoạch phải tự tăng tốc."""
    return [{"ma": ma, "bat": i * cach_giay,
             "ket": i * cach_giay + noi_giay, "chu": f"cau {i}"}
            for i, ma in enumerate(mas)]


def _he_so_nan(muc, dai, tong_giay):
    """Hệ số mà **BẬC THANG NẮN** sẽ ra cho cùng hình học — dựng đúng chuỗi thật.

    🔴 **⛔ Không được gõ tay một `ap` rồi đo.** Bản đầu của bộ kiểm này truyền
       `ap = 1,0` cho mọi `ma` trên một bài **nói dồn** (`khoang_lang = 0`) — một
       cặp đôi mà chuỗi thật ⛔ **KHÔNG BAO GIỜ** sinh ra được: không có lặng thì
       `ngan_sach == khe`, nên bậc thang nắn **phải** ra một hệ số > 1. Đo trên
       tiền đề tự mâu thuẫn ấy cho ra kết luận *"A4 làm khách mất thêm một câu"* —
       **SAI**, đúng khuôn `fixture-tu-dung-tien-de-ma-san-pham-KHONG-co`.

    ⭐ Nên hàm này **tính** `ap` bằng chính bốn mắt ở sản phẩm:
       `nan_cho_vua.khe_cua` → `thoi_gian.ngan_sach_nan_s` →
       `nan_cho_vua.co_gian_du_khong` → `giai_doan_thoi_gian.he_so_ap`.
    """
    moc = [tg._ms(x["bat"]) for x in muc]
    tong_ms = tg._ms(tong_giay)
    ra = {}
    for i, x in enumerate(muc):
        khe = nan_cho_vua.khe_cua(x)
        ns = tg.ngan_sach_nan_s(khe, tg.ngan_sach_doan(moc, i, tong_ms) / 1000.0)
        _duoc, h = nan_cho_vua.co_gian_du_khong(dai[x["ma"]], khe, ns)
        ra[x["ma"]] = gt.he_so_ap(h, tran_ky_thuat=tg.TRAN_KY_THUAT_ATEMPO)
    return ra


def _do_ke(ke) -> dict:
    """Bốn con số của một kế hoạch, kể cả số chỗ chồng quá trần."""
    truoc_ket, chong = None, 0
    for d in ke["doan"]:
        if int(d["dai_ms"]) == 0:        # đoạn đã bị bỏ: ⛔ không chiếm thời gian
            continue
        dat = int(d["dat_tai_ms"])
        if truoc_ket is not None and dat + tg.TRAN_CHONG_LAN_MS < truoc_ket:
            chong += 1
        truoc_ket = dat + int(d["dai_ms"])
    return {"cat": int(ke["so_doan_bi_cat"]),
            "troi_max_ms": int(ke["troi_toi_da_ms"]),
            "ket_cuoi_ms": int(ke["ket_cuoi_ms"]),
            "tong_ms": int(ke["tong_ms"]),
            "chong_qua_tran": chong}


# ══════════════════════════════════════════════════════════════════════════════
#  §1 TRƯỚC / SAU trên chính 12 `ma` ấy
# ══════════════════════════════════════════════════════════════════════════════

def test_4921_TRUOC_A4_ke_hoach_tu_tang_toc_va_ban_phoi_KHONG_ap():
    """🔴 Tái hiện con bọ TRƯỚC khi chốt bản vá — ⛔ không có bài này thì bài dưới
       đo một thứ ⛔ không ai biết có phải thứ đã xảy ra trên máy khách.

    Đường LUI (`he_so_da_ap=None`) giữ NGUYÊN luật cũ, nên nó là cỗ máy thời gian
    dùng được: nó cho đúng hình dạng *"kế hoạch nén, bản phối ⛔ không nén"*.
    """
    muc = _muc_noi_don(MA_12_DOAN)
    dai = {m["ma"]: 1.5 for m in muc}
    ke_cu = tg.lap_ke_hoach(muc, dai, tong_giay=30.0)          # ⛔ không truyền

    nhanh = [d["ma"] for d in ke_cu["doan"] if float(d["he_so_toc"]) > 1.0]
    assert nhanh, "đường LUI phải vẫn tự tăng tốc — nếu không, bài này đã mù"
    assert tg.tom_tat(ke_cu)["he_so_toc_lon_nhat"] == pytest.approx(
        tg.TRAN_TANG_TOC, abs=1e-3), "luật cũ kẹp về trần THIẾT KẾ 1,15"

    # Bản phối áp `1,0` cho MỌI `ma` (không đoạn nào tràn ngân sách nắn).
    ap = {m["ma"]: 1.0 for m in muc}
    ra = tg.doi_chieu_he_so_toc(
        {str(d["ma"]): float(d["he_so_toc"]) for d in ke_cu["doan"]}, ap)
    assert ra["so_doan_he_so_lech_ke_hoach"] == len(nhanh) > 0, (
        "đây là con bọ: kế hoạch chừa chỗ theo 1,15 mà bản phối áp 1,0 ⇒ "
        f"{len(nhanh)} đoạn tiếng dài hơn chỗ được chừa")


def test_4921_SAU_A4_doi_chieu_dem_DUNG_KHONG_doan_nao_lech():
    """🔑 **Phép chứng minh A4 đã ăn.** `doi_chieu_he_so_toc` từng đếm 12; nay 0.

    ⛔ Và đó là lý do ⛔ KHÔNG được xoá hàm ấy: một hàm đếm ra `0` **sau khi từng
       đếm ra 12** là bằng chứng; xoá nó đi thì ⛔ không còn gì nói A4 có tác dụng.
    """
    muc = _muc_noi_don(MA_12_DOAN)
    dai = {m["ma"]: 1.5 for m in muc}
    # Bản phối áp `1,0` cho mọi `ma` — đúng lượt đã đo.
    ap = {m["ma"]: 1.0 for m in muc}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=30.0, he_so_da_ap=ap)

    assert all(float(d["he_so_toc"]) == 1.0 for d in ke["doan"]), (
        "A4: kế hoạch ⛔ không còn tự nén — tiếng giữ nhịp tự nhiên và dàn vào "
        "khoảng lặng")
    ra = tg.doi_chieu_he_so_toc(
        {str(d["ma"]): float(d["he_so_toc"]) for d in ke["doan"]}, ap)
    assert ra["so_doan_he_so_lech_ke_hoach"] == 0, (
        f"còn lệch: {ra['lech']}")
    assert ra["he_so_gop_ke_hoach_x_da_ap_lon_nhat"] == pytest.approx(1.0)


def test_4921_ke_hoach_MIRROR_he_so_se_duoc_ap_ke_ca_khi_vuot_tran_thiet_ke():
    """⭐ `seg_0011`/`seg_0031` của lượt thật có `he_so_co_gian ≈ 1,17 / 1,14` —
       lặng bằng 0 nên tăng tốc là ĐÚNG (B13-A2). Kế hoạch phải chừa chỗ theo
       ĐÚNG con số ấy, kể cả khi nó vượt trần THIẾT KẾ 1,15.

    ⛔ Kẹp về `TRAN_TANG_TOC` ở đây là dựng lại cái cổng chủ dự án đã bỏ 26/09, ở
       một tệp khác, nơi ⛔ không ai đi tìm nó.
    """
    muc = _muc_noi_don(("seg_0011", "seg_0031"), cach_giay=3.0, noi_giay=1.0)
    dai = {"seg_0011": 2.32, "seg_0031": 2.08}
    ap = {"seg_0011": 1.1711, "seg_0031": 1.1422}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=12.0, he_so_da_ap=ap)

    theo_ma = {str(d["ma"]): d for d in ke["doan"]}
    for ma, h in ap.items():
        assert float(theo_ma[ma]["he_so_toc"]) == pytest.approx(h, abs=1e-4), (
            f"{ma}: kế hoạch phải chừa chỗ theo hệ số SẼ ĐƯỢC ÁP")
        # Và chỗ chừa = `giay / h`, tức ĐÚNG độ dài tệp sau `atempo`.
        assert theo_ma[ma]["dai_ms"] == int(tg._ms(dai[ma]) / h), (
            f"{ma}: `dai_ms` phải là độ dài THẬT sau `atempo`")
    assert tg.doi_chieu_he_so_toc(
        {ma: float(d["he_so_toc"]) for ma, d in theo_ma.items()},
        ap)["so_doan_he_so_lech_ke_hoach"] == 0


def test_4921_kiem_cuong_che_tran_KY_THUAT_chu_khong_tran_THIET_KE():
    """🔴 `kiem()` từng ném ở `TRAN_TANG_TOC` (1,15). Từ A4 `he_so_toc` là hệ số
       SẼ ĐƯỢC ÁP, và chủ dự án chốt 26/09 rằng trần thiết kế là **CẢNH BÁO**.

    ⛔ Giữ 1,15 ở `kiem()` sẽ làm MỌI lượt chạy có một đoạn `CO_GIAN` chết ngay ở
       phép kiểm kế hoạch — tức chặn khách vì một ngưỡng đã bị bỏ.
    """
    # 1,50 > trần thiết kế 1,15, < trần kỹ thuật 2,0 ⇒ ⛔ KHÔNG được ném.
    muc = _muc_noi_don(("seg_0001",), cach_giay=5.0, noi_giay=1.0)
    ke = tg.lap_ke_hoach(muc, {"seg_0001": 3.0}, tong_giay=10.0,
                         he_so_da_ap={"seg_0001": 1.5})
    assert float(ke["doan"][0]["he_so_toc"]) == pytest.approx(1.5)

    # Và trần KỸ THUẬT vẫn là một CỔNG: 2,4 bị kẹp về 2,0, ⛔ không lọt qua.
    ke2 = tg.lap_ke_hoach(muc, {"seg_0001": 3.0}, tong_giay=10.0,
                          he_so_da_ap={"seg_0001": 2.4})
    assert float(ke2["doan"][0]["he_so_toc"]) == pytest.approx(
        tg.TRAN_KY_THUAT_ATEMPO)
    # ⭐ MỘT chỗ khai con số ấy — `giai_doan_thoi_gian` chỉ là bí danh.
    assert gt.TRAN_KY_THUAT_ATEMPO is tg.TRAN_KY_THUAT_ATEMPO

    # ⚠️ Chốt **CON SỐ trần được in ra**, ⛔ không chốt câu chữ: `msgid` giữ nguyên
    #    từng chữ có lý do cơ học (xem chú thích tại `kiem()` — bộ quét ranh giới
    #    của `test_410` + catalog `locale/`). Đại lượng cần chốt là *"trần nào
    #    đang được cưỡng chế"*, và nó nằm ở con số.
    with pytest.raises(tg.ThoiGianError,
                       match=str(tg.TRAN_KY_THUAT_ATEMPO)):
        tg.kiem({"schema": tg.SCHEMA_KE_HOACH, "tong_ms": 10_000,
                 "ket_cuoi_ms": 3000,
                 "doan": [{"ma": "seg_0001", "dat_tai_ms": 0, "dai_ms": 1000,
                           "he_so_toc": 2.5}]})


# ══════════════════════════════════════════════════════════════════════════════
#  §2 ĐỐI CHỨNG NGƯỢC — ⛔ không được bỏ
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Thiếu §2 thì một bản vá *"chừa thật rộng cho chắc"* cũng xanh trên §1, và nó
#    sẽ giao cho khách một bản lồng tiếng dài hơn video hoặc chồng câu lên nhau.

#: Nam hinh hoc, moi cai mot `(nhan, cach_giay, noi_giay, tieng_giay, tong_giay)`.
#: ⭐ `ap` ⛔ KHONG go tay — `_he_so_nan` tinh no bang chinh bac thang nan, nen
#:    moi hang la mot tien de chuoi that CO THE sinh ra.
HINH_HOC = (
    ("noi don, tieng 1,5s", 1.0, 1.0, 1.5, 30.0),
    ("co nghi, tieng 1,5s", 2.0, 1.0, 1.5, 30.0),
    ("co nghi, tieng 2,4s", 3.0, 1.0, 2.4, 40.0),
    ("noi don, tieng 2,2s", 1.0, 1.0, 2.2, 30.0),
    ("vua khit", 1.0, 1.0, 1.0, 30.0),
)


@pytest.mark.parametrize("nhan,cach,noi,tieng,tong", HINH_HOC)
def test_4921_DOI_CHUNG_T2_va_CHONG_LAN_giu_nguyen(nhan, cach, noi, tieng, tong):
    """⚠️ Ràng buộc 1 và 2: **T2 / D-ASV-03** và `TRAN_CHONG_LAN_MS`.

    A4 dàn rộng hơn ⇒ đuôi dễ tràn hơn. Bậc thang trả nợ (`TRAN_TROI_SO_DOAN`
    → bỏ đoạn) và vòng `while` ở đuôi hàm phải gánh — ⛔ **không** nới luật.
    """
    muc = _muc_noi_don(MA_12_DOAN, cach_giay=cach, noi_giay=noi)
    dai = {m["ma"]: tieng for m in muc}
    ap = _he_so_nan(muc, dai, tong)
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=tong, he_so_da_ap=ap)
    do = _do_ke(ke)

    assert do["ket_cuoi_ms"] <= do["tong_ms"], (
        f"{nhan}: bản lồng tiếng dài hơn video "
        f"({do['ket_cuoi_ms']} > {do['tong_ms']})")
    assert do["chong_qua_tran"] == 0, (
        f"{nhan}: {do['chong_qua_tran']} chỗ chồng quá "
        f"{tg.TRAN_CHONG_LAN_MS} ms — nghe thành HAI NGƯỜI cùng nói")
    tg.kiem(ke)      # đã chạy trong `lap_ke_hoach`; gọi lại để nói rõ bất biến nào


@pytest.mark.parametrize("nhan,cach,noi,tieng,tong", HINH_HOC)
def test_4921_DOI_CHUNG_A4_KHONG_xau_hon_o_BAT_KY_chieu_nao(nhan, cach, noi,
                                                            tieng, tong):
    """🔑 **Cái giá thật của A4, ĐO chứ ⛔ không đoán.**

    Giả thuyết đáng sợ: bỏ máy tăng tốc ⇒ nợ ⛔ không còn được trả bằng
    `atempo` ⇒ bậc thang phải **BỎ** nhiều đoạn hơn, tức khách **mất thêm lời
    thoại** — một đánh đổi sản phẩm thật sự.

    ⭐ Đo trên năm hình học với `ap` **nhất quán** (tính từ chính bậc thang
       nắn): giả thuyết **SAI**. A4 ⛔ không xấu hơn ở bất kỳ chiều nào, và tốt
       hơn rõ ở ca nặng: `noi don, tieng 2,2s` đi từ **3 đoạn bị bỏ → 0**, nợ
       đỉnh **4.591 → 1.100 ms**.

    🔑 Lý do cơ học: `ngan_sach_nan_s(khe, ngan_sach)` = `khe + 0,7 × lặng` là
       **CÙNG một con số** với `dung_duoc` trong `lap_ke_hoach`, nên bậc thang
       nắn đã nén mỗi đoạn về ĐÚNG chỗ kế hoạch chừa ⇒ `troi` teo lại. Máy
       tăng tốc trong `lap_ke_hoach` vốn giải **cùng một bài** bằng **sai mẫu số**.
    """
    muc = _muc_noi_don(MA_12_DOAN, cach_giay=cach, noi_giay=noi)
    dai = {m["ma"]: tieng for m in muc}
    ap = _he_so_nan(muc, dai, tong)

    cu = _do_ke(tg.lap_ke_hoach(muc, dai, tong_giay=tong))
    moi = _do_ke(tg.lap_ke_hoach(muc, dai, tong_giay=tong, he_so_da_ap=ap))

    assert moi["cat"] <= cu["cat"], (
        f"{nhan}: A4 làm khách MẤT THÊM lời thoại "
        f"({cu['cat']} → {moi['cat']} đoạn bị bỏ)")
    assert moi["ket_cuoi_ms"] <= cu["ket_cuoi_ms"], (
        f"{nhan}: tổng thời lượng bản ra TĂNG "
        f"({cu['ket_cuoi_ms']} → {moi['ket_cuoi_ms']} ms)")
    assert moi["troi_max_ms"] <= cu["troi_max_ms"]
    assert moi["chong_qua_tran"] <= cu["chong_qua_tran"] == 0


def test_4921_DOI_CHUNG_hai_mau_so_PHAI_bang_nhau():
    """⭐ ĐẲNG THỨC làm A4 an toàn — chốt nó ở mức CÔNG THỨC.

    Nếu một ngày ai đó đổi MỘT trong hai vế, bài này đỏ **TRƯỚC** khi khách
    mất một câu — và đó là toàn bộ công dụng của nó.
    """
    for khe, ngan_sach in ((2.0, 5.0), (0.9, 33.39), (1.98, 1.98), (0.0, 3.0)):
        a = tg.ngan_sach_nan_s(khe, ngan_sach)                      # bậc thang nắn
        b = khe + (ngan_sach - khe) * tg.TY_LE_MUON_KHOANG_LANG     # `dung_duoc`
        assert a == pytest.approx(b), (
            f"hai mẫu số đã lệch tại (khe={khe}, ngan_sach={ngan_sach}): bậc thang "
            f"nắn nén về {a} mà `lap_ke_hoach` chừa {b} ⇒ nợ quay lại và khách "
            f"mất thêm lời thoại")


# ════════════════════════════════════════════════════════════════════════════
#  §3 Hai khoá phẳng của `tom_tat` sau A4: ⛔ KHÔNG chết, mà thành ĐÚNG
# ════════════════════════════════════════════════════════════════════════════

def test_4921_hai_khoa_phang_KHONG_thanh_truong_CHET():
    """🔴 **Câu hỏi điều phối đặt ra, và câu trả lời đo được.**

    Nỗi lo: sau A4 `he_so_toc` luôn `1,0` ⇒ `so_doan_tang_toc` là một **số 0
    vĩnh viễn** và `he_so_toc_lon_nhat` một **số 1 vĩnh viễn** — hai trường chết
    mua sự yên tâm bằng tín dụng giả, trong khi 4 đoạn CÓ bị tăng tốc thật.

    ⭐ **Nỗi lo ấy không xảy ra, và vì một lý do mạnh hơn cả đổi tên:** A4
       ⛔ không đặt `he_so_toc = 1,0`, nó **MIRROR** hệ số sẽ được áp. Nên từ A4
       hai khoá phẳng đo **ĐÚNG cái mà tên chúng hứa** — chúng từ SAI thành
       ĐÚNG, chứ ⛔ không từ SAI thành CHẾT. ⇒ ⛔ Không đổi tên, ⛔ không xóa,
       ⛔ không chạm `tools/asv_doi_soat.py`.
    """
    muc = _muc_noi_don(("seg_0011", "seg_0031"), cach_giay=3.0, noi_giay=1.0)
    dai = {"seg_0011": 2.32, "seg_0031": 2.08}
    ap = {"seg_0011": 1.1711, "seg_0031": 1.1422}
    tt = tg.tom_tat(tg.lap_ke_hoach(muc, dai, tong_giay=12.0, he_so_da_ap=ap))

    assert tt["so_doan_tang_toc"] == 2, (
        "sau A4 khoá này phải đếm ĐÚNG số đoạn bị `atempo` thật — một `0` "
        "vĩnh viễn ở đây mới là trường chết")
    assert tt["he_so_toc_lon_nhat"] == pytest.approx(1.171, abs=1e-3)


def test_4921_hai_khoa_phang_va_master_bao_CUNG_MOT_dai_luong():
    """⭐ Đây là cái A4 làm được mà B4 (đổi tên) chỉ làm được một nửa: hai tầng
       báo cáo nay nói **cùng một đại lượng**, nên `1,15` cạnh `1,3333` ⛔ không
       còn hình thành được nữa.

    ⚠️ **Một vế VẪN khác, và nói ra ở đây:** `tom_tat` đếm theo **`ma`** (kể cả
       dòng ĐI THEO của một khe đã gộp, chúng mirror hệ số của trưởng nhóm), còn
       `master.so_doan_tang_toc_da_ap` đếm theo **TỆP**. ⇒ Trên một lượt CÓ gộp,
       số phẳng **≥** số lồng. `he_so_toc_lon_nhat` thì **bằng hản** (mirror ⇒
       `max` trên tập cha bằng `max` trên tập con).

    ⚠️ **Cái giá nếu quyết định giữ tên này sai:** một người muốn biết *"bao
       nhiêu TỆP bị tăng tốc"* đọc khoá phẳng sẽ đếm **thừa** trên lượt có gộp.
       Đổi lại: ⛔ không phải sửa `tools/asv_doi_soat.py` (L3 sở hữu), và khoá lồng
       nằm ngay cạnh trong cùng `outputs`.
    """
    muc = _muc_noi_don(("seg_0011", "seg_0031"), cach_giay=3.0, noi_giay=1.0)
    dai = {"seg_0011": 2.32, "seg_0031": 2.08}
    ap = {"seg_0011": 1.1711, "seg_0031": 1.1422}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=12.0, he_so_da_ap=ap)

    tt = tg.tom_tat(ke)
    doi = tg.doi_chieu_he_so_toc(
        {str(d["ma"]): float(d["he_so_toc"]) for d in ke["doan"]}, ap)

    # Lượt KHÔNG gộp ⇒ hai mẫu số trùng ⇒ hai tầng báo số GIỐNG NHAU.
    assert tt["so_doan_tang_toc"] == doi["so_doan_tang_toc_da_ap"]
    assert tt["he_so_toc_lon_nhat"] == pytest.approx(
        doi["he_so_toc_da_ap_lon_nhat"], abs=1e-3)
    # Và đó là điều kiện để cái bẫy cũ ⛔ không hình thành được.
    assert doi["so_doan_he_so_lech_ke_hoach"] == 0



def test_4921_van_tay_PHIEN_BAN_THOI_GIAN_da_tang():
    """⚠️ A4 đổi `dai_ms` của MỌI đoạn ⇒ `dat_tai_ms` của mọi đoạn sau đổi theo.
       Một cache cũ dùng lại được là một cache **nói dối**.

    ⭐ Khác hẳn lần A2 (28/09 sáng), khi giữ `2` là ĐÚNG: A2 ⛔ không đổi một
       mili-giây nào của kế hoạch, nó đổi `ban_ke.json` — và `van_tay_ke_hoach`
       đã bấm checksum của bản kê.
    """
    assert tg.PHIEN_BAN_THOI_GIAN >= 3, (
        "A4 đổi cách đặt đoạn ⇒ `PHIEN_BAN_THOI_GIAN` PHẢI tăng")
    goc = dict(checksum_van_ban="aaa", ban_ke_tieng="bbb", che_do="fit_original")
    assert tg.van_tay_ke_hoach(**goc) != tg.van_tay_ke_hoach(
        **{**goc, "ban_ke_tieng": "ccc"})
