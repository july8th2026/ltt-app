"""P0-c — **BAI TRUC**: dem bang AST bao nhieu cho ha nguon dung tren TRUC GOC.

## Vi sao DEM, ⛔ khong liet ke tu tri nho

Mot danh sach "cac cho can sua" viet tay thanh **TRAN** cua viec (bai hoc
`liet-ke-tu-tri-nho-thay-vi-dem`). Nen tep nay ⛔ khong ke ten tu tri nho — no
quet AST va **chot TAP HOP**. Mot lan doi "cat dau o `media_prepare`" se lam bai
o duoi do, va thong bao do se ke ten dung nhung tep phai theo.

## Ba nhom cho, va ca ba dang o truc GOC

    A. doc `run.source_key`      — 5 module. Chung mo **ban goc, TOAN BO do dai**,
                                   ⛔ khong mo ban tieng cua `media_prepare`.
       🔴 `giai_doan_ket_xuat` (RENDER) va `giai_doan_am_thanh` (AUDIO_PREPARE) la
          hai cai nang nhat: RENDER dung hinh cua BAN GOC, con AUDIO_PREPARE rut
          nhac nen tu BAN GOC. Cat mot dau chi o ban tieng ASR ⇒ loi thoai tieng
          Viet bi dat len mot khung hinh va mot nen dai hon `dau_cat` giay.

    B. ap cua so `cat_dau_cuoi.giao`  — DUNG 2 cho, ca hai nhan do dai GD1
                                        (`test_4973` do cai gia cua cho thu ba).

    C. tru `dau_cat` o bien ASR       — **0 cho**. Day la phep con THIEU, va
                                        vang mat cua no chinh la chan chan.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

GOC = Path(__file__).resolve().parents[1]
THU_MUC = GOC / "apps" / "auto_scan_video"

#: 🔴 Do 28/09 (lan P0-c). Cac module mo BAN GOC qua `run.source_key`.
#:
#: ⭐ Con so 5 la mot **cai gia**, ⛔ khong phai mot bang liet ke: doi cat len
#:    `media_prepare` thi moi cho o day phai tra loi *"toi dung truc nao"*.
DOC_BAN_GOC = frozenset({
    "giai_doan_media",        # sinh `audio_full.wav` tu ban goc
    "giai_doan_am_thanh",     # AUDIO_PREPARE — nhac nen 44,1 kHz tu ban goc
    "giai_doan_ban_dung",     # COMPOSE — ghi `khoa_video=run.source_key`
    "giai_doan_ket_xuat",     # RENDER — `-c:v copy` HINH cua ban goc
    "giai_doan_qc",           # do ban ra SO VOI ban goc
})

#: Cua so khach duoc ap dung 2 cho, ca hai tren do dai ban ra cua GD1.
AP_CUA_SO = frozenset({
    "giai_doan_hinh_anh",     # cat THAT
    "giai_doan_qc",           # dung LAI phep giao de biet do dai mong doi
})


def _cay(ten: str):
    return ast.parse((THU_MUC / f"{ten}.py").read_text(encoding="utf-8"))


def _quet(kiem) -> set[str]:
    ra: set[str] = set()
    for f in sorted(THU_MUC.glob("*.py")):
        cay = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            if kiem(n):
                ra.add(f.stem)
                break
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  A — ai mo BAN GOC
# ══════════════════════════════════════════════════════════════════════════════

def test_dem_module_doc_run_source_key__chot_TAP_HOP():
    """🔴 Do bai nay ⇒ mot module vua bat dau (hay thoi) doc ban goc.

    ⛔ **Dung "cap nhat con so" roi di tiep.** Cau hoi phai tra loi la: module
       moi ay dung tren TRUC NAO — truc ban goc, hay truc da cat?
    """
    def la(n):
        return (isinstance(n, ast.Attribute) and n.attr == "source_key"
                and isinstance(n.value, ast.Name) and n.value.id == "run")

    assert _quet(la) == DOC_BAN_GOC


def test_render_va_audio_prepare_dung_BAN_GOC__khong_ban_tieng_media():
    """⭐ Hai cho nang nhat, goi ten rieng de mot nguoi doc bao cao khong phai
    tu suy tu tap hop o tren.

    RENDER `-c:v copy` HINH cua ban goc (`giai_doan_ket_xuat.py:130`), va
    AUDIO_PREPARE rut nen tu ban goc (`giai_doan_am_thanh.py:67`). Ca hai ⛔
    khong biet gi ve cua so khach — nen mot phep cat chi o ban tieng ASR lam loi
    thoai lech so voi HINH va so voi NEN dung bang `dau_cat`.
    """
    for ten in ("giai_doan_ket_xuat", "giai_doan_am_thanh"):
        assert ten in DOC_BAN_GOC
        nguon = (THU_MUC / f"{ten}.py").read_text(encoding="utf-8")
        # ⛔ Ca hai ⛔ khong doc artifact tieng cua MEDIA_PREPARE.
        assert "MEDIA_PREPARE" not in nguon, ten


# ══════════════════════════════════════════════════════════════════════════════
#  B — cua so khach ap o DUNG hai cho
# ══════════════════════════════════════════════════════════════════════════════

def test_cua_so_khach_ap_o_DUNG_HAI_cho():
    """`giao` la cho DUY NHAT doi phan so -> giay (`cat_dau_cuoi.py:11-14`), nen
    dem `giao` la dem cac lan AP."""
    def la(n):
        return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "giao"
                and isinstance(n.func.value, ast.Name))

    assert _quet(la) == AP_CUA_SO


def test_media_prepare_KHONG_o_trong_tap_ap_cua_so():
    """Bai chot phan quyet cua lan P0-c, phat bieu nguoc de doc duoc mot dong."""
    assert "giai_doan_media" not in AP_CUA_SO


# ══════════════════════════════════════════════════════════════════════════════
#  C — phep TRU `dau_cat` o bien ASR: DO SU VANG MAT
# ══════════════════════════════════════════════════════════════════════════════

def test_canary_TEN_bu_truc_chua_xuat_hien_o_dau():
    """🔴 **Mot CANARY theo TEN, ⛔ KHONG phai mot bang chung.**

    `test_4973::test_bai_truc__*` ghim dai luong: cat dau ⇒ moc phai thanh
    `T - dau_cat`. Neu phep cat duoc doi len `media_prepare` thi mot cho nao do
    giua ASR va `compose` **phai** cong lai `dau_cat`, neu ⛔ khong loi thoai
    tieng Viet se dat len hinh lech dung bang do.

    ⚠️ **Gioi han phai noi ra**: bai nay do su VANG MAT cua bon CAI TEN, nen mot
       phep bu viet duoi ten khac se di qua ma no ⛔ khong do. Lop bao ve THAT la
       hai bai tren (`AP_CUA_SO` chot tap hop) va `test_4974` (AST chan
       `media_prepare` doc `cai_dat`/import module cat). Bai nay chi la mot cai
       chuong re — giu vi no re, ⛔ dung tin no la cong.
    """
    mo_ta = ("offset", "dau_cat", "dich_truc", "bu_truc")
    co = {f.stem for f in sorted(THU_MUC.glob("*.py"))
          for n in ast.walk(ast.parse(f.read_text(encoding="utf-8")))
          if isinstance(n, ast.Name) and n.id in mo_ta}
    assert co == set(), sorted(co)


def test_khoa_tieng_ASR_den_tu_MEDIA_PREPARE__mot_bien_duy_nhat():
    """⭐ Bien giua "ban goc" va "ban tieng" nam o DUNG mot ham:
    `giai_doan_chep_loi._khoa_tieng_asr`. ⇒ Moi phep bu truc, neu mot ngay nao
    do can, se phai di qua day — nen bai nay ghim rang bien ay ton tai va chi co
    MOT."""
    cay = _cay("giai_doan_chep_loi")
    ham = [n.name for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and "khoa_tieng" in n.name]
    assert ham == ["_khoa_tieng_asr"]
