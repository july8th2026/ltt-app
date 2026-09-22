"""ASV V6 pha 19 — VoiceBinding: giong khong the chot bi tu choi O CUA.

🔑 **Truoc pha 19, cua `routes.tao` chi hoi: "USER_SELECTED co kem ma giong
   khong".** Quyen so huu duoc kiem o `giai_doan_noi_dung` — tuc SAU khi khach
   bi giu credit va sau tach nguon + ASR. Mot ma giong cua nguoi khac, mot giong
   da tat, mot ma go sai: ca ba di het doan dat tien roi moi hong.

⭐ Menh de DUONG cua tep nay, chot o tang HTTP that voi CSDL that:
   mot ma giong khong thuoc tai khoan -> 400, **khong** tao lan chay, **khong**
   dong vao credit. Va doi chung: cung form voi mot giong mau thi CHAY duoc —
   neu khong, bai kia se xanh ca khi cua tu choi MOI giong.

⚠️ Pham vi, noi thang: bai HTTP dung mot ma giong KHONG TON TAI, khong dung
   giong nhan ban cua nguoi dung B. LTT Voice co y tra CUNG MOT CAU cho hai
   truong hop do (`features.giai_giong`: phan biet chung la cho do xem ma nao
   co that), va ASV chuyen nguyen cau ay — nen ca hai di cung mot nhanh.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import giong_noi, hop_dong_v4, loi, rang_giong

# Nhap MODULE roi lay thuoc tinh — xem ghi chu F811 o `test_455`.
from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

TU_CHON = hop_dong_v4.CHE_DO_GIONG_TU_CHON
TU_KHOP = hop_dong_v4.CHE_DO_GIONG_TU_KHOP
CAU_KHONG_THAY = "Không tìm thấy giọng này trong tài khoản của bạn."


def _mau() -> str:
    from apps.ltt_voice.giong_mau import DANH_SACH

    return DANH_SACH[0].ma


# ══ 1. `kiem_o_cua` ═════════════════════════════════════════════════════════

def test_USER_SELECTED_de_trong_bi_TU_CHOI():
    with pytest.raises(rang_giong.RangGiongError) as e:
        rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_CHON, giong_id="  ")
    assert "Hãy chọn một giọng đọc" in str(e.value)


def test_giong_mau_duoc_NHAN_khong_cham_CSDL():
    """Giong mau ai cung dung duoc — khong co chu so huu de kiem."""
    rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_CHON, giong_id=_mau())


def test_AUTO_MATCH_khong_doi_ma_giong_o_cua():
    """⛔ Doi mot ma giong o cua cho `AUTO_MATCH` la dung loi D-V4-04 cam:
       giong cua che do nay chot SAU, tu ho so noi dung.
    """
    rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_KHOP, giong_id="")


def test_giong_khong_thuoc_tai_khoan_bi_TU_CHOI_bang_CAU_CUA_LTT_VOICE(monkeypatch):
    """⚠️ Chuyen NGUYEN cau cua LTT Voice, khong viet lai: ho co y dung cung mot
       cau cho "khong co" va "khong phai cua ban".
    """
    # `giong_noi.giai_giong` THAT boc `ltt_voice.LoiGiongNoi` thanh
    # `GiongKhongHopLe` (giu nguyen cau) — stub nem dung thu ham that nem.
    def _tu_choi(db, *, owner_id, voice_id="", preset="", **_):
        raise giong_noi.GiongKhongHopLe(CAU_KHONG_THAY)

    monkeypatch.setattr(giong_noi, "giai_giong", _tu_choi)
    with pytest.raises(rang_giong.RangGiongError) as e:
        rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_CHON,
                              giong_id="giong-cua-nguoi-khac")
    assert str(e.value) == CAU_KHONG_THAY


def test_loi_HA_TANG_KHONG_bi_doi_thanh_loi_cua_khach(monkeypatch):
    """⭐ Chi bat dung lop loi cua khach. Mot loi CSDL doi thanh "giong khong hop
       le" la bao khach sua mot thu ho khong he lam sai — va giau mat su co.
    """
    def _sap(db, *, owner_id, voice_id="", preset="", ngon_ngu=""):
        raise RuntimeError("CSDL mat ket noi")

    monkeypatch.setattr(giong_noi, "giai_giong", _sap)
    with pytest.raises(RuntimeError, match="CSDL"):
        rang_giong.kiem_o_cua(None, owner_id="u", che_do=TU_CHON, giong_id="x-1")


def test_ChuaRangError_xep_loai_NGUOI_DUNG():
    """Thu lai khong lam `ma_giong` xuat hien trong mot ban long tieng thieu no."""
    assert loi.phan_loai(rang_giong.ChuaRangError("x")) == loi.NGUOI_DUNG


# ══ 2. Cua HTTP that ════════════════════════════════════════════════════════

def _nop(client, csrf, tmp_path, giong_id):
    from tests.fixtures.asv_media import tiny_mp4

    tep = tiny_mp4(tmp_path / "a.mp4", duration_s=1.0)
    with open(tep, "rb") as f:
        return client.post("/auto-scan-video/tao", data={
            "csrf_token": csrf, "che_do": "fit_original",
            "che_do_giong": TU_CHON, "giong_id": giong_id},
            files={"video": ("a.mp4", f, "video/mp4")})


def _so_run_va_so_du():
    import platform_core.db as dbmod
    from sqlalchemy import func, select

    from apps.auto_scan_video.tables import AsvRun
    from platform_core import credit
    from platform_core.models import User

    db = next(dbmod.get_session())
    try:
        so_run = db.execute(select(func.count()).select_from(AsvRun)).scalar_one()
        u = db.execute(select(User).where(User.email == "asv-a@example.com")
                       ).scalar_one()
        return so_run, credit.so_du(db, u.id)
    finally:
        db.close()


def test_HTTP_ma_giong_khong_thuoc_tai_khoan_TU_CHOI_truoc_khi_giu_credit(
        moi_truong, tmp_path):
    """🔴 Bai quan trong nhat cua tep nay."""
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong

    run_truoc, du_truoc = _so_run_va_so_du()
    r = _nop(a, csrf, tmp_path, "giong-khong-thuoc-ai-ca-7f3a")
    assert r.status_code == 400, r.status_code
    assert CAU_KHONG_THAY in r.text
    run_sau, du_sau = _so_run_va_so_du()
    assert run_sau == run_truoc, "tao lan chay cho mot giong khong the chot"
    assert du_sau == du_truoc, "da giu credit cho mot giong khong the chot"


def test_HTTP_giong_mau_CHAY_duoc_doi_chung(moi_truong, tmp_path):
    """⭐ Doi chung: neu cua tu choi MOI giong thi bai tren van xanh."""
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong

    run_truoc, _ = _so_run_va_so_du()
    r = _nop(a, csrf, tmp_path, _mau())
    assert r.status_code == 200, r.text[:300]
    run_sau, _ = _so_run_va_so_du()
    assert run_sau == run_truoc + 1


# ══ 3. MOT nguon cho "giong nao?" ═══════════════════════════════════════════

def test_giai_doan_giong_KHONG_con_lui_ve_settings():
    """🔴 Voi `AUTO_MATCH`, `settings.giong_id` RONG. Duong lui `or cai.giong_id`
       roi xuong `""`, va `giai_giong("")` = giong mac dinh cua engine, khong
       ai bam nut. Chot bang AST: phep gan `ma_giong` khong duoc doc `giong_id`.
    """
    goc = Path(__file__).resolve().parents[1]
    cay = ast.parse((goc / "apps/auto_scan_video/giai_doan_giong.py")
                    .read_text(encoding="utf-8"))
    gan = [n for n in ast.walk(cay) if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "ma_giong" for t in n.targets)]
    assert gan, "khong tim thay phep gan `ma_giong`"
    for n in gan:
        doc = {a.attr for a in ast.walk(n.value) if isinstance(a, ast.Attribute)}
        assert "giong_id" not in doc, ast.unparse(n)


def test_route_goi_kiem_o_cua():
    """⛔ `nang-luc-co-nhung-khong-ai-di-tren-duong`: ham kiem ton tai ma cua khong
       goi no thi moi bai o muc 1 van xanh.
    """
    goc = Path(__file__).resolve().parents[1]
    cay = ast.parse((goc / "apps/auto_scan_video/routes.py").read_text(encoding="utf-8"))
    goi = [n for n in ast.walk(cay) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "kiem_o_cua"]
    assert goi, "routes.py khong goi rang_giong.kiem_o_cua"
