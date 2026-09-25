"""N-51 — cong QC (ngu nghia) FAIL-OPEN khi truong `loi` thieu hoac sai dang.

Ban ghi that: `docs/auto_scan_video_final/LOI_TONG.md` hang `N-51`, cho o
`apps/auto_scan_video/qc_ai.py:287-324` (`doc_ngu_nghia`, `_loc_loi`).

    `qc_ai.doc_ngu_nghia` tinh `dat` bang `not nang` voi
    `nang = [e for e in loi if e["muc"] in MUC_KHONG_DAT]` — `loi` lay tu
    `v.get("loi")` cua phan quyet model. `_loc_loi(None, ...)` (thieu khoa),
    `_loc_loi([], ...)` (rong that su), hay mot phan quyet bi cat giua dong
    deu cho `loi=[]` ⇒ `dat=True`: mot lan model KHONG NOI GI DOC DUOC bi doc
    thanh "da cham va sach", va tep di thang toi khach.

Thuoc dung (ghi trong LOI_TONG.md): thieu/hong truong `loi` phai tra ve mot
trang thai KHONG CHAM DUOC rieng — ⛔ khong duoc mac dinh `dat=True`.

## Fail-CLOSED — quyet dinh SAN PHAM, khong phai ma

`_loc_loi` gio NEM `qc_ai.QcAiError` khi `tho` (gia tri cua khoa `loi`)
KHONG PHAI list — cung khuon bat bien-o-bien voi `ke_cat.kiem()` /
`che_do_render.hinh_hoc_dien_nen`: mot noi DUY NHAT nem, moi noi goi (hien
tai chi `doc_ngu_nghia`) deu di qua cung mot cua, ⛔ khong phai mot `if` rai
rac o tung cho goi.

O `giai_doan_qc_ai.chay`, vong lap ngu nghia TRUOC day nuot MOI ngoai le
(`except Exception: ... continue`) va coi mot lo KHONG DOC DUOC nhu mot "lo
hong binh thuong, bo qua lang le" — dung hinh dang N-51 mot lan nua, o cho
GOI thay vi o cho DOC. Nhanh `except qc_ai.QcAiError: raise` moi them di
CUNG DUONG voi nhanh `hong` cua `jobs.py` ("QC hong" = `STAGE_FAILED_TERMINAL`),
⛔ khong phai cung duong voi "QC dat".

## Ba trang thai — ⛔ dung gop

    QC da cham va DAT         `dat=True`,  khong nem
    QC da cham va HONG        `dat=False`, khong nem  (co loi `nang`/`nghiem_trong` THAT)
    QC KHONG DOC DUOC         `QcAiError` — khiem khuyet cua TA, khong phai loi du lieu khach
"""
from __future__ import annotations

import inspect

import pytest

from apps.auto_scan_video import giai_doan_qc_ai as gdqa
from apps.auto_scan_video import qc_ai

#: Mot cap that, du de doan trich duoi day khop vao ca hai ben.
GOC = "源 产量 增加 了 百分之 二十"
DICH = "Sản lượng tăng hai mươi phần trăm trong năm nay."
VAN_BAN = {"seg_0001": (GOC, DICH)}


def _doc(loi, ma="seg_0001"):
    return qc_ai.doc_ngu_nghia({"doan": {ma: {"loi": loi}}}, {ma}, VAN_BAN)


# ══════════════════════════════════════════════════════════════════════════════
#  1. Cong THAT SU chan — dung tay mot phan quyet sai dang, phai bi TU CHOI
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("loi_hong", [
    None,                     # thieu / `loi: null` tuong minh
    "khong phai list",        # sai kieu — chuoi
    {"nang": 1},               # sai kieu — dict
    7,                         # sai kieu — so
], ids=["none", "chuoi", "dict", "so"])
def test_loi_thieu_hoac_sai_dang_bi_TU_CHOI_khong_duoc_coi_la_dat(loi_hong):
    """🔴 Day la phep kiem CHINH cua N-51: truoc sua, ca bon dau vao nay lam
    `dat=True` lang le. Sau sua, ca bon deu phai NEM, khong duoc tra ve gi."""
    with pytest.raises(qc_ai.QcAiError):
        _doc(loi_hong)


def test_khoa_loi_vang_mat_hoan_toan_cung_bi_TU_CHOI():
    """`v` KHONG co khoa `loi` nao ca (khac `loi: None` tuong minh o tren) —
    `.get("loi")` cung tra ve `None`, va phai di CUNG duong NEM."""
    with pytest.raises(qc_ai.QcAiError):
        qc_ai.doc_ngu_nghia({"doan": {"seg_0001": {}}}, {"seg_0001"}, VAN_BAN)


# ══════════════════════════════════════════════════════════════════════════════
#  2. ⚠️ DOI CHUNG BAT BUOC — QC dat BINH THUONG (hoac hong THAT) van di qua
#     Thieu phep nay thi chi chung minh duoc cong chan-DUOC-MOI-THU, khong
#     chung minh no chi chan dung THU CAN chan.
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_rong_that_su_VAN_la_DAT_khong_bi_chan():
    """`loi: []` la mot list HOP LE — "da cham, khong thay gi" — phai qua."""
    ra = _doc([])
    assert ra[0]["dat"] is True
    assert ra[0]["muc"] == ""
    assert ra[0]["loi"] == []


def test_loi_that_van_duoc_doc_DUNG_khong_bi_chan():
    ra = _doc([{"loai": "lat_nghia", "muc": "nang", "doan": "tăng"}])
    assert ra[0]["dat"] is False
    assert ra[0]["muc"] == "nang"
    assert len(ra[0]["loi"]) == 1


# ══════════════════════════════════════════════════════════════════════════════
#  3. Ba trang thai phan biet duoc bang CA GIA TRI LAN CO CHE — khong gop chung
# ══════════════════════════════════════════════════════════════════════════════

def test_ba_trang_thai_KHONG_gop_chung_mot_gia_tri():
    dat = _doc([])[0]
    hong = _doc([{"loai": "lat_nghia", "muc": "nang", "doan": "tăng"}])[0]
    assert dat["dat"] is True and hong["dat"] is False
    # Trang thai thu ba KHONG tra ve mot ban ghi cung khuon roi gan mot co —
    # no NEM, nen no khong the vo tinh bi doc nham thanh dat HAY hong.
    with pytest.raises(qc_ai.QcAiError):
        _doc(None)


# ══════════════════════════════════════════════════════════════════════════════
#  4. Cho GOI (`giai_doan_qc_ai.chay`) khong con nuot `QcAiError` lam "lo sach"
#
#     Mot lan chay() day du can toan bo ha tang hang doi/DB/lat_cat cua giai
#     doan khac (fixtures thuoc `tests/fixtures/asv_e2e.py`, ngoai pham vi lan
#     nay) — nen phep kiem duoi day doc CO CAU TRUC cua nhanh except (thu tu +
#     than nhanh), khong phai mot chuoi con tuy y.
# ══════════════════════════════════════════════════════════════════════════════

def test_giai_doan_qc_ai_KHONG_con_nuot_QcAiError_lam_lo_sach():
    src = inspect.getsource(gdqa.chay)
    assert "except qc_ai.QcAiError" in src, (
        "N-51: vong lap ngu nghia phai co nhanh rieng cho QcAiError, khong "
        "duoc de no roi xuong `except Exception` chung")

    vi_tri_moho = src.index("except ai.AiMoHo")
    vi_tri_qc = src.index("except qc_ai.QcAiError")
    vi_tri_chung = src.index("except Exception as exc:")
    assert vi_tri_moho < vi_tri_qc < vi_tri_chung, (
        "thu tu except sai: QcAiError phai duoc hoi TRUOC nhanh `Exception` "
        "chung, neu khong no van roi vao do va bi nuot y het truoc sua")

    than_nhanh_qc = src[vi_tri_qc:vi_tri_chung]
    assert "raise" in than_nhanh_qc, (
        "N-51: nhanh QcAiError phai NEM tiep (fail-closed), khong duoc "
        "`continue` coi nhu lo da hoi va sach")
    assert "continue" not in than_nhanh_qc, (
        "N-51: nhanh QcAiError khong duoc di theo duong 'lo hong binh "
        "thuong, bo qua lang le' cua nhanh Exception chung")


def test_QcAiError_duoc_PHAN_LOAI_la_khong_thu_lai_cho_qua():
    """`loi.phan_loai` (bien dich ngoai le -> loai cua nen tang, `thi_hanh.py`)
    da xep `QcAiError` vao nhom KHONG retry-cho-qua — chot lai hanh vi do o
    day de mot lan sua `loi.py` sau nay khong vo tinh lam QcAiError troi noi
    thanh mot phep thu lai am tham roi cuoi cung van `succeeded`."""
    from apps.auto_scan_video import loi

    assert loi.phan_loai(qc_ai.QcAiError("x")) != loi.TAM_THOI
