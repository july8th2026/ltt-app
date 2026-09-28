"""test_4922 — B15: NẤC 0 (xén lặng TTS) và HAI cỗ máy cắt được tách ra.

⭐ Hàm thuần: ⛔ không model, ⛔ không ffmpeg, ⛔ không CSDL, ⛔ không kho. WAV được
dựng bằng `wave` của thư viện chuẩn ngay trong bộ kiểm.

## Số đo thật đứng sau bộ kiểm này

Lượt `asvr_47327a869a8f4597960048f09064740` (69 tệp tiếng sở hữu, 122,56 s):

    lặng ĐẦU 4,98 s + lặng CUỐI 8,67 s = 13,65 s = 11,1 % tổng độ dài
    ⇒ số đoạn vượt trần 1,15:  2 → 0
    ⇒ điểm vỡ của popper đuôi: k = 1,15 → k = 1,35

⚠️ `n = 1` video. Con số 11,1 % là của phim NÀY, ⛔ không phải một hằng số sản
phẩm — bộ kiểm dưới đây chốt **cơ chế**, ⛔ không chốt 11,1 %.
"""
from __future__ import annotations

import array
import io
import math
import wave

import pytest

from apps.auto_scan_video import giai_doan_giong as gg, thoi_gian as tg

SR = 24_000


def _wav(dau_s: float, tieng_s: float, cuoi_s: float, *, ch: int = 1,
         bien_do: int = 8000) -> bytes:
    """WAV `int16`: lặng `dau_s` — sin `tieng_s` — lặng `cuoi_s`."""
    mau = array.array("h")
    for _ in range(int(SR * dau_s)):
        mau.append(0)
    for i in range(int(SR * tieng_s)):
        mau.append(int(bien_do * math.sin(2 * math.pi * 440 * i / SR)))
    for _ in range(int(SR * cuoi_s)):
        mau.append(0)
    if ch > 1:
        keo = array.array("h")
        for x in mau:
            keo.extend([x] * ch)
        mau = keo
    ra = io.BytesIO()
    with wave.open(ra, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(mau.tobytes())
    return ra.getvalue()


def _giay(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav), "rb") as w:
        return w.getnframes() / w.getframerate()


# ══════════════════════════════════════════════════════════════════════════════
#  §1 NẤC 0 — xén đúng cái phải xén
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dau,tieng,cuoi", [
    (0.30, 1.00, 0.50),
    (0.00, 1.00, 0.40),
    (0.25, 2.00, 0.00),
    (0.20, 0.50, 0.20),
])
def test_4922_xen_dung_phan_lang_hai_dau(dau, tieng, cuoi):
    """⭐ Xén ra phải ≈ `dau + cuoi`, dung sai một CỬA SỔ mỗi đầu (10 ms)."""
    goc = _wav(dau, tieng, cuoi)
    moi, xen = gg.xen_lang_hai_dau(goc)
    cua = gg._CUA_LANG_MS / 1000.0
    assert xen == pytest.approx(dau + cuoi, abs=2 * cua + 1e-6), (
        f"xén {xen:.3f}s, chờ {dau + cuoi:.3f}s")
    assert _giay(moi) == pytest.approx(_giay(goc) - xen, abs=1e-6), (
        "độ dài tệp mới phải bằng độ dài cũ trừ đúng phần đã xén")
    # ⛔ Phần TIẾNG ⛔ không được xén mất: tệp mới >= độ dài tiếng.
    assert _giay(moi) >= tieng - 2 * cua


def test_4922_KHONG_xen_gi_khi_khong_co_lang():
    """⭐ `0.0` ở đây nghĩa *"không có gì để xén"* — và tệp phải y NGUYÊN byte."""
    goc = _wav(0.0, 1.5, 0.0)
    moi, xen = gg.xen_lang_hai_dau(goc)
    assert xen == pytest.approx(0.0, abs=gg._CUA_LANG_MS / 1000.0)
    assert _giay(moi) == pytest.approx(_giay(goc), abs=1e-6)


def test_4922_tep_LANG_HOAN_TOAN_tra_ve_NGUYEN_VEN():
    """🔴 Một khe **CỐ Ý im lặng** (Task 25) là một tệp lặng từ đầu đến cuối.

    ⛔ Xén nó "đúng" là xén về **0 giây**, và `giong_noi.kiem_tep_tieng` sẽ NÉM
       *"Tệp tiếng sinh ra quá ngắn"* ⇒ **chết cả lượt chạy** vì một tối ưu.
    """
    goc = _wav(0.0, 0.0, 2.0)          # toàn bộ là lặng
    moi, xen = gg.xen_lang_hai_dau(goc)
    assert moi == goc, "tệp lặng hoàn toàn phải trả về NGUYÊN VẸN từng byte"
    assert xen == 0.0


def test_4922_SAN_chan_viec_xen_xuong_qua_ngan():
    """⚠️ Dưới `_SAN_XEN_S` thì trả nguyên vẹn — sàn là hàng rào cuối."""
    assert gg._SAN_XEN_S > 0
    goc = _wav(0.5, 0.05, 0.5)         # tiếng chỉ 50 ms
    moi, xen = gg.xen_lang_hai_dau(goc)
    assert moi == goc and xen == 0.0


def test_4922_dinh_dang_LA_tra_ve_nguyen_ven_chu_KHONG_nem():
    """⚠️ Một phép xén sai trên định dạng lạ là một tệp HỎNG giao cho khách;
       trả nguyên vẹn chỉ là mất một tối ưu. ⇒ ⛔ không đoán, ⛔ không ném."""
    for rac in (b"", b"khong phai wav", b"RIFF" + b"\x00" * 20):
        moi, xen = gg.xen_lang_hai_dau(rac)
        assert moi == rac and xen == 0.0


def test_4922_stereo_giu_dung_so_kenh_va_tan_so():
    """⛔ Xén ⛔ không được đổi `nchannels`/`framerate` — hạ nguồn trộn theo chúng."""
    goc = _wav(0.3, 1.0, 0.3, ch=2)
    moi, xen = gg.xen_lang_hai_dau(goc)
    assert xen > 0.0
    with wave.open(io.BytesIO(moi), "rb") as w:
        assert (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (2, SR, 2)


def test_4922_nac0_chay_TRUOC_phep_DO():
    """🔑 **Thứ tự là toàn bộ giá trị của nấc 0.**

    `kiem_tep_tieng` đo con số đi vào `ban_ke.giay` → vào MẪU SỐ của
    `he_so_co_gian`. Xén SAU khi đo là đo một đại lượng khách ⛔ không nghe, và
    là nén giọng người để nhét vừa một khoảng im lặng.

    ⭐ Chốt bằng AST: lời gọi `xen_lang_hai_dau` phải đứng TRƯỚC
       `kiem_tep_tieng` trong thân `chay`.
    """
    import ast
    import pathlib

    src = pathlib.Path(gg.__file__).read_text("utf-8")
    cay = ast.parse(src)
    goi = [(n.lineno, n.func.attr if isinstance(n.func, ast.Attribute)
            else getattr(n.func, "id", ""))
           for n in ast.walk(cay) if isinstance(n, ast.Call)]
    xen = [ln for ln, ten in goi if ten == "xen_lang_hai_dau"]
    do = [ln for ln, ten in goi if ten == "kiem_tep_tieng"]
    assert xen, "⛔ không ai gọi `xen_lang_hai_dau` — nấc 0 là mã chết"
    assert do, "⛔ không tìm thấy `kiem_tep_tieng` — bài này đã mù"
    assert min(xen) < min(do), (
        f"`xen_lang_hai_dau` (dòng {min(xen)}) phải đứng TRƯỚC "
        f"`kiem_tep_tieng` (dòng {min(do)})")


# ══════════════════════════════════════════════════════════════════════════════
#  §2 HAI cỗ máy cắt, HAI con số
# ══════════════════════════════════════════════════════════════════════════════

def _muc(so: int, *, cach: float, noi: float = 1.0):
    return [{"ma": f"seg_{i:04d}", "bat": i * cach, "ket": i * cach + noi,
             "chu": f"cau {i}"} for i in range(so)]


def test_4922_so_doan_bi_cat_la_TONG_cua_hai_co_may():
    """⭐ Khoá cũ GIỮ NGUYÊN nghĩa *"tổng số đoạn khách mất"* — bốn chỗ hạ nguồn
       đọc nó. Hai khoá MỚI nói **vì sao**."""
    muc = _muc(6, cach=2.0)
    ke = tg.lap_ke_hoach(muc, {m["ma"]: 1.0 for m in muc}, tong_giay=20.0)
    assert (ke["so_doan_bi_cat"]
            == ke["so_doan_cat_vi_no"] + ke["so_doan_cat_vi_duoi"])
    assert tg.tom_tat(ke)["so_doan_bi_cat"] == ke["so_doan_bi_cat"]


def test_4922_popper_DUOI_cat_KHI_tran_no_KHONG_cat():
    """🔴 **Phát hiện 28/09, và nó đảo ngược tiền đề của cả hạng mục.**

    Một đoạn ĐUÔI dài hơn phần video còn lại bị `pop()` bởi vòng `while` ở cuối
    `lap_ke_hoach` — **⛔ không** bởi `TRAN_TROI_SO_DOAN`. Ở ca dưới nợ khi bước
    vào đoạn cuối là `0`, nên nhánh cắt-vì-nợ ⛔ không thể chạy; thế mà khách vẫn
    mất một câu. ⇒ *"⛔ không bao giờ cắt"* + *"⛔ không bao giờ dài hơn nguồn"*
    (T2 / `D-ASV-03`) là **bất khả** trên đầu vào đủ dồn.

    ⭐ Và đó là lý do phải có HAI con số: một số gộp đã che mất điều này.

    ⚠️ **⛔ Đừng thử "tắt" trần nợ bằng cách nâng `TRAN_TROI_SO_DOAN` lên vô
       cực** — bản đầu của bài này làm thế và nó ⛔ KHÔNG tắt: `tran` là
       `sum(ngan_sach_doan(j) for j in range(i, min(len(muc), i + N)))`, và
       `min(...)` kẹp cửa sổ về `len(muc)`, nên với `i` gần cuối `tran` **teo
       lại** và nhánh nợ vẫn nổ (đo được: 24 lần). Một phép "tắt" ⛔ không tắt là
       một tiền đề sai, và nó làm bài kiểm nói về một thứ khác.
    """
    # Đoạn cuối bắt đầu ở 8 s, tiếng dài 5 s, video chỉ 10 s ⇒ tràn 3 s.
    muc = [{"ma": "seg_0000", "bat": 0.0, "ket": 1.0, "chu": "a"},
           {"ma": "seg_0001", "bat": 8.0, "ket": 9.0, "chu": "b"}]
    dai = {"seg_0000": 1.0, "seg_0001": 5.0}
    ke = tg.lap_ke_hoach(muc, dai, tong_giay=10.0,
                         he_so_da_ap={"seg_0000": 1.0, "seg_0001": 1.0})

    assert ke["so_doan_cat_vi_no"] == 0, (
        "nợ khi bước vào đoạn cuối là 0 ⇒ nhánh cắt-vì-nợ ⛔ không thể chạy")
    assert ke["so_doan_cat_vi_duoi"] == 1, (
        "popper đuôi PHẢI cắt — nó là thứ cưỡng chế T2, và một bộ kiểm nói "
        "ngược lại nghĩa là T2 đang do ai khác giữ")
    assert ke["so_doan_bi_cat"] == 1
    # ⭐ Và T2 vẫn đứng: `kiem()` đã chạy trong `lap_ke_hoach`.
    assert ke["ket_cuoi_ms"] <= ke["tong_ms"]


def test_4922_hai_khoa_moi_KHONG_vao_tom_tat_PHANG():
    """⚠️ Chúng đi qua `outputs["master"]`, ⛔ không qua `tom_tat` phẳng.

    Lý do cơ học: mỗi khoá phẳng mới của `thoi_gian.tom_tat` phải được khai ở
    `asv_doi_soat.KHOA_{CAN,BO_QUA_CO_Y}` (`test_408` chốt hai chiều), và
    `tools/` ⛔ không thuộc làn này. `master` là MỘT khoá trong `KHOA_CAN` nên
    khoá con thêm được tự do — cùng đường đã dùng cho B13-B4.
    """
    import pathlib

    tl = tg.tom_tat({"doan": []})
    assert "so_doan_cat_vi_no" not in tl
    assert "so_doan_cat_vi_duoi" not in tl
    src = pathlib.Path(
        tg.__file__).parent.joinpath("giai_doan_thoi_gian.py").read_text("utf-8")
    for k in ("so_doan_cat_vi_no", "so_doan_cat_vi_duoi"):
        assert f'do_duoc["{k}"]' in src, (
            f"`{k}` phải được xuất xuống `master`, nếu không nó là một con số "
            f"được GHI mà ⛔ không ai đọc")


def test_4922_giay_xen_di_theo_TUNG_LUOT_DOC_chu_khong_thanh_khoa_phang():
    """⭐ `giay_xen` nằm trong mỗi bản ghi `tung_luot_doc`, ⛔ không phải một khoá
       PHẲNG của `tom_tat`.

    Hai lẽ: (i) mỗi khoá phẳng mới phải được khai ở `asv_doi_soat`, thứ thuộc
    `tools/` ⛔ không phải làn này; (ii) nó ĐÚNG HƠN — nói xén được bao nhiêu ở
    ĐOẠN NÀO thay vì một con số gộp bắt người đọc đi tìm.

    ⛔ Và `None` ≠ `0.0`: vắng mặt = lượt đọc ⛔ KHÔNG đi qua nấc 0 (lượt chạy cũ,
       hoặc tệp ⛔ không phải PCM 16-bit); `0.0` = đã đi qua, ⛔ không có gì để xén.
    """
    from apps.auto_scan_video import nan_cho_vua

    co = nan_cho_vua.ban_ghi_luot_doc("seg_0001", vong=0, giay=2.0, khe=2.0,
                                      giay_xen=0.31)
    khong = nan_cho_vua.ban_ghi_luot_doc("seg_0001", vong=0, giay=2.0, khe=2.0)
    zero = nan_cho_vua.ban_ghi_luot_doc("seg_0001", vong=0, giay=2.0, khe=2.0,
                                        giay_xen=0.0)
    assert co["giay_xen"] == pytest.approx(0.31)
    assert "giay_xen" not in khong, "⛔ vắng mặt phải là khoá VẮNG"
    assert zero["giay_xen"] == 0.0, "`0.0` phải đi qua được, ⛔ không bị bỏ"
    # ⛔ Và nó ⛔ KHÔNG được là một khoá phẳng của `tom_tat`.
    assert "giay_xen_lang" not in nan_cho_vua.tom_tat([], tung_luot_doc=[])


def test_4922_van_tay_da_tang_theo_hinh_dang_moi():
    """⚠️ `ke_hoach` có hai khoá mới ⇒ một kế hoạch cũ đọc bằng mã mới sẽ báo
       `0`/`0` — một lời khai SAI về nguyên nhân, ⛔ không phải trường thiếu."""
    assert tg.PHIEN_BAN_THOI_GIAN >= 4
