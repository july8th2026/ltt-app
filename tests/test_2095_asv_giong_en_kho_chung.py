"""asv-final F-03 — `AUTO_MATCH` dich `en` khop vao KHO CHUNG cua LTT Voice.

**§1** 20/20 giong mau la lan `vi` => dich `en` truoc day LUON `CHUA_RANG`.
       Nay tang 2 doc kho chung (`tham_chieu.ung_vien_kho_chung`) — chi giong
       license `ok`, `active`, `dung_chung`, dung lan, dung gioi.
**§2** Khong co giong mac dinh doi ten (D-V4-04): thieu gioi / thieu phien CSDL /
       khong ai khop => `CHUA_RANG`.
**§3** Duong `vi` KHONG doi: lan co giong mau thi kho chung khong bi hoi.
**§4** Giong da chon DUNG DUOC qua `features.giai_giong` cho mot khach bat ky.
**§5** Be mat khai o CA HAI phia.
"""
from __future__ import annotations

import re
import uuid

import pytest

from apps.auto_scan_video import rang_giong as rg

TU_KHOP = "AUTO_MATCH"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "t2095.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "thu-nghiem-2095")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    phien = next(gen)
    yield phien
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _giong(db, *, gioi="nam", ngon_ngu="en", dung_chung=True, license_status="ok",
           trang_thai="active", owner="nen-tang", pid=None) -> str:
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr
    pid = pid or "vc_" + uuid.uuid4().hex
    p = VoiceProfile(public_id=pid, owner_id=owner, ten_hien_thi=pid[:12],
                     ngon_ngu=ngon_ngu, gioi=gioi, trang_thai=trang_thai,
                     dung_chung=dung_chung, license_status=license_status)
    db.add(p)
    db.flush()
    db.add(VoiceRepr(profile_id=p.id, ref_id=0, engine="vieneu", storage_key="k",
                     fingerprint="vt", trang_thai="dang_dung"))
    db.commit()
    return pid


def _rang(db, gioi="nam", vung="", phong_cach="", dich="en"):
    dd = rg.DacDiemMongMuon(gioi=gioi, vung=vung, phong_cach=phong_cach)
    return rg.rang(db, owner_id="khach-x",
                   yeu_cau=rg.YeuCau(che_do=TU_KHOP, dac_diem=dd, ngon_ngu_dich=dich))


# §1 ─────────────────────────────────────────────────────────────────────────

def test_EN_khop_kho_chung_CHI_giong_du_dieu_kien(db):
    a = _giong(db, pid="vc_" + "b" * 32)
    b = _giong(db, pid="vc_" + "a" * 32)
    # Nhieu: khong duoc lot vao.
    _giong(db, pid="vc_" + "0" * 32, gioi="nu")                      # sai gioi
    _giong(db, pid="vc_" + "1" * 32, ngon_ngu="vi")                  # sai lan
    _giong(db, pid="vc_" + "2" * 32, license_status="cho_soat")      # chua soat
    _giong(db, pid="vc_" + "3" * 32, dung_chung=False, owner="khac") # giong RIENG
    _giong(db, pid="vc_" + "4" * 32, trang_thai="disabled")          # da tat
    _giong(db, pid="vc_" + "5" * 32, gioi="")                        # chua ro gioi

    kq = _rang(db)
    assert kq.da_chot
    assert kq.nguon == rg.NGUON_TU_KHOP
    assert kq.can_cu["loai"] == rg.LOAI_KHO_CHUNG
    assert kq.can_cu["so_ung_vien"] == 2
    assert kq.giong_id == min(a, b), "phai tat dinh theo public_id"


def test_EN_TAT_DINH_hai_lan_cung_mot_giong(db):
    for _ in range(4):
        _giong(db)
    assert _rang(db).giong_id == _rang(db).giong_id


def test_UU_TIEN_theo_so_do_dung_truoc_public_id(db, monkeypatch):
    dau = _giong(db, pid="vc_" + "a" * 32)
    uu = _giong(db, pid="vc_" + "f" * 32)
    monkeypatch.setattr(rg, "UU_TIEN_KHO_CHUNG", ("vc_" + "9" * 32, uu))
    assert _rang(db).giong_id == uu
    monkeypatch.setattr(rg, "UU_TIEN_KHO_CHUNG", ())
    assert _rang(db).giong_id == dau


def test_UU_TIEN_KHONG_vuot_rao_gioi(db, monkeypatch):
    """⛔ Uu tien chi SAP ung vien da khop — khong phai giong mac dinh."""
    nu = _giong(db, gioi="nu")
    monkeypatch.setattr(rg, "UU_TIEN_KHO_CHUNG", (nu,))
    assert not _rang(db, gioi="nam").da_chot


def test_vung_phong_cach_GHI_la_bo_qua_chu_khong_gia_vo_khop(db):
    _giong(db)
    kq = _rang(db, vung="bac", phong_cach="tin_tuc")
    assert kq.da_chot
    assert kq.can_cu["mat_khong_ap_dung"] == ["vung", "phong_cach"]


# §2 ─────────────────────────────────────────────────────────────────────────

def test_EN_thieu_GIOI_thi_CHUA_RANG_khong_lay_ca_lan(db):
    _giong(db)
    kq = _rang(db, gioi="", vung="bac")
    assert not kq.da_chot and kq.giong_id == ""
    with pytest.raises(rg.ChuaRangError):
        kq.ma_giong()


def test_EN_khong_ai_khop_thi_CHUA_RANG(db):
    _giong(db, gioi="nu")
    assert not _rang(db, gioi="nam").da_chot


def test_EN_khong_phien_CSDL_thi_CHUA_RANG():
    assert not _rang(None).da_chot


# §3 ─────────────────────────────────────────────────────────────────────────

def test_VI_KHONG_hoi_kho_chung(db, monkeypatch):
    from apps.ltt_voice import tham_chieu

    def _cam(_db):
        raise AssertionError("lan vi co giong mau — khong duoc hoi kho chung")

    monkeypatch.setattr(tham_chieu, "ung_vien_kho_chung", _cam)
    _giong(db, ngon_ngu="vi")
    kq = _rang(db, gioi="nam", vung="bac", dich="vi")
    assert kq.da_chot and kq.can_cu["loai"] == rg.LOAI_GIONG_MAU
    # Lan vi phu nhung dac diem khong khop => van CHUA_RANG, khong xuong kho chung.
    assert not _rang(db, gioi="nam", phong_cach="khong-co-that", dich="vi").da_chot


# §4 ─────────────────────────────────────────────────────────────────────────

def test_giong_da_chon_GIAI_DUOC_cho_khach_khac_lan_en(db, monkeypatch):
    from apps.ltt_voice import features, tham_chieu
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda bd: "REF")
    _giong(db)
    ma = _rang(db).ma_giong()
    ref, preset, _cb = features.giai_giong(db, features.YeuCau(
        text="The river carried stories.", voice_id=ma, owner_id="khach-x",
        ngon_ngu="en"))
    assert ref == "REF" and preset is None


# §5 ─────────────────────────────────────────────────────────────────────────

def test_be_mat_KHAI_ca_hai_phia():
    import apps.ltt_voice as lv
    from tools import lint_app_contract as lint
    muc = ("apps.ltt_voice.tham_chieu", "ung_vien_kho_chung")
    assert muc in lv.BE_MAT_CONG_KHAI
    assert muc in lint.APP_DUOC_DUNG_APP[("auto_scan_video", "ltt_voice")]


def test_UU_TIEN_la_public_id_hop_le_khong_trung():
    assert len(set(rg.UU_TIEN_KHO_CHUNG)) == len(rg.UU_TIEN_KHO_CHUNG)
    for ma in rg.UU_TIEN_KHO_CHUNG:
        assert re.fullmatch(r"vc_[0-9a-f]{32}", ma), ma
