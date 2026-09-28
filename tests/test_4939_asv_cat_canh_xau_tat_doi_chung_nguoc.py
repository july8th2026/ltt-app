"""B14 — chu du an chot 28/09 BO tinh nang "cat canh xau" (gom ca E2/diem_dong).

⛔ KHONG rip giai doan `edit_plan` khoi `pipeline.CHUOI` — TAT quyet dinh, GIU
bo xuong (doc canh, do den/dung hinh). Neo cua viec tat: `giai_doan_ban_bien_
tap.chay()` nay goi `ban_bien_tap.lap_ban(hieu_canh=())` VO DIEU KIEN, buoc
MOI canh di qua nhanh "khong co bang chung — giu" DA CO SAN cua
`_quyet_dinh_mot_canh` — dung mot HOP DONG da duoc kiem (`test_438::
test_KHONG_co_bang_chung_thi_GIU`), ⛔ khong phai mot nhanh moi.

Ba nhom:
  A. `edit_plan` ra RONG tren BAT KY dau vao — chot bang `lap_ban` THAT
  B. Neo — AST: cho goi `lap_ban(` trong `chay()` phai truyen `hieu_canh=()`
  C. Doi chung NGUOC — `ke_cat.chon` van dung khi goi TRUC TIEP voi ung vien
     (E3 hop-khong-tong, `co_thoai`, tran 5%) du duong san pham da tat
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.auto_scan_video import ban_bien_tap as bt
from apps.auto_scan_video import canh as cn
from apps.auto_scan_video import hieu_canh as hc
from apps.auto_scan_video import ke_cat as kc
from apps.auto_scan_video.hop_dong_v4 import PRESET_CAT_THONG_MINH as CAT

GOC = pathlib.Path(__file__).resolve().parent.parent / "apps" / "auto_scan_video"


def _ci(so=127, dai=2.0) -> cn.ChiMucCanh:
    return cn.ChiMucCanh(
        tuple(cn.Canh(f"canh_{i:04d}", i * dai, (i + 1) * dai) for i in range(so)),
        so * dai)


def _bang_chung_cat_manh(so: int):
    """Bang chung se cat SACH neu con duoc doc — do_tin 1.0, de_xuat "bo"."""
    return [hc.HieuCanh(f"canh_{i:04d}", de_xuat="bo", do_tin=1.0)
           for i in range(so)]


# ══════════════════════════════════════════════════════════════════════════════
#  A. edit_plan ra RONG tren BAT KY dau vao
# ══════════════════════════════════════════════════════════════════════════════

def test_lap_ban_hieu_canh_rong__GIU_MOI_canh_du_chi_muc_the_nao():
    """`hieu_canh=()` (dung nhu `chay()` nay truyen) -> GIU TAT CA, bat ke so
    canh hay do dai — ⛔ khong phai mot ket qua may man tren MOT chi muc."""
    for so_canh in (1, 6, 127, 300):
        ci = _ci(so_canh)
        ban = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=())
        assert ban.cac_ma_cat == (), f"so_canh={so_canh}"
        assert len(ban.cac_ma_giu) == so_canh


def test_bang_chung_MANH_van_bi_BO_QUA_khi_hieu_canh_rong():
    """🔴 Doi chung TRUC TIEP: cung mot chi muc, bang chung se cat SACH neu
    duoc doc (`do_tin=1.0`) — nhung `chay()` nay KHONG con doc no
    (`hieu_canh=()` thay vi `hieu_canh=hieu`), nen ket qua van GIU HET."""
    ci = _ci(10)
    se_cat_neu_doc = bt.lap_ban(preset=CAT, chi_muc=ci,
                                hieu_canh=_bang_chung_cat_manh(10))
    assert se_cat_neu_doc.cac_ma_cat, "bang chung THAT manh phai cat duoc"

    that_su = bt.lap_ban(preset=CAT, chi_muc=ci, hieu_canh=())
    assert that_su.cac_ma_cat == (), (
        "duong san pham (hieu_canh=()) phai GIU HET du bang chung manh co ton "
        "tai — day chinh la 'tat quyet dinh'")


# ══════════════════════════════════════════════════════════════════════════════
#  B. Neo — AST: `chay()` phai truyen `hieu_canh=()`, ⛔ khong phai `hieu`
# ══════════════════════════════════════════════════════════════════════════════

def test_neo_AST__chay_goi_lap_ban_voi_hieu_canh_RONG_khong_phai_hieu():
    """Bam dung CHO GOI — mot ban vá vo tinh doi `hieu_canh=()` lai thanh
    `hieu_canh=hieu` se lam bai nay DO, truoc khi kip cham toi san pham that."""
    cay = ast.parse((GOC / "giai_doan_ban_bien_tap.py").read_text(encoding="utf-8"))
    goi_lap_ban = [n for n in ast.walk(cay)
                  if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "lap_ban"]
    assert len(goi_lap_ban) == 1, "phai co DUNG MOT cho goi lap_ban() trong chay()"
    kw = {k.arg: k.value for k in goi_lap_ban[0].keywords}
    assert "hieu_canh" in kw, "lap_ban() phai truyen hieu_canh tuong minh"
    gt = kw["hieu_canh"]
    assert isinstance(gt, ast.Tuple) and len(gt.elts) == 0, (
        f"hieu_canh phai la tuple RONG `()`, doc duoc: {ast.dump(gt)}")


# ══════════════════════════════════════════════════════════════════════════════
#  C. Doi chung NGUOC — `ke_cat.chon` goi TRUC TIEP van dung, du duong san
#     pham (giai_doan_hinh_anh) da ngung dua ung vien vao
# ══════════════════════════════════════════════════════════════════════════════

def _uv(bat, ket, diem=0.9):
    return kc.UngVien(bat=bat, ket=ket, diem_kem=diem, ly_do_cat="chat_luong_kem")


def test_doi_chung_nguoc_ke_cat_chon__E3_co_thoai_tran_5_van_dung_nguyen():
    """MOT lan goi, chot CA BA bat bien ma `ke_cat.chon` phai giu ke ca khi
    ⛔ khong con duong san pham nao dua ung vien vao no nua:

      1. `co_thoai` — ung vien cham khe thoai bi LOAI, ⛔ khong thu hep
      2. tran 5 % — ứng viên vượt ngân sách bị loại kèm lý do
      3. E3 — ngân sách đo bằng HỢP (hai ứng viên chồng nhau vẫn được nhận
         đúng cả hai, ⛔ không bị đóng sớm bởi một phép cộng sai)
    """
    tl = 100.0
    ung_vien = [
        _uv(0.0, 3.0, diem=0.95),     # (3) chong len uv2 -> hop, khong tong
        _uv(1.0, 4.0, diem=0.95),     # (3)
        _uv(50.0, 52.0, diem=0.99),   # (1) cham khe thoai -> LOAI
        _uv(90.0, 93.0, diem=0.10),   # (2) uu tien thap nhat -> vuot_tran
    ]
    ke = kc.chon(ung_vien, thoai=((51.0, 51.5),), thoi_luong=tl)

    # (3) E3: hop [0;4) = 4,0 s, ⛔ khong phai tong 3+3=6,0 s
    assert ke.cat == ((0.0, 4.0),)
    assert ke.giay_cat == pytest.approx(4.0)

    ly_do = {x["bat"]: x["ly_do"] for x in ke.bo_qua}
    assert ly_do[50.0] == kc.LY_DO_CO_THOAI          # (1)
    assert ly_do[90.0] == kc.LY_DO_VUOT_TRAN          # (2)

    assert ke.ti_le_cat <= kc.TRAN_CAT_TI_LE
    kc.kiem(ke)   # ⛔ khong nem — ke van hop le
