"""Auto Scan Video — TIMING_ALIGN: tràn vào khoảng lặng, và trả nợ trôi.

Thi hành `ADR-003-mo-hinh-thoi-gian.md`.

## Vì sao tệp này khác các tệp trước

Ba giai đoạn trước kiểm **an toàn** (tiền, quyền, phục hồi). Tệp này kiểm **hành
vi sản phẩm**: một câu tiếng Việt dài hơn câu gốc thì chuyện gì xảy ra?

  §1 ngân sách gồm khoảng lặng   <- thay đổi nền tảng so với bản Phase 02
  §2 nợ trôi: ghi và trả
  §3 trần cứng và phép cắt
  §4 bất biến không được vi phạm
  §5 vân tay
  §6 chờ bằng chứng ngoài
"""
from __future__ import annotations

import pytest


def _muc(so: int, *, cach_giay: float, noi_giay: float = 1.0) -> list[dict]:
    """`so` câu, mỗi câu nói `noi_giay`, cách nhau `cach_giay` (tính từ đầu câu)."""
    return [{"ma": f"seg_{i:04d}", "bat": i * cach_giay,
             "ket": i * cach_giay + noi_giay, "chu": f"cau {i}"}
            for i in range(so)]


def _dai(muc: list[dict], giay: float) -> dict:
    return {m["ma"]: giay for m in muc}


# ══════════════════════════════════════════════════════════════════════════════
#  §1 Ngân sách gồm khoảng lặng
# ══════════════════════════════════════════════════════════════════════════════

def test_ngan_sach_keo_toi_luc_doan_SAU_bat_dau():
    """🔑 Dòng quan trọng nhất của cả mô hình.

    Lấy `ket - bat` là chỉ lấy thời gian **đang nói**, tức vứt đi toàn bộ khoảng
    lặng. Trên một video có nhịp nghỉ bình thường, đó là vứt đi phần lớn ngân
    sách sẵn có.

    Lấy từ `Subdub/src/subdub/media/audio.py`:
        `block_duration = next_block_start_ms - block_start_ms`
    """
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(3, cach_giay=2.0, noi_giay=1.0)   # nói 1s, nghỉ 1s
    # ⚠️ Pha 16 đổi chữ ký: hàm nhận **mốc đã đổi sang trục bản ra** thay vì
    #    `muc` gốc, vì nó từng tự đọc giờ NGUỒN rồi trừ vào một `tong_ms` giờ
    #    BẢN RA — trộn hai đồng hồ. Xem docstring của hàm.
    moc = [tg._ms(m["bat"]) for m in muc]
    assert tg.ngan_sach_doan(moc, 0, tong_ms=10_000) == 2000, (
        "ngân sách phải gồm cả khoảng lặng phía sau")
    # Đoạn cuối lấy tới hết nguồn — phần đuôi cũng là khoảng lặng dùng được.
    assert tg.ngan_sach_doan(moc, 2, tong_ms=10_000) == 6000


def test_tieng_Viet_dai_hon_60_phan_tram_van_VUA_khi_co_khoang_lang():
    """⭐ Đây là quan sát sản phẩm đã thay đổi cả thiết kế.

    Người ta không nói liền mạch. Với khoảng lặng 1 giây sau mỗi câu, một bản
    dịch dài hơn 60 % vẫn vừa — **không đoạn nào phải nén**.

    ⛔ Thiết kế Phase 02 (`fit_original` = ép vừa khung thoại) sẽ nén 1,6× ở
       **mọi** câu, làm hỏng chất lượng giọng đều khắp bài.
    """
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(5, cach_giay=2.0, noi_giay=1.0)
    ke = tg.lap_ke_hoach(muc, _dai(muc, 1.6), tong_giay=10.0)

    assert ke["so_doan_bi_cat"] == 0
    assert all(d["he_so_toc"] == 1.0 for d in ke["doan"]), "không câu nào bị nén"
    assert ke["troi_toi_da_ms"] == 0, "không sinh nợ nào"
    # Mỗi câu vẫn nằm đúng mốc gốc của nó.
    assert [d["dat_tai_ms"] for d in ke["doan"]] == [0, 2000, 4000, 6000, 8000]


def test_chi_muon_MOT_PHAN_khoang_lang():
    """ADR-003 D2 — mượn hết thì bản lồng tiếng không còn nhịp nghỉ.

    Mượn 70 % của khoảng lặng 1000 ms ⇒ ngân sách dùng được 1700 ms. Một đoạn
    dài 1800 ms phải sinh nợ, dù khoảng lặng "còn chỗ".
    """
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(3, cach_giay=2.0, noi_giay=1.0)
    ke = tg.lap_ke_hoach(muc, _dai(muc, 1.8), tong_giay=10.0)
    assert ke["doan"][0]["troi_sau_ms"] > 0, (
        "mượn quá 70 % khoảng lặng mà không ghi nợ")


# ══════════════════════════════════════════════════════════════════════════════
#  §2 Nợ trôi: ghi và trả
# ══════════════════════════════════════════════════════════════════════════════

def test_no_troi_duoc_TRA_o_khoang_lang_ke_tiep():
    """🔑 Trái tim của mô hình, lấy từ Subdub.

    Nợ không bị chặn bằng số đoạn — nó được **trả liên tục** bằng chính các
    khoảng lặng. Video nhiều nhịp nghỉ thì nợ tan nhanh.
    """
    from apps.auto_scan_video import thoi_gian as tg

    # Câu 0 rất dài (sinh nợ), các câu sau ngắn và có khoảng lặng rộng.
    muc = _muc(4, cach_giay=3.0, noi_giay=1.0)
    dai = {"seg_0000": 4.0, "seg_0001": 0.5, "seg_0002": 0.5, "seg_0003": 0.5}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=15.0)

    assert ke["doan"][0]["troi_sau_ms"] > 0, "câu dài phải sinh nợ"
    assert ke["doan"][-1]["troi_sau_ms"] == 0, (
        "nợ phải được trả hết bằng các khoảng lặng phía sau")


def test_tang_toc_CHI_de_tra_no_chu_khong_de_ep_vua():
    """ADR-003 D4.

    Không có nợ thì không tăng tốc — kể cả khi đoạn dài hơn phần thoại gốc,
    vì khoảng lặng đã gánh phần chênh.
    """
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(3, cach_giay=2.0, noi_giay=1.0)
    ke = tg.lap_ke_hoach(muc, _dai(muc, 1.5), tong_giay=10.0)
    assert ke["doan"][0]["he_so_toc"] == 1.0, (
        "đã tăng tốc dù không có nợ nào để trả")


def test_tang_toc_KHONG_BAO_GIO_vuot_tran_KY_THUAT():
    """🔴 **Viết lại 28/09 — bản cũ ghim trần THIẾT KẾ `1,15` làm cổng.**

    Hai quyết định đã dời cột mốc này:
      · 26/09 chủ dự án chốt `TRAN_TANG_TOC` là **CẢNH BÁO**, ⛔ không phải cổng;
      · 28/09 chốt **⛔ không bao giờ bỏ câu**, nên NẤC 5 được phép nén thêm tới
        `TRAN_KY_THUAT_ATEMPO` để giữ đủ nội dung.

    ⇒ Cổng duy nhất còn cưỡng chế là trần **KỸ THUẬT** — qua nó `atempo` cho
      TIẾNG RÁC. Bài này chốt đúng cổng ấy, ⛔ không chốt một cổng đã bị bỏ.
    """
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(8, cach_giay=1.0, noi_giay=1.0)      # nói dồn, không nghỉ
    ke = tg.lap_ke_hoach(muc, _dai(muc, 1.5), tong_giay=20.0)

    assert all(d["he_so_toc"] <= tg.TRAN_KY_THUAT_ATEMPO + 1e-9
               for d in ke["doan"])
    assert tg.tom_tat(ke)["he_so_toc_lon_nhat"] <= tg.TRAN_KY_THUAT_ATEMPO

    # ⭐ Và ĐỐI CHỨNG: còn chỗ thì ⛔ KHÔNG nén gì cả (nấc 5 ⛔ không tự bật).
    thua = tg.lap_ke_hoach(_muc(4, cach_giay=3.0, noi_giay=1.0),
                           _dai(_muc(4, cach_giay=3.0), 1.2), tong_giay=20.0)
    assert thua["boi_nac5"] == 1.0
    assert all(d["he_so_toc"] == 1.0 for d in thua["doan"])


# ══════════════════════════════════════════════════════════════════════════════
#  §3 Trần cứng và phép cắt
# ══════════════════════════════════════════════════════════════════════════════

def test_no_bi_CHAN_boi_tran_ba_doan():
    """ADR-003 D5 — chỗ ta đi xa hơn cả ba dự án tham chiếu.

    🔴 Subdub **không có trần nào**. Trên một video nói dồn, nợ tăng đơn điệu
       tới khi tiếng lệch hình cả chục giây mà không gì chặn lại.
    """
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(10, cach_giay=1.0, noi_giay=1.0)     # nói dồn
    ke = tg.lap_ke_hoach(muc, _dai(muc, 2.2), tong_giay=30.0)

    # 🔴 **Viết lại 28/09.** Trần nợ ⛔ KHÔNG còn cắt câu — nó là **CẢNH BÁO**
    #    (khuôn `TRAN_TANG_TOC`, chốt 26/09). Cái giữ `D-ASV-03` nay là NẤC 5.
    assert ke["so_doan_bi_cat"] == 0, (
        "⛔ KHÔNG BAO GIỜ bỏ câu (chủ dự án chốt 28/09)")
    assert ke["so_doan_vuot_tran_troi"] > 0, (
        "trần nợ phải vẫn ĐẾM được — một cảnh báo ⛔ không đếm được thì ⛔ không "
        "ai biết phim nào đang căng")
    assert ke["ket_cuoi_ms"] <= ke["tong_ms"], "T2 / D-ASV-03"


def test_cat_MOT_doan_chi_mua_lai_ngan_sach_cua_DOAN_DO():
    """🔴 Lỗi đã có thật trong bản đầu, và nó sai theo hai cách cùng lúc.

    Bản đầu đặt lại `dat_tai = bat_goc` và `troi = 0` khi cắt:

      * lùi thời gian về sau mốc mà tiếng đoạn trước vẫn đang chạy — phép kiểm
        chồng lấn bắt được ngay;
      * xoá sạch nợ, tức giả vờ rằng bỏ **một** đoạn đủ trả **mọi** khoản nợ.

    Mô hình đúng: bỏ một đoạn chỉ mua lại đúng ngân sách của đoạn đó. Nợ lớn thì
    cần nhiều lần cắt — điều đó tự giới hạn và trung thực.
    """
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(10, cach_giay=1.0, noi_giay=1.0)
    ke = tg.lap_ke_hoach(muc, _dai(muc, 2.2), tong_giay=30.0)

    # 🔴 **Viết lại 28/09: ⛔ KHÔNG đoạn nào bị cắt, nên ⛔ không còn "một lần
    #    cắt" nào để mà đúng hay sai.** Bất biến MỚI mạnh hơn bất biến cũ.
    assert all(d["cat_bot_ms"] == 0 for d in ke["doan"]), (
        "⛔ KHÔNG BAO GIỜ bỏ câu — nấc 5 nén thêm thay vì cắt")
    assert all(d["dai_ms"] > 0 for d in ke["doan"]), (
        "mọi đoạn phải còn tiếng: một `dai_ms == 0` là một câu khách đã mất")
    assert len(ke["doan"]) == len(muc), "⛔ không đoạn nào được biến mất"


def test_doan_bi_cat_duoc_DEM_de_QC_bao_cao():
    """ADR-003 T12 — mất lời thoại là một khiếm khuyết chất lượng, không phải
    một chi tiết kỹ thuật."""
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(10, cach_giay=1.0, noi_giay=1.0)
    ke = tg.lap_ke_hoach(muc, _dai(muc, 2.2), tong_giay=30.0)
    # 🔴 **Viết lại 28/09**: con số vẫn phải TỚI được QC, nhưng nay nó luôn `0`
    #    và `0` có nghĩa *"ta ⛔ không bao giờ bỏ câu"*. Giữ đường dẫn của nó là
    #    giữ khả năng phát hiện một cỗ máy cắt thứ ba xuất hiện sau này.
    assert tg.tom_tat(ke)["so_doan_bi_cat"] == ke["so_doan_bi_cat"] == 0


# ══════════════════════════════════════════════════════════════════════════════
#  §4 Bất biến không được vi phạm
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_long_tieng_KHONG_BAO_GIO_dai_hon_video():
    """T2 / D-ASV-03 — luồng hình được **sao chép**, nên tổng thời lượng là một
    con số cố định, không co giãn."""
    from apps.auto_scan_video import thoi_gian as tg

    # 🔑 **Hai hình dạng, và CẢ HAI đều giữ T2** (viết lại 28/09):
    #      · vừa được ⇒ `ket_cuoi_ms <= tong_ms`;
    #      · ⛔ không vừa kể cả khi mọi đoạn đã ở trần KỸ THUẬT ⇒ **NÉM**.
    #    ⛔ Cái ⛔ KHÔNG còn là một lựa chọn: giao một bản thiếu câu.
    muc = _muc(6, cach_giay=1.0, noi_giay=1.0)
    try:
        ke = tg.lap_ke_hoach(muc, _dai(muc, 3.0), tong_giay=8.0)
    except tg.ThoiGianError as exc:
        assert "dài hơn video" in str(exc), (
            f"phải nói rõ vì sao ⛔ không vừa, nhận: {exc}")
    else:
        assert ke["ket_cuoi_ms"] <= ke["tong_ms"]
        assert ke["so_doan_bi_cat"] == 0


def test_che_do_natural_KHONG_duoc_keo_dai_video():
    """`MVP_CONTRACT.md` §6 nói rõ. Phần dư bị cắt tại biên đoạn cuối vừa lọt."""
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(5, cach_giay=1.0, noi_giay=1.0)
    try:
        ke = tg.lap_ke_hoach(muc, _dai(muc, 2.5), tong_giay=6.0,
                             che_do="natural")
    except tg.ThoiGianError as exc:
        # ⭐ Viết lại 28/09: ⛔ không còn cắt đuôi, nên ca ⛔ không vừa thì NÉM.
        assert "dài hơn video" in str(exc)
    else:
        assert ke["ket_cuoi_ms"] <= ke["tong_ms"]
        assert ke["so_doan_bi_cat"] == 0


def test_chong_lan_KHONG_vuot_tran():
    """⛔ Hai câu chồng nhau 0,2 s nghe tự nhiên; 0,5 s thì thành hai người cùng
    nói. Theo `avoid_overlap` của SoniTranslate cho trường hợp cùng người nói."""
    from apps.auto_scan_video import thoi_gian as tg

    for cach in (0.8, 1.0, 1.5, 2.0):
        muc = _muc(6, cach_giay=cach, noi_giay=0.7)
        ke = tg.lap_ke_hoach(muc, _dai(muc, 1.4), tong_giay=20.0)
        truoc = None
        for d in ke["doan"]:
            if d["dai_ms"] == 0:
                continue
            if truoc is not None:
                assert d["dat_tai_ms"] + tg.TRAN_CHONG_LAN_MS >= truoc, (
                    f"chồng lấn quá {tg.TRAN_CHONG_LAN_MS} ms ở cách={cach}")
            truoc = d["dat_tai_ms"] + d["dai_ms"]


def test_ke_hoach_thieu_tieng_bi_TU_CHOI():
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(3, cach_giay=2.0)
    with pytest.raises(tg.ThoiGianError):
        tg.lap_ke_hoach(muc, {"seg_0000": 1.0}, tong_giay=10.0)


def test_che_do_khong_hop_le_bi_TU_CHOI():
    from apps.auto_scan_video import thoi_gian as tg

    muc = _muc(2, cach_giay=2.0)
    with pytest.raises(tg.ThoiGianError):
        tg.lap_ke_hoach(muc, _dai(muc, 1.0), tong_giay=10.0, che_do="bia_ra")


def test_KHONG_cham_tep_am_thanh_nao():
    """⛔ Prompt 13 / ADR-003: giai đoạn này ra một KẾ HOẠCH.

    Ghép là việc của COMPOSE/RENDER. Trộn hai việc lại là giấu một quyết định
    thời gian bên trong một phép ghép — nơi không ai đi tìm nó.
    """
    import inspect

    from apps.auto_scan_video import thoi_gian
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    ma = inspect.getsource(thoi_gian)
    assert _vi_pham(ma, ("AudioSegment", "atempo", "concat", "ffmpeg")) == []


# ══════════════════════════════════════════════════════════════════════════════
#  §5 Vân tay
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_doi_theo_dau_vao_va_che_do():
    from apps.auto_scan_video import thoi_gian as tg

    goc = dict(checksum_van_ban="aaa", ban_ke_tieng="bbb", che_do="fit_original")
    nen = tg.van_tay_ke_hoach(**goc)

    assert nen != tg.van_tay_ke_hoach(**{**goc, "checksum_van_ban": "xxx"})
    assert nen != tg.van_tay_ke_hoach(**{**goc, "ban_ke_tieng": "yyy"})
    assert nen != tg.van_tay_ke_hoach(**{**goc, "che_do": "natural"})


@pytest.mark.parametrize("ten", [
    "TY_LE_MUON_KHOANG_LANG", "TRAN_TANG_TOC", "TRAN_TROI_SO_DOAN",
    "TRAN_CHONG_LAN_MS",
])
def test_doi_bat_ky_HANG_SO_nao_cung_doi_van_tay(monkeypatch, ten):
    """O13 — đổi một hằng số là đổi kế hoạch, nên cache cũ phải vô hiệu."""
    from apps.auto_scan_video import thoi_gian as tg

    goc = dict(checksum_van_ban="aaa", ban_ke_tieng="bbb", che_do="fit_original")
    truoc = tg.van_tay_ke_hoach(**goc)
    monkeypatch.setattr(tg, ten, getattr(tg, ten) * 2)
    assert tg.van_tay_ke_hoach(**goc) != truoc, f"{ten} không vào vân tay"


# ══════════════════════════════════════════════════════════════════════════════
#  §6 Chờ bằng chứng ngoài
# ══════════════════════════════════════════════════════════════════════════════

class TestChoBangChungNgoai:
    """Ba con số, ba nguồn gốc — và sự khác nhau đó quan trọng."""

    def test_hai_nguong_MUON_chua_do_lai_tren_tieng_Viet(self):
        """⚠️ `TY_LE_MUON_KHOANG_LANG` và `TRAN_TANG_TOC` là ngưỡng **mượn** từ
        SoniTranslate và Subdub — hai dự án làm cho tiếng Anh/Tây Ban Nha.

        Kho này có luật: mượn ngưỡng thì phải đo lại. Đo trên tiếng Việt cần
        máy sinh tiếng thật (RISK-12-01), nên món nợ này chưa trả được.
        """
        from apps.auto_scan_video import thoi_gian as tg

        assert tg.TY_LE_MUON_KHOANG_LANG == 0.7, "SoniTranslate"
        assert tg.TRAN_TANG_TOC == 1.15, "Subdub"

    def test_tran_ba_doan_la_LUA_CHON_chua_phai_phep_do(self):
        """⚠️ `TRAN_TROI_SO_DOAN = 3` là **lựa chọn có lý lẽ**, không phải một
        phép đo, và không dự án tham chiếu nào có nó.

        Lý lẽ: một đoạn quá chặt (một câu dài hơn bình thường đã đủ vượt), quá
        nhiều thì trần mất tác dụng. Ba đoạn ≈ 6–10 giây, vẫn trong khoảng người
        xem chưa thấy tiếng rời khỏi hình.

        Đo thật cần người nghe chấm trên nội dung thật — thuộc pha 21.
        """
        from apps.auto_scan_video import thoi_gian as tg

        assert tg.TRAN_TROI_SO_DOAN == 3

    def test_chua_do_ty_le_dai_that_cua_tieng_Viet(self):
        """🔴 RISK-02-01 vẫn mở.

        Cả mô hình này dựng trên giả định "tiếng Việt dài hơn nhưng khoảng lặng
        gánh được". Kịch bản trong tệp này dùng tỷ lệ **giả định** (1,5×–2,2×);
        tỷ lệ **thật** cần một lần chạy đầu-tới-cuối với model và máy sinh tiếng
        thật.

        Ghi ra để pha 21 không tưởng rằng mô hình đã được nghiệm thu trên dữ
        liệu thật.
        """
        from apps.auto_scan_video import giong_noi

        assert giong_noi.san_sang() is False, (
            "Máy sinh tiếng đã sẵn sàng — hãy ĐO tỷ lệ dài thật của tiếng Việt "
            "trên nội dung thật, cập nhật RISK-02-01, rồi xoá phép kiểm này.")
