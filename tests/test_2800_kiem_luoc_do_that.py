"""Doi chieu `Base.metadata` voi luoc do THAT — bat "alembic noi doi" ngay ngay dau.

🔴 Su co do 23/09/2026. Giua 01/09 23:04 va 06/09 08:51, `alembic_version` tren
   production bi day qua NAM revision ma khong thuc thi cai nao. Ca nam bang
   `asv_*` khong bao gio duoc tao. Suot 21 luot deploy sau do, moi luot deu in
   `[OK] Luoc do CSDL da o ban moi nhat` — vi dong do in VO DIEU KIEN khi
   `alembic upgrade head` tra ma 0, ma "khong co gi de lam" cung tra 0.

   Su co nam im 20 ngay. No chi lo ra khi mot vong quet tai san (ra doi 04/09)
   duoc deploy va bat dau nem `UndefinedTable` vao log worker — tuc no lo ra
   boi mot TAI NAN, khong boi mot phep kiem.

⭐ Day dung khuon "hai cho khai cung mot dieu ma khong ai bat khop"
   (`docs/BAY_TRONG_CONG_CHAT_LUONG.md`): `alembic_version` noi "da chay toi
   day", `information_schema` noi "bang nay khong ton tai", va khong ai doi
   chieu hai ben. Co hoc thang giao uoc.

Phep kiem o day chot PHAN THUAN cua cong cu (so sanh hai tap, gom theo app).
Phan doc CSDL that song o `tools/kiem_luoc_do.py` va chay o moi lan deploy.
"""
from __future__ import annotations

import pytest

from tools import kiem_luoc_do as K


def _ma_song() -> str:
    """`setup/2-cai-dat.ps1` sau khi bo moi dong chu thich."""
    import pathlib
    ps1 = pathlib.Path(__file__).resolve().parents[1] / "setup" / "2-cai-dat.ps1"
    return "\n".join(d for d in ps1.read_text(encoding="ascii").splitlines()
                     if not d.lstrip().startswith("#"))


def _khai(**bang) -> dict[str, set[str]]:
    """`{ten_bang: {cot,...}}` — dang ma ca hai ben duoc quy ve."""
    return {t: set(c) for t, c in bang.items()}


# ── bat thieu bang ──────────────────────────────────────────────────────────

def test_thieu_ca_bang_thi_bao_thieu():
    lech = K.doi_chieu(
        khai=_khai(asv_run=["id"], users=["id"]),
        that=_khai(users=["id"]))
    assert [x.ten for x in lech.bang_thieu] == ["asv_run"]
    assert lech.dat is False


def test_khop_het_thi_DAT():
    """Doi chung. Thieu no thi phep tren xanh ca khi cong cu luon bao thieu."""
    lech = K.doi_chieu(khai=_khai(users=["id", "email"]),
                       that=_khai(users=["id", "email"]))
    assert lech.dat is True
    assert lech.bang_thieu == [] and lech.cot_thieu == []


# ── bat thieu COT, khong chi bang ───────────────────────────────────────────

def test_thieu_cot_cung_bi_bat():
    """🔴 Lo hong cua ban do TAY ngay 23/09: no chi gom `create_table(...)` nen
    mot revision chi `add_column` ma bi bo qua thi khong ai thay. Bang co mat
    KHONG co nghia la bang dung hinh dang."""
    lech = K.doi_chieu(
        khai=_khai(waitpoint=["id", "so_nguon"]),
        that=_khai(waitpoint=["id"]))
    assert lech.bang_thieu == []
    assert [(x.bang, x.ten) for x in lech.cot_thieu] == [("waitpoint", "so_nguon")]
    assert lech.dat is False


# ── cot THUA khong phai loi ─────────────────────────────────────────────────

def test_cot_thua_ben_CSDL_khong_lam_do():
    """CSDL co cot ma ORM khong khai la chuyen binh thuong: cot cu cho mot ban
    go dan, hoac cot do mot cong cu ngoai them. Bao do vi no la bien mot phep
    kiem that thanh mot phep kiem bi bo qua."""
    lech = K.doi_chieu(khai=_khai(users=["id"]),
                       that=_khai(users=["id", "cot_cu"]))
    assert lech.dat is True


def test_bang_THUA_ben_CSDL_cung_khong_lam_do():
    lech = K.doi_chieu(khai=_khai(users=["id"]),
                       that=_khai(users=["id"], bang_la=["id"]))
    assert lech.dat is True


# ── bao theo APP, va KHONG loc app dang tat ─────────────────────────────────

def test_gom_theo_app_chu_khong_chi_liet_ke_bang():
    """"thieu asv_run, asv_stage, ..." doc ra nhu rac cua mot app dang tat.
    "app auto_scan_video: thieu 5/5 bang" doc ra thanh mot cau co nghia."""
    lech = K.doi_chieu(
        khai=_khai(asv_run=["id"], asv_stage=["id"], users=["id"]),
        that=_khai(users=["id"]),
        chu_bang={"asv_run": "auto_scan_video", "asv_stage": "auto_scan_video"})
    theo_app = lech.gom_theo_app()
    assert theo_app["auto_scan_video"] == 2


def test_app_DANG_TAT_van_bi_soi():
    """⛔ Dung loc app dang tat — do CHINH LA cho benh nap.

    `auto_scan_video` khai `enabled=False`, nen khong luong nao cham bang cua
    no, nen khong co gi keu. Do la ly do su co song duoc 20 ngay. Mot phep
    kiem bo qua app dang tat se bo qua dung ca ma no sinh ra de bat.
    """
    lech = K.doi_chieu(khai=_khai(asv_run=["id"]), that=_khai())
    assert lech.dat is False, "app dang tat van phai bi soi"


# ── cong cu phai noi duoc bang tieng nguoi ──────────────────────────────────

def test_bao_cao_noi_ro_so_bang_va_so_cot():
    lech = K.doi_chieu(
        khai=_khai(a=["id", "x"], b=["id"]),
        that=_khai(a=["id"]))
    bao = lech.bao_cao()
    assert "b" in bao and "x" in bao
    assert "1" in bao


def test_khong_lech_thi_bao_cao_noi_DAT():
    bao = K.doi_chieu(khai=_khai(a=["id"]), that=_khai(a=["id"])).bao_cao()
    assert "DAT" in bao.upper()


# ── banh coc: cong cu phai co mat o duong deploy ────────────────────────────

def test_deploy_co_goi_phep_kiem_nay():
    """Mot phep kiem chi chay khi ai do nho thi se khong bat duoc lan sau.

    Bang chung ro nhat cua su co 23/09: 21 luot deploy deu in dau xanh. Neu
    phep nay khong nam TRONG duong deploy thi no chi la mot cong cu dep.
    """
    assert "kiem_luoc_do" in _ma_song(), (
        "setup/2-cai-dat.ps1 khong goi tools/kiem_luoc_do.py - phep kiem nay "
        "se khong bao gio chay o luc no can chay nhat")


@pytest.mark.parametrize("cau", [
    "da chay",            # co migration -> noi SO
    "khong co migration", # khong co -> noi dung la khong co
])
def test_deploy_khong_con_in_mot_dau_OK_chung_cho_hai_tinh_huong(cau):
    """Chinh dong OK vo dieu kien da giup su co song sot qua 21 luot deploy."""
    assert cau in _ma_song()
    # Doc MA SONG, khong doc ca tep: chu thich trong tep CO TRICH nguyen dong
    # cu de ke lai su co, va mot phep kiem cam chuoi do o moi noi se cam luon
    # viec ghi lai lich su — tuc phat dung thu dang lam nguoi sau hieu chuyen.
    assert "Ok 'Luoc do CSDL da o ban moi nhat'" not in _ma_song(), (
        "dau OK vo dieu kien da quay lai")


def test_bao_cao_THUAN_ASCII_vi_no_in_ra_console_windows():
    """🔴 Suyt lap lai chinh ho loi dang sua.

    `setup/2-cai-dat.ps1` in ket qua nay ra console Windows (cp1252). Mot ky tu
    ngoai ASCII o day la mot `UnicodeEncodeError` giet dung phep kiem sinh ra de
    phat hien loi — tuc lop bao ve cuoi cung chet cam, y het dau OK vo dieu kien
    ma no thay the.
    """
    lech = K.doi_chieu(khai=_khai(asv_run=["id"], b=["id", "x"]),
                       that=_khai(b=["id"]))
    for ten, cau in (("bao_cao khi LECH", lech.bao_cao()),
                     ("bao_cao khi DAT",
                      K.doi_chieu(khai=_khai(a=["id"]), that=_khai(a=["id"])).bao_cao())):
        xau = [c for c in cau if ord(c) >= 128]
        assert not xau, f"{ten} co ky tu ngoai ASCII: {xau[:3]}"
