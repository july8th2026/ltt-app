"""ASV V6 pha 22 — Dubbing adaptation + fit: giong chot TRUOC, va nguong do duoc.

🔑 **Bac thang vua khe bon nac da co tu V4** (`nan_cho_vua`): do tren tep that ->
   viet lai RIENG doan -> co gian co tran -> danh dau can sua. Pha 22 khong viet
   lai no. Hai viec con thieu:

   1. Menh de dau tien cua de bai — *"VoiceBinding truoc rewrite"* — chua bai nao
      chot. Loi thoai duoc viet lai cho VUA toc do doc cua MOT giong; viet lai
      truoc khi giong chot (hoac voi mot giong khac) la do do dai cho mot giong
      roi doc bang giong kia.

   2. Nguong `DUNG_SAI_DAI = 0,08` tu khai **CHUA DO**. Tom tat giai doan chi co
      con so GOP, va con so gop khong tra loi duoc *"bao nhieu doan nam gan
      nguong"*. Nay tom tat mang TUNG DOAN — de luot nghiem thu that ke tiep do
      duoc nguong.

⭐ Du lieu that dau tien (nghiem thu 11/09, model that + giong that, n = 12 doan):
   `so_can_sua = 2` o MOI canh, `lech_lon_nhat = 0,5618`. Chua tach duoc do la 4
   doan hay 2 doan tai dung — chinh vi thieu du lieu tung doan. Xem
   `PHA22_VUA_KHE.md`.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import nan_cho_vua as n

GOC = Path(__file__).resolve().parents[1]


def _ba_doan():
    return [n.ket_luan("s1", chu="loi thoai mot", giay=3.0, khe=3.0, so_vong=0),
            n.ket_luan("s2", chu="loi thoai hai", giay=3.3, khe=3.0, so_vong=2),
            n.ket_luan("s3", chu="loi thoai ba", giay=5.0, khe=3.0, so_vong=2)]


# ══ 1. Tom tat mang TUNG DOAN ═══════════════════════════════════════════════

def test_tom_tat_co_TUNG_DOAN_du_so_luong():
    t = n.tom_tat(_ba_doan())
    assert len(t["tung_doan"]) == t["so_doan"] == 3
    assert [d["ma"] for d in t["tung_doan"]] == ["s1", "s2", "s3"]


def test_tung_doan_KHONG_mang_loi_thoai_cua_khach():
    """⛔ Tom tat la sieu du lieu cua giai doan; loi thoai la noi dung cua khach."""
    for d in n.tom_tat(_ba_doan())["tung_doan"]:
        assert "chu" not in d
        assert not any("loi thoai" in str(v) for v in d.values())


def test_lech_tung_doan_KHOP_ham_lech():
    for k, d in zip(_ba_doan(), n.tom_tat(_ba_doan())["tung_doan"], strict=True):
        assert d["lech"] == pytest.approx(n.lech(k.giay, k.khe), abs=1e-4)
        assert d["trang_thai"] == k.trang_thai


def test_du_lieu_tung_doan_TACH_DUOC_ba_nac_quanh_nguong():
    """⭐ Day la cau hoi con so gop khong tra loi duoc: doan nao nam o nac nao,
       lech bao nhieu so voi `DUNG_SAI_DAI`.
    """
    t = n.tom_tat(_ba_doan())
    theo_ma = {d["ma"]: d for d in t["tung_doan"]}
    assert theo_ma["s1"]["lech"] <= n.DUNG_SAI_DAI
    assert n.DUNG_SAI_DAI < theo_ma["s2"]["lech"] <= n.tran_co_gian() - 1
    assert theo_ma["s3"]["lech"] > n.tran_co_gian() - 1


def test_khoa_GOP_cu_van_con_nguyen():
    """⚠️ `test_448` va bao cao nghiem thu doc cac khoa gop. Them tung doan khong
       duoc lam mat khoa nao cua ban cu.
    """
    t = n.tom_tat(_ba_doan())
    for k in ("so_doan", "so_vua", "so_co_gian", "so_can_sua", "so_vong_tong",
              "lech_lon_nhat"):
        assert k in t, k


def test_tom_tat_rong_van_hop_le():
    t = n.tom_tat([])
    assert t["so_doan"] == 0 and t["tung_doan"] == [] and t["lech_lon_nhat"] == 0.0


# ══ 2. Giong chot TRUOC moi lan viet lai ════════════════════════════════════

def _chay_cua_giai_doan_giong():
    cay = ast.parse((GOC / "apps/auto_scan_video/giai_doan_giong.py")
                    .read_text(encoding="utf-8"))
    return next(f for f in cay.body if isinstance(f, ast.FunctionDef)
                and f.name == "chay")


def _dong_goi(fn, ten_thuoc_tinh):
    return sorted(c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                  and isinstance(c.func, ast.Attribute)
                  and c.func.attr == ten_thuoc_tinh)


def test_giong_duoc_giai_TRUOC_moi_lan_nho_viet_lai():
    """🔑 Menh de dau tien cua de bai pha 22.

    Loi thoai duoc viet lai cho vua toc do doc cua MOT giong. Neu giong duoc
    giai SAU vong viet lai (hoac giai lai giua chung) thi do dai duoc do cho mot
    giong roi doc bang giong khac.
    """
    fn = _chay_cua_giai_doan_giong()
    giai = _dong_goi(fn, "giai_giong")
    assert len(giai) == 1, f"giai giong {len(giai)} lan trong `chay` — phai MOT"
    nac = _dong_goi(fn, "can_nan") + _dong_goi(fn, "ket_luan")
    assert nac, "khong tim thay bac thang nan trong `chay`"
    assert giai[0] < min(nac), (giai, nac)


def test_vong_viet_lai_KHONG_tu_doc_giong_tu_settings():
    """⛔ Mot nguon cho "giong nao?" (pha 19). Ham viet lai khong duoc doc lai
       `giong_id` tu `settings`.
    """
    cay = ast.parse((GOC / "apps/auto_scan_video/giai_doan_giong.py")
                    .read_text(encoding="utf-8"))
    for f in ast.walk(cay):
        if isinstance(f, ast.FunctionDef) and f.name.startswith("_viet_lai"):
            doc = {a.attr for a in ast.walk(f) if isinstance(a, ast.Attribute)}
            assert "giong_id" not in doc, f.name
            assert "giai_giong" not in doc, f.name
