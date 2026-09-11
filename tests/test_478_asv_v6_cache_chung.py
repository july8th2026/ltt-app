"""ASV V6 pha 25 — cache DUNG CHUNG xuyen lan chay: dia chi noi dung, chu so huu.

🔑 Khach nop lai CUNG mot video (doi giong, doi preset...) thi tach nguon va chep
   loi — hai thu dat nhat — khong duoc chay lai. Nhung khoa dung chung phai la
   **noi dung**, khong phai van tay giai doan: van tay giai doan khong mang danh
   tinh nguon, nen hai video khac nhau cung settings se trung van tay.

⭐ Moi phep kiem "co dung lai" di kem mot phep kiem "KHONG duoc dung lai" o cung
   duong — mot cache chi duoc chung minh la dung khi no cung chung minh duoc la
   no biet TU CHOI.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests import test_403_asv_vong_doi_artifact as _t403
from tests.conftest import bao_dam_user

# Fixture dung chung voi vong doi artifact: CSDL + kho + ASR gia that su giong het.
db, kho, asr_gia = _t403.db, _t403.kho, _t403.asr_gia

GOC = Path(__file__).resolve().parents[1]
BA = ("media_prepare", "audio_prepare", "transcribe")


def _nguon(kho, tmp_path, *, owner="uA", ten="a", tone_hz=None, chep_tu=None):
    """Tep nguon trong kho. `chep_tu` = CUNG BYTE, KHAC KHOA (khach tai lai)."""
    from tests.fixtures.asv_media import tiny_mp4

    khoa = f"asv/{owner}/nguon-{ten}/nguon.mp4"
    if chep_tu:
        with kho.open(chep_tu) as f:
            du_lieu = f.read()
    else:
        kw = {"tone_hz": tone_hz} if tone_hz else {}
        du_lieu = tiny_mp4(tmp_path / f"{ten}.mp4", **kw).read_bytes()
    kho.put(khoa, io.BytesIO(du_lieu), content_type="video/mp4")
    return khoa


def _run(db, khoa_nguon, *, owner="uA", **settings):
    from platform_core import credit
    from apps.auto_scan_video import features

    bao_dam_user(db, owner)
    credit.nap(db, owner, 1000)
    run = features.tao_run(db, owner_id=owner, source_key=khoa_nguon,
                           settings={"giong_id": "Minh Đức", **settings},
                           uoc_luong_credit=10)
    db.commit()
    return run


def _chay(db, run, ten):
    from apps.auto_scan_video import thi_hanh

    thi_hanh.chay_giai_doan(ten, {"run_id": run.id, "owner_id": run.owner_id})
    db.expire_all()


def _gd(db, run, ten):
    from apps.auto_scan_video import features

    return features.giai_doan_theo_ten(db, run.id, ten)


@pytest.fixture()
def dem_engine(monkeypatch):
    """Dem so lan ENGINE that cua hai giai doan dat duoc goi."""
    from apps.auto_scan_video import giai_doan_am_thanh, giai_doan_chep_loi

    dem = {"audio_prepare": 0, "transcribe": 0}
    for ten, mod in (("audio_prepare", giai_doan_am_thanh),
                     ("transcribe", giai_doan_chep_loi)):
        that = mod.chay

        def boc(*a, _ten=ten, _that=that, **kw):
            dem[_ten] += 1
            return _that(*a, **kw)
        monkeypatch.setattr(mod, "chay", boc)
    return dem


def _hai_lan_chay(db, kho, tmp_path, *, owner2="uA", chung=None, **settings2):
    """`chung` = thiet lap cho CA HAI lan chay; `settings2` = chi lan thu hai."""
    k1 = _nguon(kho, tmp_path)
    r1 = _run(db, k1, **(chung or {}))
    for t in BA:
        _chay(db, r1, t)
    k2 = _nguon(kho, tmp_path, owner=owner2, ten="b", chep_tu=k1)
    r2 = _run(db, k2, owner=owner2, **{**(chung or {}), **settings2})
    return r1, r2


# ══ 1. Dung lai: cung noi dung, cung khach ═══════════════════════════════════

def test_lan_chay_thu_hai_CUNG_noi_dung_KHONG_goi_engine(db, kho, tmp_path, asr_gia, dem_engine):
    r1, r2 = _hai_lan_chay(db, kho, tmp_path)
    assert dem_engine == {"audio_prepare": 1, "transcribe": 1}
    for t in BA:
        _chay(db, r2, t)
    assert dem_engine == {"audio_prepare": 1, "transcribe": 1}, (
        "lan chay thu hai cung noi dung van goi engine dat")
    for t in ("audio_prepare", "transcribe"):
        ra = _gd(db, r2, t).outputs
        assert _gd(db, r2, t).status == "succeeded"
        assert ra["tu_cache_chung"] is True
        assert ra["khoa_chung"] == _gd(db, r1, t).outputs["khoa_chung"]


def test_artifact_dung_lai_la_BAN_CHEP_cua_lan_chay_moi_cung_noi_dung(db, kho, tmp_path, asr_gia):
    from apps.auto_scan_video import assets

    r1, r2 = _hai_lan_chay(db, kho, tmp_path)
    for t in BA:
        _chay(db, r2, t)
    for t in ("audio_prepare", "transcribe"):
        k1 = _gd(db, r1, t).outputs["khoa_asset"]
        k2 = _gd(db, r2, t).outputs["khoa_asset"]
        assert len(k1) == len(k2) >= 1
        for a, b in zip(k1, k2, strict=True):
            assert a != b and f"/{r2.id[:24]}/" in b, "tro vao tep cua lan chay khac"
            assert (assets.asset_cua(db, a, "uA").checksum
                    == assets.asset_cua(db, b, "uA").checksum)


def test_xoa_lan_chay_CHO_khong_lam_hong_lan_chay_NHAN(db, kho, tmp_path, asr_gia):
    """🔑 Chep, khong tro: hai lan chay giu hai vong doi doc lap."""
    from apps.auto_scan_video import assets

    r1, r2 = _hai_lan_chay(db, kho, tmp_path)
    for t in BA:
        _chay(db, r2, t)
    assert assets.don_theo_run(db, kho, r1.id, "uA") > 0
    db.commit()
    for t in ("audio_prepare", "transcribe"):
        for k in _gd(db, r2, t).outputs["khoa_asset"]:
            assert assets.kiem_toan_ven(db, kho, assets.asset_cua(db, k, "uA")) == "ok"


def test_tom_tat_cua_lan_cho_di_theo_KHONG_mang_khoa_asset_cu(db, kho, tmp_path, asr_gia):
    r1, r2 = _hai_lan_chay(db, kho, tmp_path)
    for t in BA:
        _chay(db, r2, t)
    o1, o2 = _gd(db, r1, "transcribe").outputs, _gd(db, r2, "transcribe").outputs
    assert o2["so_doan"] == o1["so_doan"] > 0
    assert not set(o1["khoa_asset"]) & set(o2["khoa_asset"])


# ══ 2. TU CHOI dung lai ═════════════════════════════════════════════════════

def test_khach_KHAC_cung_noi_dung_van_TINH_LAI(db, kho, tmp_path, asr_gia, dem_engine):
    """⛔ I19: checksum trung la su that ve noi dung, khong phai giay phep."""
    r1, r2 = _hai_lan_chay(db, kho, tmp_path, owner2="uB")
    for t in BA:
        _chay(db, r2, t)
    assert dem_engine == {"audio_prepare": 2, "transcribe": 2}
    assert not _gd(db, r2, "transcribe").outputs.get("tu_cache_chung")
    assert (_gd(db, r1, "transcribe").outputs["khoa_chung"]
            != _gd(db, r2, "transcribe").outputs["khoa_chung"])


def test_noi_dung_KHAC_cung_settings_van_TINH_LAI(db, kho, tmp_path, asr_gia, dem_engine):
    """🔴 Day la ca van tay giai doan se dung SAI: settings trung, video khac."""
    k1 = _nguon(kho, tmp_path)
    r1 = _run(db, k1)
    for t in BA:
        _chay(db, r1, t)
    r2 = _run(db, _nguon(kho, tmp_path, ten="c", tone_hz=660))
    for t in BA:
        _chay(db, r2, t)
    assert dem_engine == {"audio_prepare": 2, "transcribe": 2}


def test_doi_NGON_NGU_NGUON_thi_chep_loi_TINH_LAI_con_tach_nguon_DUNG_LAI(
        db, kho, tmp_path, asr_gia, dem_engine):
    """Khoa mang DUNG nhung thiet lap giai doan doc — khong hon, khong kem."""
    r1, r2 = _hai_lan_chay(db, kho, tmp_path, ngon_ngu_nguon="en")
    for t in BA:
        _chay(db, r2, t)
    assert dem_engine == {"audio_prepare": 1, "transcribe": 2}


def test_nang_PHIEN_BAN_ENGINE_thi_TINH_LAI(db, kho, tmp_path, asr_gia, dem_engine, monkeypatch):
    from apps.auto_scan_video import tach_tieng

    r1, r2 = _hai_lan_chay(db, kho, tmp_path)
    monkeypatch.setattr(tach_tieng, "PHIEN_BAN_TACH", tach_tieng.PHIEN_BAN_TACH + 1)
    for t in BA:
        _chay(db, r2, t)
    assert dem_engine["audio_prepare"] == 2


def test_artifact_cho_BI_MAT_thi_TINH_LAI(db, kho, tmp_path, asr_gia, dem_engine):
    r1, r2 = _hai_lan_chay(db, kho, tmp_path)
    for k in _gd(db, r1, "audio_prepare").outputs["khoa_asset"]:
        kho.delete(k)
    for t in BA:
        _chay(db, r2, t)
    assert dem_engine["audio_prepare"] == 2
    assert _gd(db, r2, "audio_prepare").status == "succeeded"


def test_lan_THU_LAI_chu_dong_KHONG_dung_cache_chung(db, kho, tmp_path, asr_gia, dem_engine):
    """Khach bam "thu lai" la khach khong tin ket qua — tra lai dung no la lam ngo."""
    r1, r2 = _hai_lan_chay(db, kho, tmp_path)
    _chay(db, r2, "media_prepare")
    gd = _gd(db, r2, "audio_prepare")
    gd.attempt = 2
    db.commit()
    _chay(db, r2, "audio_prepare")
    assert dem_engine["audio_prepare"] == 2


def _phan_vai_ra(monkeypatch, trang_thai):
    from apps.auto_scan_video import ban_ghi, giai_doan_chep_loi

    monkeypatch.setattr(giai_doan_chep_loi, "phan_vai", lambda duong, ban, **kw:
                        ban_ghi.danh_dau_phan_vai(ban, trang_thai))


@pytest.mark.parametrize("trang_thai,so_lan", [("da_chay", 1), ("khong_kha_dung", 2)])
def test_ban_chep_loi_SUY_GIAM_phan_vai_KHONG_duoc_cho(db, kho, tmp_path, asr_gia, dem_engine,
                                                    monkeypatch, trang_thai, so_lan):
    """🔴 Mot su co tam thoi hom qua khong duoc thanh ket qua vinh vien hom nay.

    ⭐ Hai ve cung duong: phan vai CHAY DUOC thi dung lai (1 lan engine); phan
       vai KHONG KHA DUNG thi tinh lai (2 lan). Va khoa phai TRUNG o ca hai — de
       ly do duy nhat cua lan tinh lai la chot suy giam, khong phai khoa lech.
    """
    _phan_vai_ra(monkeypatch, trang_thai)
    r1, r2 = _hai_lan_chay(db, kho, tmp_path, chung={"che_do_giong": "AUTO_MATCH"})
    assert dem_engine["transcribe"] == 1
    for t in BA:
        _chay(db, r2, t)
    assert (_gd(db, r1, "transcribe").outputs["khoa_chung"]
            == _gd(db, r2, "transcribe").outputs["khoa_chung"])
    assert dem_engine["transcribe"] == so_lan


# ══ 3. Khoa: dia chi noi dung ═══════════════════════════════════════════════

def test_giai_doan_KHONG_chia_se_khong_co_khoa(db, kho, tmp_path, asr_gia):
    from apps.auto_scan_video import cache_chung, pipeline

    r = _run(db, _nguon(kho, tmp_path))
    _chay(db, r, "media_prepare")
    assert cache_chung.khoa(db, r, pipeline.AUDIO_PREPARE, engine="e")
    khac = [g.ten for g in pipeline.CHUOI if g.ten not in cache_chung.GIAI_DOAN_CHUNG]
    assert len(khac) == len(pipeline.CHUOI) - 2
    for t in khac:
        assert cache_chung.khoa(db, r, t, engine="e") == "", t


def test_thieu_checksum_nguon_thi_KHONG_co_khoa(db, kho, tmp_path):
    """Fail-closed: khong biet noi dung la gi thi khong dung chung gi ca."""
    from apps.auto_scan_video import cache_chung, pipeline

    r = _run(db, _nguon(kho, tmp_path))
    assert cache_chung.khoa(db, r, pipeline.AUDIO_PREPARE, engine="e") == ""
    assert cache_chung.khoa(db, r, pipeline.TRANSCRIBE, engine="e") == ""


def _thuoc_tinh_cua_cai_dat(duong: Path) -> set[str]:
    """Moi `X.<thuoc_tinh>` voi X la mot bien gan tu `cd.doc(...)`, hoac chinh
    `cd.doc(...).<thuoc_tinh>`."""
    cay = ast.parse(duong.read_text(encoding="utf-8"))

    def la_doc(n):
        return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "doc" and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "cd")
    bien = {t.id for n in ast.walk(cay) if isinstance(n, ast.Assign) and la_doc(n.value)
            for t in n.targets if isinstance(t, ast.Name)}
    return {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)
            and (la_doc(n.value) or (isinstance(n.value, ast.Name) and n.value.id in bien))}


def test_chep_loi_CHI_doc_nhung_thiet_lap_NAM_TRONG_khoa():
    """🔑 Them mot phep doc `cd.doc(run)` vao `transcribe` ma quen them vao khoa
       thi cache chung se giao ban chep loi sai — va khong gi bao loi.
    """
    doc = _thuoc_tinh_cua_cai_dat(GOC / "apps/auto_scan_video/giai_doan_chep_loi.py")
    assert doc, "bo phan tich khong thay phep doc thiet lap nao — xanh rong"
    assert doc <= {"ngon_ngu_nguon", "che_do_giong"}, doc


def test_tach_nguon_KHONG_doc_thiet_lap_nao():
    van = (GOC / "apps/auto_scan_video/giai_doan_am_thanh.py").read_text(encoding="utf-8")
    assert not _thuoc_tinh_cua_cai_dat(GOC / "apps/auto_scan_video/giai_doan_am_thanh.py")
    assert ".settings" not in van and "cai_dat" not in van
