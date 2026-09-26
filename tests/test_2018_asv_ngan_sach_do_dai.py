"""R-04 — NGAN SACH DO DAI cua mot cau long tieng, va DONG HO cua giai doan GIONG.

Luot nghiem thu nen v3 (23/09) do duoc `voice_synthesis` = 943 giay cho mot phim
107 giay. `tools/do_toc_do_giong.py` tach con so ay lam hai va chi ra nguyen nhan
o dau chuoi — chi tiet + so lieu: `docs/auto_scan_video_final/L_FIX_TOC_DO.md`.

Bon cua, moi cua mot cau hoi:

  §1 `ngon_ngu.NHIP`              — nhip doc la MOT con so DO DUOC, moi noi tinh ra tu no
  §2 `ngan_sach_do_dai`           — tran DEM DUOC, khong phai mot phep nhan giao cho model
  §3 loi nhac mang tran do        — ca pha VIET DAU lan pha NAN, cung mot nguon
  §4 `giai_doan_giong` co dong ho — "cham vi cai gi" tra loi duoc tu bang chung cua luot

⛔ Khong phep kiem nao o day goi model hay may sinh tieng that.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ai, giai_doan_giong, long_tieng,  # noqa: E402
                                  nan_cho_vua, ngon_ngu as nn)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Nhip doc: MOT con so, moi cum tinh ra tu no
# ══════════════════════════════════════════════════════════════════════════════

def test_nhip_phu_kin_moi_dich_hop_le():
    """Mot dich khong co nhip = mot dich khong tinh duoc ngan sach do dai."""
    for m in nn.DICH_HOP_LE:
        assert m in nn.NHIP and nn.NHIP[m] > 0
        assert m in nn.DON_VI_DO_DAI


def test_cum_loi_nhac_TINH_RA_tu_NHIP_chu_khong_go_tay():
    """🔴 Tai hien nguyen nhan goc cua R-04.

    Truoc 23/09 `CUM[vi]["nhip"]` la chuoi `"khoang 4,5 am tiet/giay"` go tay,
    va khong con so nao ben canh no. Nen khi phep do that cho ra 3,35 thi khong
    co cho nao de sua **mot lan**: chuoi nam o `CUM`, phep nhan nam trong dau
    model, va khong ai doi chieu hai thu do.
    """
    for m in nn.DICH_HOP_LE:
        n = f"{nn.NHIP[m]:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        assert nn.CUM[m]["nhip"] == f"khoang {n} {nn.DON_VI_DO_DAI[m]}/giay"
        assert nn.CUM[m]["nhip_moi_giay"] == \
            f"khoang {n} {nn.DON_VI_DO_DAI[m]} moi giay"


def test_nhip_vi_la_so_DA_DO_khong_phai_4_5():
    """⛔ Banh coc: khong duoc quay ve con so chua do.

    3,35 am tiet/giay — `tools/do_toc_do_giong.py --che-do tts`, hai vong tren
    sau doan tieng Viet that cua luot nen v3, giong `Minh Duc`:
    trung binh 3,349 va 3,324; bien 3,04-3,51.
    """
    assert nn.NHIP["vi"] == pytest.approx(3.35)


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Tran DEM DUOC
# ══════════════════════════════════════════════════════════════════════════════

def test_ngan_sach_do_dai_la_so_nguyen_duong_va_TANG_theo_khe():
    assert nn.ngan_sach_do_dai(19.879, "vi") == 61
    assert nn.ngan_sach_do_dai(4.553, "vi") == 14
    assert nn.ngan_sach_do_dai(0.0, "vi") >= 1
    truoc = 0
    for giay in (1, 5, 10, 30, 60):
        n = nn.ngan_sach_do_dai(giay, "vi")
        assert isinstance(n, int) and n > truoc
        truoc = n


def test_ngan_sach_NHAM_THAP_hon_khe_va_he_so_o_MOT_cho():
    """`HE_SO_MUC_TIEU` la nguon duy nhat — `nan_cho_vua` khong go lai 0,92."""
    assert 0.8 <= nn.HE_SO_MUC_TIEU < 1.0
    assert nn.ngan_sach_do_dai(10.0, "vi") < round(10.0 * nn.NHIP["vi"])
    # ⚠️ **26/09 (Task 22) — DUONG doi, Y DINH giu.** `loi_nhac_nan` da bi xoa;
    #    loi nhac NAN con lai la `loi_nhac_nan_lo`. Va pham vi ROI RA: chot tren
    #    CA MODULE thay vi mot ham, vi mon no dung la mot ban lo **khong he doc**
    #    `HE_SO_MUC_TIEU` — mot phep kiem nham vao MOT ten ham khong bat duoc
    #    dieu do (ho `banh-coc-do-cach-go`).
    ma = inspect.getsource(nan_cho_vua.loi_nhac_nan_lo)
    assert "ngon_ngu.HE_SO_MUC_TIEU" in ma
    ca_module = inspect.getsource(nan_cho_vua)
    assert "* 0.92" not in ca_module and "*0.92" not in ca_module


def test_ngan_sach_tu_choi_dich_ngoai_hop_dong():
    with pytest.raises(nn.NgonNguError):
        nn.ngan_sach_do_dai(5.0, "ja")


def test_bien_do_DO_DUOC_cua_may_sinh_tieng_NAM_TRONG_dung_sai():
    """🔑 Vi sao he so la 0,92 chu khong phai 1,0 — va no kiem duoc.

    Nhip do duoc bien thien 3,04-3,51 am tiet/giay. Mot cau viet dung ngan sach
    (`NHIP x HE_SO_MUC_TIEU`) doc o hai dau bien do deu phai con nam trong dung
    sai cua `nan_cho_vua` — neu khong, bac thang nan lai chay o **moi** doan y
    het truoc 23/09.
    """
    khe = 20.0
    n = nn.ngan_sach_do_dai(khe, "vi")
    for nhip_that in (3.04, 3.51):
        giay = n / nhip_that
        assert not nan_cho_vua.can_nan(giay, khe), (
            f"nhip that {nhip_that} -> {giay:.2f}s cho khe {khe}s: van phai nan")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Loi nhac mang tran — CA HAI pha
# ══════════════════════════════════════════════════════════════════════════════

def _than(msg) -> tuple[str, dict]:
    return msg[0]["content"], json.loads(msg[1]["content"])


def test_loi_nhac_VIET_DAU_mang_tran_dem_duoc_cho_TUNG_doan():
    d = [{"ma": "a", "chu": "x", "bat": 0.0, "ket": 19.879},
         {"ma": "b", "chu": "y", "bat": 19.879, "ket": 24.432}]
    he_thong, nguoi_dung = _than(
        long_tieng.loi_nhac(d, tat_ca=d, ngon_ngu_goc="zh", dac_diem_giong={}))
    assert "do_dai_toi_da" in he_thong and "am tiet" in he_thong
    theo_ma = {m["ma"]: m for m in nguoi_dung["doan"]}
    assert theo_ma["a"]["do_dai_toi_da"] == nn.ngan_sach_do_dai(19.879, "vi")
    assert theo_ma["b"]["do_dai_toi_da"] == nn.ngan_sach_do_dai(4.553, "vi")


def test_loi_nhac_NAN_mang_CUNG_tran_voi_pha_viet_dau():
    """Hai pha nham hai dich khac nhau tren cung mot khe thi vong hai khong hoi tu.

    🔴 **26/09 (Task 22) — DUONG doi, Y DINH giu, va bai nay DA DO khi doi.**

       Bai cu do `loi_nhac_nan` (mot doan mot luot). Task 12 (`96e27cff`) chuyen
       `giai_doan_giong` sang `loi_nhac_nan_lo`, va ban lo ⛔ **khong mang
       `do_dai_toi_da` lan `muc_tieu_giay`** — tuc bat bien nay bi bo roi im lang
       trong khi bai kiem van xanh vi no do **ham cu**, thu khong con ai goi.
       Day dung la hinh dang `doc-thu-dai-dien-thay-vi-doc-thu-that`.
    """
    khe = 13.818
    he_thong, nguoi_dung = _than(nan_cho_vua.loi_nhac_nan_lo(
        [{"ma": "a", "chu": "y", "giay_doc": 18.0, "khe": khe}]))
    assert "do_dai_toi_da" in he_thong
    muc = nguoi_dung["a"]
    assert muc["do_dai_toi_da"] == nn.ngan_sach_do_dai(khe, "vi")
    assert muc["muc_tieu_giay"] == round(khe * nn.HE_SO_MUC_TIEU, 2)


def test_loi_nhac_en_KHONG_mang_don_vi_tieng_Viet():
    d = [{"ma": "a", "chu": "x", "bat": 0.0, "ket": 10.0}]
    he_thong, nguoi_dung = _than(long_tieng.loi_nhac(
        d, tat_ca=d, ngon_ngu_goc="zh", dac_diem_giong={}, ngon_ngu_dich="en"))
    assert "am tiet" not in he_thong and " tu" in he_thong
    assert nguoi_dung["doan"][0]["do_dai_toi_da"] == \
        nn.ngan_sach_do_dai(10.0, "en")


def test_doi_tran_do_dai_lam_DOI_VAN_TAY_ban_long_tieng():
    """⛔ Doi loi nhac ma giu van tay = lan chay sau dung lai ban cua loi nhac cu."""
    assert long_tieng.PHIEN_BAN_LONG_TIENG >= 2
    assert nan_cho_vua.PHIEN_BAN_NAN >= 2


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Dong ho cua giai doan GIONG + muc suy nghi cua thao tac NAN
# ══════════════════════════════════════════════════════════════════════════════

def test_giai_doan_giong_GHI_giay_TTS_va_giay_LLM_rieng():
    """Luot nen v3 chi biet TONG (943 giay) — phai do lai ngoai san pham moi
    biet 751 giay la LLM. Hai con so nay lam cau do khong phai hoi lan hai."""
    ma = inspect.getsource(giai_doan_giong.chay)
    assert '"giay_tts"' in ma and '"giay_llm_nan"' in ma
    assert "time.monotonic()" in ma


def test_thao_tac_NAN_khai_muc_suy_nghi_THAP():
    """🔑 `rut_ngan_cho_vua` la thao tac de nhat trong nam; do duoc 68,3 giay/luot
    o `medium` va 47,7 o `low` (cung 6/6 `stop`, cung 6/6 cau ngan hon)."""
    assert ai.RUT_NGAN_CHO_VUA.muc_nghi == "low"
    # ⛔ `none` bi `ltt_llm` tu choi tu 14/09 — khong thao tac nao duoc khai no.
    assert all(t.muc_nghi != "none" for t in ai.THAO_TAC)


def test_ai_goi_TRUYEN_muc_nghi_cua_thao_tac_xuong_dieu_phoi():
    ma = inspect.getsource(ai.goi)
    assert "reasoning_effort" in ma and "thao_tac.muc_nghi" in ma


def test_cua_TIEU_TIEN_phai_doc_NGAN_SACH_khong_doc_khe_cua():
    """🔴 Đ4: đoạn vừa được nếu mượn khoảng lặng thì ⛔ KHÔNG được gọi LLM.

    Chốt bằng AST: `nen_viet_lai` trong `giai_doan_giong` ⛔ không được nhận biến
    tên `khe`. Một phép kiểm hành vi ở đây phải dựng cả máy sinh tiếng; một phép
    kiểm hình dạng thì bắt đúng cái sai và ⛔ không đòi GPU.
    """
    import ast

    cay = ast.parse(inspect.getsource(giai_doan_giong))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "nen_viet_lai"]
    assert goi, "khong tim thay loi goi nen_viet_lai"
    for n in goi:
        ten = [a.id for a in n.args if isinstance(a, ast.Name)]
        assert "khe" not in ten, (
            "cua tieu tien van doc `khe` (= ket - bat). Phai doc `ngan_sach` "
            "(da gom khoang lang muon duoc) — xem thoi_gian.ngan_sach_nan_s")
        assert "ngan_sach" in ten, "cua tieu tien chua doc ngan_sach"


def test_dong_ho_giai_doan_giong_co_bo_dem_nan_oan():
    """Đ4 phải ĐẾM ĐƯỢC, ⛔ không phải suy ra từ log."""
    ma = inspect.getsource(giai_doan_giong)
    assert '"so_doan_nan_oan"' in ma, (
        "thieu bo dem D4: so doan `giay > khe` NHUNG `giay <= ngan_sach`")


def test_tom_tat_XUAT_so_doan_nan_oan_that_su():
    """🔴 Task 15, Lo #1 — phan biet 'da KHAI' voi 'da XUAT RA'.

    Bai `test_dong_ho_giai_doan_giong_co_bo_dem_nan_oan` (ngay tren) chi kham
    pha CHUOI `'"so_doan_nan_oan"'` co mat o dau do trong tep — no XANH du
    chuoi ay chi la ten khoa cua `dong_ho` (dong khai `{"giay_tts": ...,
    "so_doan_nan_oan": 0}` va dong tang `dong_ho["so_doan_nan_oan"] += 1`), du
    con so ay KHONG BAO GIO duoc dua vao dict `tom_tat` ma `chay()` tra ve —
    dung dieu da xay ra: `tools/asv_doi_soat.py` doc `outputs["tom_tat"]` va
    luon nhan `None`.

    Bai nay doc dung NUT AST cua dict LIEU duoc `return` lam gia tri cua khoa
    `"tom_tat"` trong `chay()`, va khang dinh `"so_doan_nan_oan"` la MOT KHOA
    CUA CHINH DICT DO — ⛔ khong phai "co mat trong tep". Xoa dong xuat ra
    (`"so_doan_nan_oan": dong_ho["so_doan_nan_oan"],`) nhung GIU nguyen dong
    khai `dong_ho` se lam bai nay DO, dung cai ma bai cu ⛔ khong lam duoc.
    """
    import ast

    cay = ast.parse(inspect.getsource(giai_doan_giong.chay))
    tom_tat_dict: ast.Dict | None = None
    for node in ast.walk(cay):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        for k, v in zip(node.value.keys, node.value.values, strict=True):
            if (isinstance(k, ast.Constant) and k.value == "tom_tat"
                    and isinstance(v, ast.Dict)):
                tom_tat_dict = v
    assert tom_tat_dict is not None, (
        "khong tim thay dict LIEU tra ve o khoa 'tom_tat' trong giai_doan_giong.chay")
    khoa = {k.value for k in tom_tat_dict.keys if isinstance(k, ast.Constant)}
    assert "so_doan_nan_oan" in khoa, (
        "dong_ho['so_doan_nan_oan'] duoc TANG o [F] nhung ⛔ KHONG duoc xuat "
        "vao dict 'tom_tat' — con so nay khong bao gio toi duoc asv_doi_soat")


# ══════════════════════════════════════════════════════════════════════════════
#  §4b  Task 15, Lo #2 — `giay_doan` (giay UOC LUONG) trong ban ghi luot doc
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_ghi_luot_doc_XUAT_giay_doan_khi_co_uoc_luong():
    """🔴 Task 15, Lo #2 — hanh vi THAT cua `ban_ghi_luot_doc`, khong phai AST.

    `nan_cho_vua.ban_ghi_luot_doc` la mot ham THUAN (khong CSDL, khong mang,
    khong may sinh tieng) nen goi THAT no la phep kiem manh nhat co the co —
    manh hon moi doc-ma, vi no chay dung dong `if giay_doan is not None:
    ra["giay_doan"] = ...` thay vi chi kham pha su co mat cua no.

    Truoc ban sua nay ham khong nhan tham so `giay_doan` — ban ghi mang
    `ma · vong · giay · khe · lech · can_nan · nen_viet_lai` nhung ⛔ KHONG co
    giay UOC LUONG, nen sai so cua bo uoc luong (Task 12) khong the do duoc:
    `asv_doi_soat` chi doc duoc `lech = (giay - khe) / khe`, tuc "doc ra vuot
    khe bao nhieu" — MOT dai luong KHAC voi "uoc luong sai bao nhieu so voi
    do that".
    """
    co = nan_cho_vua.ban_ghi_luot_doc("seg_01", vong=0, giay=5.0, khe=4.0,
                                      giay_doan=4.6)
    assert co.get("giay_doan") == pytest.approx(4.6)

    # ⭐ Vang mat = CHUA CO uoc luong, ⛔ khong phai "uoc luong bang 0" — dung
    #    khuon "vang mat ≠ bang 0" ma `gia.duong_nghe` da dung (xem docstring).
    khong = nan_cho_vua.ban_ghi_luot_doc("seg_01", vong=0, giay=5.0, khe=4.0)
    assert "giay_doan" not in khong


def test_giai_doan_giong_TRUYEN_giay_UOC_LUONG_vao_ban_ghi_luot_doc():
    """Chi sua `nan_cho_vua` la chua du: `giai_doan_giong` phai THUC SU truyen
    con so uoc luong cua `[B]` (`Khe.giay_can`, Task 12) vao loi goi
    `ban_ghi_luot_doc` o `[F]` — neu khong, tham so moi ton tai ma khong ai
    dung, va `giay_doan` van vang mat khoi moi ban ghi that.

    Chot bang AST: tim loi goi `nan_cho_vua.ban_ghi_luot_doc(...)` va doi hoi
    no mang keyword `giay_doan`. ⛔ Khong doi hoi ten bien cu the o phia goi —
    chi doi hoi CO mot keyword ten `giay_doan`, de khong khoa cung mot cach
    dat ten cu the.
    """
    import ast

    cay = ast.parse(inspect.getsource(giai_doan_giong.chay))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "ban_ghi_luot_doc"]
    assert goi, "khong tim thay loi goi ban_ghi_luot_doc trong chay()"
    assert any("giay_doan" in {kw.arg for kw in n.keywords} for n in goi), (
        "loi goi ban_ghi_luot_doc khong truyen keyword giay_doan — con so "
        "uoc luong cua Task 12 bi bo roi tai cho noi, du ham da nhan tham so")


# ══════════════════════════════════════════════════════════════════════════════
#  §5  `thoi_gian.ngan_sach_nan_s` — MOT nguon cho ngan sach BAC THANG NAN
# ══════════════════════════════════════════════════════════════════════════════

def test_ngan_sach_nan_khong_co_khoang_lang_thi_BANG_khe():
    from apps.auto_scan_video.thoi_gian import ngan_sach_nan_s
    assert ngan_sach_nan_s(3.0, 3.0) == 3.0


def test_ngan_sach_nan_muon_DUNG_ty_le_da_khai():
    from apps.auto_scan_video import thoi_gian as tg
    # khe 3,0 s · toi moc sau 4,0 s => khoang lang 1,0 s
    ra = tg.ngan_sach_nan_s(3.0, 4.0)
    assert abs(ra - (3.0 + 1.0 * tg.TY_LE_MUON_KHOANG_LANG)) < 1e-9


def test_ngan_sach_nan_KHONG_BAO_GIO_nho_hon_khe():
    """Du lieu hong (`moc_sau` < `ket`) khong duoc lam ngan sach teo lai."""
    from apps.auto_scan_video.thoi_gian import ngan_sach_nan_s
    assert ngan_sach_nan_s(3.0, 1.0) == 3.0


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Task 4 — VONG_TOI_DA 2 -> 1, tran tang toc thanh CANH BAO (chot 26/09)
# ══════════════════════════════════════════════════════════════════════════════

def test_vong_nan_toi_da_la_MOT():
    """VideoLingo (18,5k★) đã bỏ vòng rút gọn thứ hai; chú thích của chính ta
    cũng nói "vòng thứ hai thường không cần đến"."""
    from apps.auto_scan_video import nan_cho_vua
    assert nan_cho_vua.VONG_TOI_DA == 1


def test_he_so_toc_KHONG_bi_kep_ve_tran():
    """Chủ dự án chốt: vượt trần thoải mái. Trần còn là CẢNH BÁO, ⛔ không phải cổng.

    ⚠️ Task 16 (R4): đây là lưới PHỤ — kiểm cách VIẾT mã (không gọi cả `min`
    lẫn `max` trong CÙNG module), ⛔ không gọi hàm nên không bắt được ai viết
    lại phép kẹp bằng `sorted()`, `.clip()`, hay `if/else` mà vẫn né được cả
    hai tên gọi. Lưới CHÍNH là hành vi thật của hàm THUẦN `he_so_ap`, xem
    `test_he_so_ap_*` bên dưới.
    """
    import ast
    import inspect
    from apps.auto_scan_video import giai_doan_thoi_gian

    ma = inspect.getsource(giai_doan_thoi_gian)
    assert "he_so_toc_da_ap" in ma, "chua ghi lai he so da ap"
    cay = ast.parse(ma)
    ten_goi = {n.func.id for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "min" not in ten_goi or "max" not in ten_goi, (
        "van con phep kep he_so_co_gian ve [1/tran, tran]")


def test_he_so_ap_duoi_tran_ky_thuat_KHONG_bi_kep_ve_tran_chinh_sach():
    """h=1.10 < TRAN_TANG_TOC(1.15) va < tran ky thuat -> tra dung 1.10."""
    from apps.auto_scan_video.giai_doan_thoi_gian import he_so_ap

    assert he_so_ap(1.10, tran_ky_thuat=2.0) == pytest.approx(1.10)


def test_he_so_ap_vuot_tran_CHINH_SACH_van_di_qua_khong_bi_kep():
    """h=1.50 vuot TRAN_TANG_TOC(1.15, chinh sach san pham) nhung duoi tran ky
    thuat -> chu du an chot: van tra dung 1.50, KHONG bi kep ve 1.15."""
    from apps.auto_scan_video.giai_doan_thoi_gian import he_so_ap

    assert he_so_ap(1.50, tran_ky_thuat=2.0) == pytest.approx(1.50)


def test_he_so_ap_vuot_tran_KY_THUAT_bi_chan_dung_gia_tri_tran():
    """h=3.00 vuot ca tran ky thuat cua atempo (2.0) -> CHAN cung dung 2.0."""
    from apps.auto_scan_video.giai_doan_thoi_gian import he_so_ap

    assert he_so_ap(3.00, tran_ky_thuat=2.0) == pytest.approx(2.0)


# ══════════════════════════════════════════════════════════════════════════════
#  §7  Task 12 — dao thu tu: uoc luong TRUOC, nan theo LO, TTS MOT luot
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_nan_LO_mang_ngu_canh_truoc_sau():
    """Rút một câu mà ⛔ không biết câu kế nói gì thì dễ rút mất chủ ngữ mà câu
    sau đang trỏ tới."""
    from apps.auto_scan_video.nan_cho_vua import loi_nhac_nan_lo

    cac = [{"ma": "seg_0002", "chu": "Cau hai rat dai",
            "giay_doc": 4.8, "khe": 3.2,
            "truoc": "Cau mot", "sau": "Cau ba"}]
    tin = loi_nhac_nan_lo(cac)
    ca = " ".join(m["content"] for m in tin)
    assert "seg_0002" in ca and "3.2" in ca and "4.8" in ca
    assert "Cau mot" in ca and "Cau ba" in ca


def test_giai_doan_giong_KHONG_con_vong_while_quanh_TTS():
    """[F] chạy MỘT lượt: text đã chốt ở [E]."""
    import ast

    from apps.auto_scan_video import giai_doan_giong

    cay = ast.parse(inspect.getsource(giai_doan_giong))
    for v in [n for n in ast.walk(cay) if isinstance(n, ast.While)]:
        trong = {c.func.attr for c in ast.walk(v)
                 if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)}
        assert "doc_mot_doan" not in trong, (
            "TTS van nam trong mot vong `while` — bac thang chua duoc dao")
# ══════════════════════════════════════════════════════════════════════════════
#  §8  Task 19 — BA lo TIEN THAT cua vong loi `voice_synthesis` (soat R2, 26/09)
#
#  Vong nay vua duoc dung lai (Task 12: uoc luong TRUOC, nan theo LO, TTS MOT
#  luot) va CHUA chay that lan nao. Ba lo, ba phep kiem HANH VI:
#
#    CHAN 1  doan tran bi nan LAI o MOI lat cat        -> hoa don ×12
#    CHAN 2  `[E]` ⛔ khong nhuong duoc, va luot nan da tieu bi `rollback`
#    CHAN 3  chay lai giai doan lam MAT mot dong so cai (`ma_dispatch` trung)
#
#  ⭐ Ba bai duoi day **chay ca `giai_doan_giong.chay`** tren mot CSDL that voi
#     may sinh tieng gia + `ai.goi` gia + dong ho gia, nen chung do dung dai
#     luong phai do: **bao nhieu loi goi nan**, **cho nao nhuong**, **so cai co
#     bao nhieu dong**. ⛔ Khong bai nao doc chuoi trong ma — hai lo trong ngay
#     26/09 lot qua chinh vi phep kiem chi kham pha hinh dang.
# ══════════════════════════════════════════════════════════════════════════════
# ruff: noqa: F811 — fixture nhap tu `test_402` roi nhan lai lam tham so; ca bo
#   test ASV lam the, day khong phai dinh nghia trung.

from tests.test_402_asv_mach_doc_gia import db, kho_tam    # noqa: E402, F401

#: Khe 1 giay cho mot cau 10 am tiet: `Khe.giay_can` ~ 3,3 s ⇒ MOI doan tran.
CHU_DAI = "mot hai ba bon nam sau bay tam chin muoi."
#: Cau model tra ve: 1 am tiet ⇒ vua khe, va ⛔ khong bao gio tran lan hai.
CHU_NAN = "ngan."
#: Dong ho gia "ton" bao nhieu giay cho MOI loi goi nan. Ngan sach lat la
#: 0,85 × 5.400 = 4.590 s va du phong mot don vi la 1.980 s, nen lo thu ba
#: (troi 3.000 s) la lo dau tien phai nhuong.
GIAY_MOI_LO_NAN = 1500.0


class _DongHo:
    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self) -> float:
        return self.t


def _tai_lieu(so_doan: int) -> dict:
    """Ban long tieng: `so_doan` doan lien nhau, MOI doan tran khe cua no.

    ⛔ Cau ket bang dau cham nen `nan_thoi_luong.con_tiep` = False ⇒ `gop_khe`
       ⛔ khong gop: mot `ma` = mot khe = mot luot doc, de con so dem duoc.
    """
    return {
        "schema": 1, "ngon_ngu_goc": "zh", "ngon_ngu_dich": "vi",
        "ma_giong": "mau:gia",
        "muc": [{"ma": f"seg_{k + 1:04d}", "goc": f"yuan {k}", "chu": CHU_DAI,
                 "bat": float(k), "ket": float(k) + 1.0}
                for k in range(so_doan)],
    }


@pytest.fixture()
def vong_giong(db, kho_tam, monkeypatch, tmp_path):     # noqa: F811
    """Vong lõi `voice_synthesis` voi may sinh tieng gia + `ai.goi` gia.

    Tra ve `phong` — mot vat mang:
      `phong.dat(so_doan)`         dung run + ban long tieng
      `phong.chay_theo_luot()`     dong vai hang doi: moi vong = MOT job
      `phong.nan`                  `[(item_key, [ma...])]` cua tung loi goi nan
      `phong.tts`                  `[chu]` cua tung luot TTS
      `phong.moi_luot`             `[(so loi goi nan, so luot TTS)]` tung job
      `phong.dh`                   dong ho gia
    """
    from apps.auto_scan_video import (ai, features, giai_doan_giong as gd,
                                      giong_noi, lat_cat, pipeline)
    from tests.conftest import bao_dam_user

    dh = _DongHo()
    monkeypatch.setattr(lat_cat, "dong_ho", dh)

    class Phong:
        def __init__(self):
            self.dh = dh
            self.nan: list = []
            self.tts: list = []
            # ⭐ MOT nhat ky cho ca ba loai su kien — thu tu giua chung la thu
            #    duy nhat tra loi duoc "so cai co ben truoc khi mat luot khong".
            self.su_kien: list = []
            self.moi_luot: list = []
            self.tts_hong = False
            self.run = None
            self.tai_lieu: dict = {}

        def dat(self, so_doan: int, *, owner="uNan"):
            bao_dam_user(db, owner)
            self.run = features.tao_run(
                db, owner_id=owner, source_key="khong-dung",
                settings={"giong_id": "Minh Đức", "timing_mode": "fit_original"},
                uoc_luong_credit=0)
            db.commit()
            self.tai_lieu = _tai_lieu(so_doan)
            monkeypatch.setattr(gd, "_doc_ban_dich",
                                lambda db_, kho_, run_: self.tai_lieu)
            return self.run

        def giai_doan(self):
            return features.giai_doan_theo_ten(db, self.run.id,
                                               pipeline.VOICE_SYNTHESIS)

        def chay_mot_luot(self):
            """MOT job. Nem lai bat cu gi giai doan nem (ke ca `TiepNoi`)."""
            from platform_core.storage import get_storage
            from apps.auto_scan_video.tables import AsvRun

            n0, t0 = len(self.nan), len(self.tts)
            lat_cat.bat_dau_luot()
            try:
                db.expire_all()
                return gd.chay(db, get_storage(), run=db.get(AsvRun, self.run.id))
            finally:
                self.moi_luot.append((len(self.nan) - n0, len(self.tts) - t0))
                lat_cat.ket_thuc_luot()

        def chay_theo_luot(self, *, toi_da=90):
            """Dong vai hang doi: nhuong -> ghi con tro -> nop job ke tiep."""
            for _ in range(toi_da):
                try:
                    return self.chay_mot_luot()
                except lat_cat.TiepNoi as tn:
                    # ⛔ `thi_hanh` ROLLBACK truoc khi ghi con tro — day la cho
                    #    mot luot nan chua `commit` bien mat khoi so cai.
                    db.rollback()
                    lat_cat.ghi_tiep_noi(db, self.giai_doan(), tn)
                    db.commit()
            raise AssertionError(f"khong xong sau {toi_da} luot")

    phong = Phong()

    # ── may sinh tieng gia ────────────────────────────────────────────────
    monkeypatch.setattr(giong_noi, "san_sang", lambda: True)
    monkeypatch.setattr(giong_noi, "giai_giong",
                        lambda db_, **kw: (None, "bac"))

    def doc_mot_doan(chu, **_):
        if phong.tts_hong:
            raise giong_noi.GiongError("may sinh tieng gia: hong co y")
        phong.tts.append(chu)
        phong.su_kien.append("tts")
        return b"WAVGIA", {}

    monkeypatch.setattr(giong_noi, "doc_mot_doan", doc_mot_doan)
    # ⭐ 0,5 s < khe 1,0 s ⇒ moi doan la `VUA`; phep kiem nay do SO LOI GOI, ⛔
    #    khong do phan quyet nan.
    monkeypatch.setattr(giong_noi, "kiem_tep_tieng", lambda duong: 0.5)

    # ── `ai.goi` gia: `goi_tinh_tien` (cua tinh tien THAT) van chay ────────
    def goi(db_, thao_tac, messages, **kw):
        bang = json.loads(messages[-1]["content"])
        mas = sorted(bang)
        phong.nan.append(mas)
        phong.su_kien.append("nan")
        dh.t += GIAY_MOI_LO_NAN
        return {"noi_dung": json.dumps({m: CHU_NAN for m in mas}),
                "provider": "gia", "model": "gia", "su_dung": None,
                "finish_reason": "stop", "suy_nghi": ""}

    monkeypatch.setattr(ai, "goi", goi)
    return phong


def _dong_nan(db, run) -> list:
    """Cac dong SO CAI cua luot nan (⛔ khong phai cua doan tieng)."""
    from apps.auto_scan_video import pipeline, su_dung

    return [d for d in su_dung.cac_dong(db, run, stage=pipeline.VOICE_SYNTHESIS)
            if str(d.item_key).startswith("nan_lo:")]


# ── CHAN 1 ───────────────────────────────────────────────────────────────────

def test_CHAN1_doan_da_nan_KHONG_bi_nan_lai_o_lat_cat_sau(db, kho_tam,
                                                          vong_giong):  # noqa: F811
    """🔴 CHAN 1 — hoa don ×12.

    `[A]` chi danh dau `da_tra_tien` cho doan DA DOC (`i0 < lc.vi_tri`), nen
    `doan_tran` cua MOI lat cat = moi doan tran CHUA doc, va `[E]` nan LAI ca
    danh sach ay — moi lan mot dong so cai THAT (`item_key` mang `luot`).

    Do cua nguoi soat: video 120 phut ~1.200 doan tran ⇒ ~700 loi goi thay vi 60.
    Bai nay dung 60 doan / 3 lo va khang dinh **moi `ma` chi duoc xin DUNG MOT
    lan tren ca lan chay**, bat ke bao nhieu lat cat.
    """
    phong = vong_giong
    phong.dat(60)
    ra = phong.chay_theo_luot()

    assert len(phong.tts) == 60, "phai doc du 60 doan"
    assert len(phong.moi_luot) >= 2, (
        "phep kiem nay chi co nghia khi giai doan CO nhuong: %s" % phong.moi_luot)

    dem: dict = {}
    for mas in phong.nan:
        for m in mas:
            dem[m] = dem.get(m, 0) + 1
    thua = {m: n for m, n in dem.items() if n > 1}
    assert not thua, (
        "da xin nan LAI %d/%d doan (vd %s) — cau da nan khong duoc luu ben, nen "
        "moi lat cat nan lai ca danh sach"
        % (len(thua), len(dem), sorted(thua.items())[:3]))
    assert len(phong.nan) == 3, (
        "60 doan tran = 3 lo (20/lo) ⇒ DUNG 3 loi goi; da goi %d"
        % len(phong.nan))
    # ⭐ Va ban ra dung: moi doan duoc doc bang CAU DA NAN, ⛔ khong phai cau goc.
    assert set(phong.tts) == {CHU_NAN}
    assert ra["tom_tat"]["so_doan_moi_sinh"] == 60


def test_CHAN1_luot_nan_duoc_COMMIT_truoc_luot_TTS_dau_tien(db, kho_tam,
                                                            vong_giong):  # noqa: F811
    """🔴 CHAN 2, nua DO BEN: `db.commit()` dau tien von nam SAU ca `[E]`.

    `ai.goi_tinh_tien` ghi so cai trong giao dich cua NGUOI GOI (`su_dung.ghi`
    chi `flush`, ⛔ khong mo giao dich rieng). Nen bat cu duong ra nao TRUOC doan
    tieng dau tien — `lat_cat.TiepNoi`, hay mot loi cua may sinh tieng — di qua
    `thi_hanh` -> `db.rollback()` va **ca luot nan da tieu bien mat khoi so cai**:
    tien mat, so trong.

    ⚠️ **Vi sao bai nay do THU TU SU KIEN chu ⛔ khong do `db.rollback()`.** Bo
       test chay tren SQLite, va `su_dung.ghi`/`mo_don_vi` cam dong `INSERT`
       trong `db.begin_nested()` (SAVEPOINT). Voi driver `pysqlite`, mot SAVEPOINT
       mo khi chua co giao dich ngoai chay o che do autocommit — nen dong so cai
       SONG SOT qua `db.rollback()` **tren SQLite**, va mot bai do `rollback` se
       XANH ngay ca khi loi con nguyen (da thu: no xanh tren ma CHUA sua). Do la
       `pysqlite` cua may thu, ⛔ khong phai PostgreSQL cua production.
       ⇒ Do dai luong ⛔ KHONG phu thuoc engine: **co mot `commit` nam giua luot
       nan va luot TTS dau tien hay khong**. Mot `commit` sau lo la du de dong so
       cai ben, vi `su_dung.ghi` da `flush` no vao chinh phien nay.
    """
    phong = vong_giong
    run = phong.dat(5)

    goc = db.commit

    def commit():
        phong.su_kien.append("commit")
        return goc()

    db.commit = commit
    try:
        phong.chay_theo_luot()
    finally:
        db.commit = goc

    assert len(phong.nan) == 1, "5 doan tran = 1 lo, da goi %d" % len(phong.nan)
    assert phong.su_kien[0] == "nan", phong.su_kien[:4]
    i_tts = phong.su_kien.index("tts")
    assert "commit" in phong.su_kien[:i_tts], (
        "⛔ KHONG co `commit` nao giua luot nan va luot TTS dau tien (%s) — mot "
        "`TiepNoi` hay mot loi cua may sinh tieng o day lam ca luot nan DA TRA "
        "TIEN bien mat khoi so cai" % phong.su_kien[:i_tts + 1])
    # ⭐ Va so cai THAT co dong cua luot nan ay (⛔ khong chi "da commit gi do").
    assert len(_dong_nan(db, run)) == 1


# ── CHAN 2 ───────────────────────────────────────────────────────────────────

def test_CHAN2_khoi_nan_NHUONG_duoc_giua_cac_lo(db, kho_tam,
                                                vong_giong):  # noqa: F811
    """🔴 CHAN 2, nua NHUONG: ⛔ khong mot `lc.kiem()` nao trong `[E]`.

    Voi `LAN_XIN_NAN_LO = 3`, 200 lo xau nhat la ~10.600 s tren mot ngan sach
    lat 4.590 s ⇒ `job_runner._het_gio` ban `os._exit(3)` va `retry=False`: lan
    chay hong HAN. Va `nen_nhuong` doi `da_lam >= 1`, nen `[E]` ⛔ khong nhuong
    duoc ngay ca khi co `kiem` — mot lo nan phai DEM la mot don vi.

    ⭐ Phep do: luot DAU phai ket thuc voi **loi goi nan > 0 va luot TTS = 0**.
       Do la chu ky chi co the xay ra khi `[E]` nhuong giua cac lo: neu `[E]`
       chay het roi moi toi `[F]`, luot dau luon doc it nhat mot doan (`kiem`
       dau tien cua `[F]` co `da_lam == 0` nen ⛔ khong the nhuong).
    """
    phong = vong_giong
    phong.dat(60)
    phong.chay_theo_luot()

    nan_dau, tts_dau = phong.moi_luot[0]
    assert nan_dau > 0 and tts_dau == 0, (
        "luot dau: %d loi goi nan / %d luot TTS — `[E]` khong nhuong giua cac "
        "lo, no chay het roi moi de `[F]` nhuong (moi_luot=%s)"
        % (nan_dau, tts_dau, phong.moi_luot))
    # ⛔ Va nhuong xong thi con tro ⛔ KHONG duoc nhich: chua doan nao duoc doc.
    assert nan_dau == 2, (
        "1.500 s/lo tren ngan sach 4.590 s - du phong 1.980 s ⇒ DUNG hai lo "
        "vua luot dau; da lam %d" % nan_dau)


# ── CHAN 3 ───────────────────────────────────────────────────────────────────

def test_CHAN3_hai_ATTEMPT_cho_HAI_ma_dispatch_khac_nhau(db, kho_tam,
                                                         vong_giong):  # noqa: F811
    """🔴 CHAN 3 — chay lai giai doan lam MAT mot dong so cai.

    `item_key = f"nan_lo:{luot}:{so_lo}:{lan}"` va `UNIQUE(run_id, ma_dispatch)`
    ⛔ KHONG gom `attempt`. `features._dat_lai_giai_doan` xoa `outputs` ⇒ con tro
    lat cat mat ⇒ `lc.luot` ve 0, nen lan chay sau sinh **dung `ma_dispatch`
    cu**: `su_dung.ghi` nem `DaGhiRoi`, `goi_tinh_tien` chi `log.info`, va cac
    loi goi may B THAT cua lan chay do bien mat khoi so cai.

    ⚠️ Ta xoa ban ghi `chu_da_nan` giua hai lan chay — do la chinh canh ma rang
       buoc nay phai song sot: mot lo da goi may B ma `commit` chua kip landing
       (bi giet giua `goi_tinh_tien` va `db.commit()`) se duoc XIN LAI o lan chay
       sau, va lan xin lai ay la tien THAT.
    """
    from apps.auto_scan_video import (features, giai_doan_giong as gd,
                                      giong_noi, pipeline)

    phong = vong_giong
    run = phong.dat(5)
    phong.tts_hong = True

    def _mot_lan(lan_thu: int) -> None:
        gdoan = phong.giai_doan()
        gdoan.attempt = int(lan_thu)
        db.commit()
        with pytest.raises(giong_noi.GiongError):
            phong.chay_mot_luot()
        db.rollback()
        # Mo phong "bi giet truoc khi `commit` cua lo landing": ban ghi cau da
        # nan khong con, nen lan chay sau PHAI xin lai — va phai ghi so duoc.
        # ⛔ `getattr` co mac dinh: bai nay phai do duoc CA tren ban ma chua co
        #    `KHOA_CHU_NAN` — neu khong no do vi `AttributeError` (mot loi HINH
        #    DANG) chu khong vi `ma_dispatch` trung (loi THAT dang do).
        khoa = getattr(gd, "KHOA_CHU_NAN", "chu_da_nan")
        for it in features.cac_don_vi(db, run.id, pipeline.VOICE_SYNTHESIS):
            if khoa in (it.outputs or {}):
                it.outputs = {k: v for k, v in (it.outputs or {}).items()
                              if k != khoa}
        db.commit()

    _mot_lan(1)
    _mot_lan(2)

    assert len(phong.nan) == 2, "phai co DUNG hai luot xin (mot moi attempt)"
    dong = _dong_nan(db, run)
    ma = sorted(str(d.ma_dispatch) for d in dong)
    assert len(dong) == 2 and len(set(ma)) == 2, (
        "hai `attempt` khac nhau cho ra %d dong so cai (%s) — `ma_dispatch` "
        "trung, nen mot luot goi may B DA TRA TIEN bien mat khoi so cai" % (
            len(dong), ma))
    assert any(":a1:" in x for x in ma) and any(":a2:" in x for x in ma), ma
