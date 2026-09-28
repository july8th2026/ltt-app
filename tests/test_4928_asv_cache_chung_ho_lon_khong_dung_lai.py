"""B13 B5 phu (dieu phoi 29/09) — CUA cache_chung: ban chep co HO LON (CUA B
cua `ban_ghi.do_phu_song`) KHONG duoc dung lai qua `cache_chung.lay()` cho
mot run khac.

⛔ Day la CUA HEP: chi doc `outputs["phu_song_kiem"]["canh_bao_lo_hong"]` ma
CHI transcribe dat. Hai phep kiem o day chot CA HAI chieu — thieu vi doi
chung thu hai thi mot ban va TAT CACHE TOAN HE cung se xanh (dieu phoi da
canh bao dung dieu do).

⛔ Day la chan DOC (an toan, dao nguoc duoc), KHONG phai chan GHI: ban chep
HO LON van duoc `promote_va_ghi` luu binh thuong — no van la ket qua THAT
cua chinh run do.
"""
from __future__ import annotations

import io
from pathlib import Path

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests import test_403_asv_vong_doi_artifact as _t403
from tests.conftest import bao_dam_user

db, kho, asr_gia = _t403.db, _t403.kho, _t403.asr_gia

BA = ("media_prepare", "audio_prepare", "transcribe")


def _nguon(kho, tmp_path, *, owner="uA", ten="a", duration_s=3.0, chep_tu=None):
    """Tep nguon trong kho. `chep_tu` = CUNG BYTE, KHAC KHOA (khach tai lai)."""
    from tests.fixtures.asv_media import tiny_mp4

    khoa = f"asv/{owner}/nguon-{ten}/nguon.mp4"
    if chep_tu:
        with kho.open(chep_tu) as f:
            du_lieu = f.read()
    else:
        du_lieu = tiny_mp4(tmp_path / f"{ten}.mp4", duration_s=duration_s).read_bytes()
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


def _ban_ghi_ho_lon() -> dict:
    """Ban ghi RAW co MOT ho 20s giua hai doan tren nguon 40s — vuot
    `ban_ghi.NGUONG_LO_HONG_S` (15,0), kich `canh_bao_lo_hong` THAT qua
    `do_phu_song()` THAT (⛔ khong gia lap con so, chi gia lap ENGINE)."""
    # `en`, KHONG `vi`: dich mac dinh la `vi`, va hop dong ngon ngu (22/09) tu
    # choi nguon TRUNG dich (`ngon_ngu.kiem_nguon_da_doan`, cung khuon
    # `tests/fixtures/asv_media.ban_ghi_gia`).
    return {"segments": [
        {"start": 0.0, "end": 2.0, "text": "first line",
         "words": [{"start": 0.0, "end": 2.0, "text": "first"}]},
        {"start": 22.0, "end": 24.0, "text": "last line",
         "words": [{"start": 22.0, "end": 24.0, "text": "last"}]},
    ], "language": "en", "engine": "gia", "alignment_status": "aligned",
        "fallback_reason": "", "tham_so": {}}


def test_4928_ban_chep_HO_LON_KHONG_duoc_dung_lai_qua_cache_chung(
        db, kho, tmp_path, monkeypatch):
    """Kich ban that qua `giai_doan_chep_loi.chay()` THAT (khong gia lap
    `do_phu_song`): r1 chep ra mot ban co ho 20s -> `canh_bao_lo_hong=True`.
    r2 CUNG NOI DUNG nguon (`chep_tu=k1`) -> CUNG `khoa_chung` cho
    transcribe. Neu cache_chung dung lai ban cua r1 thi engine se KHONG
    duoc goi lai cho r2 — ta chot NGUOC LAI: engine PHAI chay lai."""
    from apps.auto_scan_video import giai_doan_chep_loi

    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: _ban_ghi_ho_lon())

    k1 = _nguon(kho, tmp_path, ten="a", duration_s=40.0)
    r1 = _run(db, k1)
    for t in BA:
        _chay(db, r1, t)
    gd1 = _gd(db, r1, "transcribe")
    assert gd1.status == "succeeded", f"transcribe r1: {gd1.status} {gd1.error}"
    assert gd1.outputs["phu_song_kiem"]["canh_bao_lo_hong"] is True, (
        "fixture phai THAT SU kich CUA B — neu khong phep kiem nay khong "
        "kiem duoc gi ca (doi chung ao)")

    goi = {"n": 0}
    that = giai_doan_chep_loi.chay

    def dem(*a, **kw):
        goi["n"] += 1
        return that(*a, **kw)
    monkeypatch.setattr(giai_doan_chep_loi, "chay", dem)

    k2 = _nguon(kho, tmp_path, ten="b", duration_s=40.0, chep_tu=k1)
    r2 = _run(db, k2)
    for t in BA:
        _chay(db, r2, t)

    assert goi["n"] == 1, (
        "transcribe cua r2 KHONG goi engine lai -> cache_chung da dung lai "
        "BAN CUT cua r1, dung dieu bo dem chan phai ngan")
    gd2 = _gd(db, r2, "transcribe")
    assert gd2.status == "succeeded", f"transcribe r2: {gd2.status} {gd2.error}"
    assert gd2.outputs.get("tu_cache_chung") is not True


def test_4928_DOI_CHUNG_giai_doan_KHONG_co_phu_song_kiem_VAN_dung_lai_duoc(
        db, kho, tmp_path, asr_gia, monkeypatch):
    """🔴 Doi chung BAT BUOC, chieu NGUOC: `audio_prepare` — giai doan CHUNG
    duy nhat con lai, KHONG mang `phu_song_kiem` trong outputs — PHAI van
    dung lai duoc binh thuong. Thieu phep kiem nay thi mot ban va TAT CACHE
    CHO CA HE THONG (khong chi transcribe) cung se xanh."""
    from apps.auto_scan_video import giai_doan_am_thanh

    k1 = _nguon(kho, tmp_path, ten="a")
    r1 = _run(db, k1)
    for t in BA:
        _chay(db, r1, t)
    gd1 = _gd(db, r1, "audio_prepare")
    assert gd1.status == "succeeded"
    assert "phu_song_kiem" not in (gd1.outputs or {}), (
        "audio_prepare KHONG duoc mang khoa nay — neu co, doi chung nay sai tien de")

    goi = {"n": 0}
    that = giai_doan_am_thanh.chay

    def dem(*a, **kw):
        goi["n"] += 1
        return that(*a, **kw)
    monkeypatch.setattr(giai_doan_am_thanh, "chay", dem)

    k2 = _nguon(kho, tmp_path, ten="b", chep_tu=k1)
    r2 = _run(db, k2)
    for t in BA:
        _chay(db, r2, t)

    assert goi["n"] == 0, (
        "audio_prepare KHONG mang phu_song_kiem -> PHAI dung lai duoc; "
        "goi engine lai nghia la mot ban va da lam TAT CACHE toan he")
    gd2 = _gd(db, r2, "audio_prepare")
    assert gd2.outputs.get("tu_cache_chung") is True


def test_4928_ham_dem_thuan_khong_can_DB(monkeypatch):
    """Phep kiem DON VI (khong DB/kho) cho `_ho_lon_khong_dung_lai` — chot
    cong thuc doc dung DUONG DAN khoa, va vang khoa (giai doan khac) tra ve
    False chu khong nem loi."""
    from apps.auto_scan_video import cache_chung

    assert cache_chung._ho_lon_khong_dung_lai(
        {"phu_song_kiem": {"canh_bao_lo_hong": True}}) is True
    assert cache_chung._ho_lon_khong_dung_lai(
        {"phu_song_kiem": {"canh_bao_lo_hong": False}}) is False
    assert cache_chung._ho_lon_khong_dung_lai({}) is False
    assert cache_chung._ho_lon_khong_dung_lai(
        {"phu_song_kiem": None}) is False
    assert cache_chung._ho_lon_khong_dung_lai(
        {"stage": "audio_prepare", "khoa_asset": ["x"]}) is False
