"""R-05 — VLM doc canh HONG: nguyen nhan, va san pham phai lam gi khi no hong.

Luot nghiem thu nen v3 (23/09): 4/12 luot `doc_canh` hong ⇒ `so_cat = 0/6` ⇒
preset `smart_localize` giao mot ban **khong cat gi**, va giai doan bao
`succeeded`. Goi lai 18 canh cua chinh phim do bang model that: **8/18 hong**,
va moi luot hong deu la mot phan hoi HTTP thanh cong co hinh dang sai —
5 lan `"giữ"` (co dau), 2 lan tra ve mot MANG, 1 lan boc `{"objects": [...]}`.
So lieu day du: `docs/auto_scan_video_final/L_FIX_TOC_DO.md`.

  §1 `chuan_de_xuat`     — `"giữ"` la CUNG mot gia tri voi `giu`, khong phai rac
  §2 loi nhac            — mot KHUNG JSON, va `de_xuat` la MA chep y nguyen
  §3 thu lai             — phan hoi sai hinh dang duoc hoi lai MOT lan
  §4 do phu bang chung   — `smart_localize` khong duoc am tham thanh "giu het"

⛔ Khong phep kiem nao o day goi model that.
"""
from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ai, canh as canh_mod,  # noqa: E402
                                  giai_doan_ban_bien_tap as gdbbt,
                                  hieu_canh as hc, hop_dong_v4)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  `de_xuat` co dau van la `de_xuat`
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tho,ra", [
    # 🔴 Nam luot THAT cua phim nghiem thu tra ve dung chuoi nay.
    ("giữ", "giu"), ("GIỮ", "giu"), (" Giữ ", "giu"),
    ("bỏ", "bo"), ("Không chắc", "khong_chac"), ("khong chac", "khong_chac"),
    ("khong-chac", "khong_chac"),
    ("giu", "giu"), ("bo", "bo"), ("khong_chac", "khong_chac"),
])
def test_de_xuat_co_dau_DUOC_nhan_dung_gia_tri(tho, ra):
    assert hc.chuan_de_xuat(tho) == ra


@pytest.mark.parametrize("tho", ["bu", "", None, "maybe", "đỏ", "giu_lai", 1])
def test_gia_tri_LA_van_bi_TU_CHOI(tho):
    """⛔ Chuan hoa nhan dien, khong doan. `"bu"` (1/18 luot that) van la loi."""
    assert hc.chuan_de_xuat(tho) == ""


def test_doc_hieu_canh_NHAN_phan_hoi_co_dau_va_TU_CHOI_gia_tri_la():
    goc = {"loai": "a", "chu_the": [], "hanh_dong": "", "cam_xuc": "",
           "quan_trong": 0.8, "de_xuat": "giữ", "do_tin": 0.9,
           "ly_do": "", "canh_bao": []}
    import json
    h = hc.doc_hieu_canh({"noi_dung": json.dumps(goc, ensure_ascii=False)}, "c1")
    assert h.de_xuat == hc.GIU

    goc["de_xuat"] = "bu"
    with pytest.raises(hc.HieuCanhError):
        hc.doc_hieu_canh({"noi_dung": json.dumps(goc, ensure_ascii=False)}, "c1")


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Loi nhac: mot KHUNG, khong phai mot cau ke ten khoa
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_canh_DUA_KHUNG_JSON_va_cam_MANG():
    van = hc.loi_nhac_canh("canh_0001", "xin chao", 2, {"a": 1})[0]["content"]
    assert '"de_xuat"' in van and '"do_tin"' in van and '"quan_trong"' in van
    assert "KHONG phai mang" in van
    for ma in hc.DE_XUAT:
        assert f'"{ma}"' in van


def test_loi_nhac_canh_NOI_RO_de_xuat_la_MA_khong_phai_chu_tieng_Viet():
    van = hc.loi_nhac_canh("canh_0001", "", 0, {})[0]["content"]
    assert "khong them dau tieng Viet" in van


def test_doi_loi_nhac_lam_DOI_van_tay_canh():
    """⛔ Giu van tay = lan chay sau dung lai ket qua sinh boi loi nhac CU."""
    assert hc.PHIEN_BAN_HIEU_CANH >= 4
    a = hc.van_tay_canh("c1", "x", 2, 0.65)
    truoc = hc.PHIEN_BAN_HIEU_CANH
    try:
        hc.PHIEN_BAN_HIEU_CANH = truoc + 1
        assert hc.van_tay_canh("c1", "x", 2, 0.65) != a
    finally:
        hc.PHIEN_BAN_HIEU_CANH = truoc


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Thu lai MOT lan, va chi voi loi HINH DANG
# ══════════════════════════════════════════════════════════════════════════════

def test_CHI_loi_HINH_DANG_duoc_hoi_lai():
    """🔴 **26/09/2026 — KY VONG DOI CHIEU, y dinh GIU NGUYEN.**

    Y dinh cu: *mot phan hoi rac cua VLM ⛔ khong duoc am tham thanh "giu het",
    va mot luot DA tra tien ⛔ khong duoc bi hoi lai vo ich.* Ca lop loi do sinh
    ra tu **viec goi model**.

    ⭐ Tu 26/09 `edit_plan` ⛔ KHONG goi model nao (B1 §9b): ba tieu chi cua no
       do bang so hoc + `blackdetect` + `freezedetect`. ⇒ Cach manh nhat de giu
       y dinh cu la chot rang **⛔ khong con mot loi goi nao** — het lop loi, het
       nhu cau hoi lai, va het hoa don.

    ⛔ Day KHONG phai mot phep kiem ve su vang mat cua mot chu: `goi_tinh_tien`
       la cua **duy nhat** ghi so cai cua kho (`ai.py`), nen vang mat cua no
       tren ca module la mot menh de ve **tien**, khong phai ve cach go.
    """
    import ast

    # ⭐ Doc AST, ⛔ khong quet chuoi con: chinh khoi ghi chu cua module GIAI
    #    THICH rang `ai.DOC_CANH` da thoi viec, nen mot phep quet van ban se do
    #    CACH GO thay vi do tinh chat (bai hoc `banh-coc-do-cach-go`).
    ten_dung: set[str] = set()
    for nut in ast.walk(ast.parse(inspect.getsource(gdbbt))):
        if isinstance(nut, ast.Attribute):
            ten_dung.add(nut.attr)
        elif isinstance(nut, ast.Name):
            ten_dung.add(nut.id)
    for cam in ("goi_tinh_tien", "DOC_CANH", "ThreadPoolExecutor", "doc_hieu_canh"):
        assert cam not in ten_dung, (
            f"`{cam}` con duoc GOI trong edit_plan — giai doan nay ⛔ khong con "
            f"goi model")
    # Va bo do tat dinh phai CO THAT, khong phai mot cho trong.
    assert callable(gdbbt._do_cac_canh)


def test_luot_thu_lai_DUNG_ma_dispatch_KHAC():
    """🔴 **26/09 — KY VONG DOI CHIEU.** Y dinh cu: *hai luot goi THAT ⛔ khong
    duoc trung `ma_dispatch`, vi `UNIQUE(run_id, ma_dispatch)` se nuot but toan
    cua luot sau — mot luot DA tra tien bien mat khoi so cai.*

    ⭐ Tu 26/09 giai doan nay ⛔ khong mo mot don vi tinh tien nao, nen cach giu
       y dinh cu la chot **⛔ khong co dong so cai nao** de ma trung: no ⛔ khong
       dung `su_dung` va ⛔ khong dung `ai`.
    """
    import ast

    ma = inspect.getsource(gdbbt)
    for cam in ("su_dung", "mo_don_vi", "ma_dispatch"):
        assert cam not in ma, (
            f"`{cam}` con trong edit_plan — no ⛔ khong con ghi so cai nao")
    # ⭐ Chot bang AST, ⛔ khong bang chuoi con: `"ai."` khop ca `hai.`/`loai.`
    #    trong chu thich tieng Viet — mot phep kiem do CACH GO chu khong do tinh
    #    chat (bai hoc `banh-coc-do-cach-go`).
    nhap: set[str] = set()
    for nut in ast.walk(ast.parse(ma)):
        if isinstance(nut, ast.ImportFrom):
            nhap |= {a.asname or a.name for a in nut.names}
        elif isinstance(nut, ast.Import):
            nhap |= {(a.asname or a.name).split(".")[0] for a in nut.names}
    assert "ai" not in nhap, f"edit_plan con nhap `ai`: {sorted(nhap)}"


def test_nhat_ky_GHI_THONG_DIEP_chu_khong_chi_ten_lop():
    """🔴 Nhat ky luot nen v3 chi co `(LuocDoSai)`, nen phai goi lai 18 luot
    that moi biet vi sao. Mot dong log day du thi khong.

    ⭐ Luat nay ⛔ khong doi khi bo do doi: cho duy nhat `_do_cac_canh` **nuot**
       mot ngoai le la nhanh `qc.QcError`, va no phai ghi THONG DIEP.
    """
    ma = inspect.getsource(gdbbt._do_cac_canh)
    assert "str(exc)[:200]" in ma


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Do phu bang chung — `smart_localize` khong duoc am tham thanh "giu het"
# ══════════════════════════════════════════════════════════════════════════════

def _chi_muc(n: int):
    return canh_mod.ChiMucCanh(
        tuple(canh_mod.Canh(f"canh_{i + 1:04d}", float(i), float(i + 1))
              for i in range(n)), float(n))


class _Hieu:
    def __init__(self, ma):
        self.ma_canh = ma


def test_SMART_LOCALIZE_tu_choi_khi_con_canh_KHONG_co_bang_chung():
    ci = _chi_muc(6)
    hieu = tuple(_Hieu(c.ma) for c in ci.canh[:4])
    hong = [{"ma_canh": "canh_0005", "loai": "LuocDoSai", "ly_do": "x"},
            {"ma_canh": "canh_0006", "loai": "HieuCanhError", "ly_do": "y"}]
    with pytest.raises(gdbbt.ThieuBangChungCanh) as e:
        gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci, hieu, hong)
    # Thong diep phai NOI RA bao nhieu canh, de khach biet minh dang doc cai gi.
    assert "2" in str(e.value) and "6" in str(e.value)


def test_SMART_LOCALIZE_DI_TIEP_khi_doc_du_moi_canh():
    """Doi chung cua bai tren: neu cua chan MOI luot thi bai tren van xanh."""
    ci = _chi_muc(6)
    gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci,
                       tuple(_Hieu(c.ma) for c in ci.canh), [])


def test_GIU_HINH_KHONG_bi_cua_nay_chan():
    """⛔ Preset giu hinh khong doc canh nao ca — do phu 0 o do la dung hop dong."""
    ci = _chi_muc(6)
    gdbbt._chot_do_phu(hop_dong_v4.PRESET_GIU_HINH, ci, (), [])


def test_loi_thieu_bang_chung_KHONG_duoc_nen_tang_tu_dong_thu_lai():
    """⚠️ Lan hoi lai da xay ra TRONG giai doan (`SO_LAN_DOC_CANH`). Mot vong
    thu lai thu hai o tang job la cung mot phep goi tren cung mot khung hinh,
    cong them mot hoa don. Nguoi quyet dinh chay lai la KHACH."""
    from apps.auto_scan_video import loi as _loi
    from apps.auto_scan_video.giai_doan_media import ThieuNguon
    assert issubclass(gdbbt.ThieuBangChungCanh, ThieuNguon)
    assert _loi.phan_loai(gdbbt.ThieuBangChungCanh("x")) == \
        _loi.THIEU_THUONG_NGUON


def test_tom_tat_giai_doan_MANG_so_canh_hong_va_do_phu():
    """Bang chung cua luot chay phai tra loi duoc *"co lo hong nao khong"*."""
    ma = inspect.getsource(gdbbt.chay)
    for khoa in ('"so_canh_hong"', '"canh_hong"', '"do_phu_bang_chung"'):
        assert khoa in ma


def test_nguong_do_phu_la_BAT_BIEN_khong_phai_tham_so_hieu_chinh():
    assert gdbbt.PHU_BANG_CHUNG_TOI_THIEU == 1.0


def test_DOC_CANH_van_doi_dung_hai_truong_quyet_dinh():
    """Bo do doi `de_xuat`/`do_tin` — hai truong `_quyet_dinh_mot_canh` that su doc.

    ⚠️ Tu 26/09 `edit_plan` ⛔ khong con goi `DOC_CANH`; ban khai nay con song vi
       `tools/do_llm_cong_asv.py` (bo do cong LLM) van do no. Hai truong do van
       la hop dong cua `_quyet_dinh_mot_canh`, va bo do TAT DINH cung tra dung
       hai truong do (`BangChungCanh`).
    """
    assert ai.DOC_CANH.truong_bat_buoc == ("de_xuat", "do_tin")
    truong = {f.name for f in dataclasses.fields(gdbbt.BangChungCanh)}
    assert {"de_xuat", "do_tin"} <= truong


# ══════════════════════════════════════════════════════════════════════════════
#  §5  26/09/2026 — `edit_plan` xuong GD2, va bo do TAT DINH thay VLM (B1 §9)
# ══════════════════════════════════════════════════════════════════════════════

def test_content_process_coi_THIEU_ban_bien_tap_la_GIU_TAT_CA():
    """🔴 Truoc 26/09 no NEM `ThieuBanBienTap`. Sau khi `edit_plan` xuong GD2 thi
    "chua co ban bien tap" la trang thai HOP LE = giu tat ca, ⛔ khong phai loi.

    ⛔ Neu buoc nay con nem thi **MOI** luot chay chet o `content_process` — dung
       lop loi B1 §7 da liet ke ("Bo `edit_plan` lam `content_process` nem").
    """
    from apps.auto_scan_video import giai_doan_noi_dung

    ma = inspect.getsource(giai_doan_noi_dung._doc_ban_bien_tap)
    assert "ThieuBanBienTap" not in ma, (
        "van nem khi thieu ban bien tap — se lam chet MOI luot chay sau khi "
        "edit_plan xuong GD2")


def test_edit_plan_chay_SAU_render_va_KHONG_giu_llm_remote():
    """⛔ `tai_nguyen` rong: no ⛔ khong con goi model nao.

    🔴 Truoc do no khai `llm_remote` **TINH** — voi preset giu hinh no ⛔ khong
       goi gi ma VAN giu suat LLM duy nhat cua ca may. Do 26/09: hai luot cung
       preset, `edit_plan` mat 2,8 s va 205,7 s; 203 giay chenh la XEP HANG.
    """
    from apps.auto_scan_video import pipeline as p

    theo_ten = {dataclasses.asdict(g)["ten"]: dataclasses.asdict(g)
                for g in p.CHUOI}
    assert theo_ten["edit_plan"]["sau"] == ("render",)
    assert theo_ten["content_process"]["sau"] == ("transcribe",)
    assert not theo_ten["edit_plan"]["tai_nguyen"], (
        "edit_plan van giu suat llm_remote — no KHONG con goi model nao")


def test_image_finish_phai_xep_SAU_edit_plan_chu_khong_chi_sau_render():
    """🔴 `ke_tiep` tra ve DANH SACH moi giai doan du phu thuoc.

    Neu `image_finish` con khai `sau=(RENDER,)` thi no nop duoc **cung luc** voi
    `edit_plan`, va mot luot chay truoc se doc `khoa_ep` rong, cat 0 khung, roi
    bao `succeeded`. ⇒ Ca phep dai giai doan xuong GD2 mat tac dung IM LANG.
    """
    from apps.auto_scan_video import pipeline as p

    assert p.THEO_TEN[p.IMAGE_FINISH].sau == (p.EDIT_PLAN,)
    # Doi chung: sau `render` xong, `edit_plan` la viec DUY NHAT san sang.
    xong = {g.ten for g in p.CHUOI[:p.TEN_GIAI_DOAN.index(p.RENDER) + 1]}
    assert [g.ten for g in p.ke_tiep(xong)] == [p.EDIT_PLAN]


# ── Bo do tat dinh ────────────────────────────────────────────────────────────

def _ban_ghi_thoai(*khoang):
    return {"doan": [{"ma": f"d{i}", "bat": b, "ket": k, "chu": "xin chao"}
                     for i, (b, k) in enumerate(khoang)]}


def _do_gia(monkeypatch, *, den=(), dong=()):
    monkeypatch.setattr(gdbbt.qc, "do_hinh", lambda *a, **k: {
        "khoang_den": [list(x) for x in den],
        "khoang_dong": [list(x) for x in dong]})


def test_canh_CO_THOAI_khong_bao_gio_la_ung_vien_cat(monkeypatch):
    """⭐ Tieu chi chu du an: *"CHI cat vung KHONG co loi thoai"*. Mot canh giao
    doan thoai phai ra `giu` du no den ca canh."""
    ci = _chi_muc(2)
    _do_gia(monkeypatch, den=[(0.0, 2.0)])
    hieu, hong = gdbbt._do_cac_canh("phim.mp4", ci, _ban_ghi_thoai((0.2, 0.8)))
    assert hong == []
    theo_ma = {h.ma_canh: h for h in hieu}
    assert theo_ma["canh_0001"].de_xuat == "giu", theo_ma["canh_0001"].ly_do
    assert theo_ma["canh_0002"].de_xuat == "bo", theo_ma["canh_0002"].ly_do


def test_khoang_den_va_dung_hinh_CHONG_LAN_khong_bi_cong_HAI_lan(monkeypatch):
    """🔴 Mot khoang vua den vua dung hinh duoc ffmpeg bao ra o CA HAI bo loc.

    Cong hai lan cho `ti_le > 1`, tuc mot canh **sach** cung vuot nguong. Day la
    lop "dem sai mau so" ma kho da ghi so ba lan trong mot ngay.
    """
    ci = _chi_muc(1)
    _do_gia(monkeypatch, den=[(0.0, 0.3)], dong=[(0.0, 0.3)])
    (h,), hong = gdbbt._do_cac_canh("phim.mp4", ci, _ban_ghi_thoai((5.0, 6.0)))
    assert hong == []
    # 0,3 / 1,0 — ⛔ KHONG phai 0,6.
    assert h.do_tin == pytest.approx(0.3)
    assert h.de_xuat == "giu"
    # Ca hai phep do phai duoc KHAI RA, khong gop thanh mot con so vo danh.
    assert set(h.canh_bao) == {"toi_den", "dung_hinh"}


def test_nguong_ti_le_hinh_kem_TACH_khoi_nguong_do_tin_VLM(monkeypatch):
    """Task 18 (R5): `ti_le` (do TAT DINH bang ffmpeg — khung den/dung hinh) va
    `do_tin` cua VLM (chu quan) la HAI dai luong khac ban chat. Truoc Task 18
    ca hai bi ep chung mot hang so `ban_bien_tap.NGUONG_BO` ma ⛔ khong ai do
    lai cho dai luong moi — nay chung la HAI hang so o HAI module.

    (a) hai hang so rieng biet (gia tri KHOI DIEM van la 0,65 — ke thua, Task 18
        ⛔ khong duoc doi hanh vi cat).
    (b) duong quyet dinh (`_do_cac_canh`) doc `NGUONG_TI_LE_HINH_KEM` cua
        CHINH module nay, ⛔ khong con doc `ban_bien_tap.NGUONG_BO`: doi
        `NGUONG_TI_LE_HINH_KEM` PHAI doi ket qua; doi `ban_bien_tap.NGUONG_BO`
        (hang so cua VLM) thi ⛔ khong duoc anh huong gi den duong bang chung
        tat dinh nay.
    (c) ca bien: `ti_le` DUNG BANG nguong ⇒ `de_xuat = "bo"` (so sanh `>=`,
        chot lai vi bien la cho hay troi).
    """
    from apps.auto_scan_video import ban_bien_tap as bt

    ci = _chi_muc(1)

    # (a) — hai ten hang so khac nhau o hai module, cung gia tri khoi diem.
    assert gdbbt.NGUONG_TI_LE_HINH_KEM == bt.NGUONG_BO == 0.65
    nguon = inspect.getsource(gdbbt._do_cac_canh)
    # Xet DUNG dong so sanh (⛔ khong xet ca comment — comment duoc phep NHAC
    # den ten hang so cu de giai thich vi sao no bi bo).
    dong_so_sanh = next(d for d in nguon.splitlines() if "de_xuat = hc.BO" in d)
    assert "NGUONG_TI_LE_HINH_KEM" in dong_so_sanh
    assert "NGUONG_BO" not in dong_so_sanh, (
        "duong quyet dinh cua phep do tat dinh van doc hang so nghi cho VLM")

    # (c) — ca bien: dung bang nguong la "bo" (>=), duoi mot chut la "giu".
    for ti_le, mong in ((0.65, "bo"), (0.65 - 0.01, "giu")):
        _do_gia(monkeypatch, den=[(0.0, ti_le)])
        (h,), _ = gdbbt._do_cac_canh("phim.mp4", ci, _ban_ghi_thoai((5.0, 6.0)))
        assert h.de_xuat == mong, (ti_le, h.ly_do)

    # (b) — doi NGUONG_TI_LE_HINH_KEM (hang so cua module NAY) PHAI doi ket qua.
    monkeypatch.setattr(gdbbt, "NGUONG_TI_LE_HINH_KEM", 0.9)
    _do_gia(monkeypatch, den=[(0.0, 0.65)])  # ti_le = 0,65 — duoi 0,9
    (h,), _ = gdbbt._do_cac_canh("phim.mp4", ci, _ban_ghi_thoai((5.0, 6.0)))
    assert h.de_xuat == "giu", (
        "NGUONG_TI_LE_HINH_KEM da doi ma ket qua khong doi — "
        "duong quyet dinh van dang doc mot hang so khac")
    monkeypatch.setattr(gdbbt, "NGUONG_TI_LE_HINH_KEM", 0.65)  # tra ve khoi diem

    # ...con doi `ban_bien_tap.NGUONG_BO` (hang so cua VLM) thi ⛔ khong duoc
    # anh huong gi den duong bang chung tat dinh nay.
    monkeypatch.setattr(bt, "NGUONG_BO", 0.01)
    _do_gia(monkeypatch, den=[(0.0, 0.65 - 0.01)])  # van "giu" o nguong 0,65
    (h,), _ = gdbbt._do_cac_canh("phim.mp4", ci, _ban_ghi_thoai((5.0, 6.0)))
    assert h.de_xuat == "giu", (
        "doi ban_bien_tap.NGUONG_BO da lam doi ket qua cua phep do tat dinh — "
        "hai duong van con dung chung mot hang so")


def test_phep_do_la_TAT_DINH_cung_dau_vao_cung_ket_qua(monkeypatch):
    """⭐ Cat la thao tac ⛔ KHONG DAO DUOC tren ban giao khach: cung mot video
    phai cat cung mot cho o moi luot chay."""
    ci = _chi_muc(4)
    _do_gia(monkeypatch, den=[(1.0, 2.0)], dong=[(2.5, 3.4)])
    bg = _ban_ghi_thoai((0.1, 0.5))
    a = gdbbt._do_cac_canh("phim.mp4", ci, bg)
    b = gdbbt._do_cac_canh("phim.mp4", ci, bg)
    assert a == b
    assert [(h.ma_canh, h.de_xuat, round(h.do_tin, 6)) for h in a[0]] == [
        ("canh_0001", "giu", 1.0),      # co thoai
        ("canh_0002", "bo", 1.0),       # [1,2) den tron ven
        ("canh_0003", "giu", 0.5),      # [2,3): 0,5 s dung hinh — duoi nguong
        ("canh_0004", "giu", 0.4),      # [3,4): 0,4 s dung hinh — duoi nguong
    ]


def test_THIEU_ban_chep_loi_la_THIEU_BANG_CHUNG_chu_khong_phai_KHONG_CO_THOAI():
    """🔴 `_co_thoai` tra `False` cho MOI canh khi ban ghi rong ⇒ ca video bien
    thanh "khong loi thoai" va thanh ung vien cat khap noi.

    ⇒ Phai la mot **bat bien o bien**: khong ban chep loi = khong bang chung,
      va `_chot_do_phu` tu choi preset cat.
    """
    ci = _chi_muc(3)
    hieu, hong = gdbbt._do_cac_canh("phim.mp4", ci, {})
    assert hieu == ()
    assert [h["loai"] for h in hong] == ["thieu_ban_chep_loi"] * 3
    with pytest.raises(gdbbt.ThieuBangChungCanh):
        gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci, hieu, hong)


def test_bo_do_hinh_HONG_thi_khong_canh_nao_co_bang_chung(monkeypatch):
    """⛔ `_do_cac_canh` KHONG nem: mot bo do hong = "khong co bang chung", va
    `_chot_do_phu` moi la cho phan xu (mot cho, khong hai)."""
    ci = _chi_muc(2)

    def no(*a, **k):
        raise gdbbt.qc.QcError("ffmpeg chet")

    monkeypatch.setattr(gdbbt.qc, "do_hinh", no)
    hieu, hong = gdbbt._do_cac_canh("phim.mp4", ci, _ban_ghi_thoai((0.1, 0.2)))
    assert hieu == ()
    assert [h["loai"] for h in hong] == ["khong_do_duoc_hinh"] * 2


def test_phien_ban_ffmpeg_vao_VAN_TAY_ban_bien_tap():
    """⚠️ Doi ffmpeg co the doi ranh gioi khoang den/dung hinh ⇒ doi QUYET DINH
    CAT. Mot bo dem khong biet phien ban ffmpeg la mot bo dem noi doi.

    ⛔ Va nhanh GIU HINH ⛔ khong mang khoa nay: no khong chay ffmpeg de quyet
       dinh gi, nen mot phien ban ffmpeg trong van tay cua no la mot ban khai ve
       mot thu khong tham gia.
    """
    ma = inspect.getsource(gdbbt.chay)
    assert "nhap_media.phien_ban_ffmpeg()" in ma
    assert '"ffmpeg"' in ma
    # Khoa chi duoc gan trong nhanh CO bang chung.
    assert "if hieu:" in ma[:ma.index('"ffmpeg"')]
