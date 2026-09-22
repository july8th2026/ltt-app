"""asv-final L_TAI_LEN — tai len nhieu phan qua HTTP THAT cua app (kho cuc bo).

Menh de chinh: tai dut giua chung TIEP TUC tu phan dang do, khong tu 0.
Kem theo: nguoi khac khong tiep tuc duoc, MD5 sai bi tu choi, ghep ra dung
tung byte (sha256), va ghep khi thieu phan bi tu choi.

`CO_PHAN` duoc thu nho bang monkeypatch (64 KiB) de bo test khong day 16 MiB
moi phan. Kho cuc bo khong co san 5 MiB nen ngu nghia khong doi.
"""
from __future__ import annotations

import base64
import hashlib
import os

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

GOC = "/auto-scan-video/tai-len"
CO = 64 * 1024


@pytest.fixture()
def mt(moi_truong, monkeypatch):
    from apps.auto_scan_video import tai_len
    monkeypatch.setattr(tai_len, "CO_PHAN", CO)
    return moi_truong


def _md5(b: bytes) -> str:
    return base64.b64encode(hashlib.md5(b).digest()).decode()


def _video(n_byte: int) -> bytes:
    # Chu ky mp4 (`ftyp` o byte 4..8) de `upload_sessions.confirm` nhan.
    dau = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
    return dau + os.urandom(n_byte - len(dau))


def _bat_dau(c, csrf, tep: bytes):
    r = c.post(GOC, data={"csrf_token": csrf, "ten_tep": "a.mp4",
                          "kieu": "video/mp4", "co": str(len(tep))})
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _gui_phan(c, csrf, uid, so, than: bytes, md5: str | None = None):
    ve = c.post(f"{GOC}/{uid}/phan/{so}/ve",
                data={"csrf_token": csrf, "md5": md5 or _md5(than)})
    assert ve.status_code == 200, ve.text[:300]
    v = ve.json()
    assert v["method"] == "PUT" and v["url"].startswith(GOC)
    return c.put(v["url"], content=than, headers=v["headers"])


def _cat(tep: bytes, so: int) -> bytes:
    return tep[(so - 1) * CO: so * CO]


def test_dut_o_73_phan_tram_roi_TIEP_TUC_tu_73_va_ghep_dung_byte(mt):
    _app, a, csrf, _b, _cb = mt
    tep = _video(11 * CO - 5000)                  # 11 phan, phan cuoi le
    mo_ta = _bat_dau(a, csrf, tep)
    uid, n = mo_ta["upload_id"], mo_ta["so_phan"]
    assert n == 11 and mo_ta["co_phan"] == CO and mo_ta["da_co"] == []

    # Gui 8/11 phan (~73%) roi "dut mang".
    for so in range(1, 9):
        assert _gui_phan(a, csrf, uid, so, _cat(tep, so)).status_code == 204

    # Lan sau: hoi may chu — chi phan 9..11 con thieu.
    tt = a.get(f"{GOC}/{uid}").json()
    assert tt["da_co"] == list(range(1, 9))
    da = sum(len(_cat(tep, s)) for s in tt["da_co"])
    assert 0.70 <= da / len(tep) <= 0.76
    for so in range(1, n + 1):
        if so not in tt["da_co"]:
            assert _gui_phan(a, csrf, uid, so, _cat(tep, so)).status_code == 204

    r = a.post(f"{GOC}/{uid}/xong", data={"csrf_token": csrf})
    assert r.status_code == 200, r.text[:300]
    assert r.json()["xong"] is True

    from platform_core.storage import get_storage
    from platform_core import upload_sessions
    import platform_core.db as dbmod
    db = next(dbmod.get_session())
    try:
        s = db.get(upload_sessions.UploadSession, uid)
        assert s.status == "ready" and s.actual_size == len(tep)
        with get_storage().open(s.staging_key) as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == hashlib.sha256(tep).hexdigest()
    finally:
        db.close()

    # Goi `xong` lan hai (phan hoi lan truoc bi dut): cung ket qua, khong loi.
    assert a.post(f"{GOC}/{uid}/xong", data={"csrf_token": csrf}).status_code == 200


def test_NGUOI_KHAC_khong_tiep_tuc_duoc_luot_tai(mt):
    _app, a, csrf_a, b, csrf_b = mt
    tep = _video(3 * CO)
    uid = _bat_dau(a, csrf_a, tep)["upload_id"]
    assert _gui_phan(a, csrf_a, uid, 1, _cat(tep, 1)).status_code == 204

    assert b.get(f"{GOC}/{uid}").status_code == 404
    assert b.post(f"{GOC}/{uid}/phan/2/ve",
                  data={"csrf_token": csrf_b, "md5": _md5(_cat(tep, 2))}).status_code == 404
    r = b.put(f"{GOC}/{uid}/phan/2", content=_cat(tep, 2),
              headers={"Content-MD5": _md5(_cat(tep, 2)), "X-CSRF-Token": csrf_b})
    assert r.status_code == 404
    assert b.post(f"{GOC}/{uid}/xong", data={"csrf_token": csrf_b}).status_code == 404
    assert b.post(f"{GOC}/{uid}/huy", data={"csrf_token": csrf_b}).status_code == 404
    # Luot cua A con nguyen.
    assert a.get(f"{GOC}/{uid}").json()["da_co"] == [1]


def test_phan_MD5_KHONG_KHOP_bi_tu_choi_va_khong_duoc_tinh(mt):
    _app, a, csrf, _b, _cb = mt
    tep = _video(2 * CO)
    uid = _bat_dau(a, csrf, tep)["upload_id"]
    hong = bytearray(_cat(tep, 1)); hong[100] ^= 0xFF
    r = _gui_phan(a, csrf, uid, 1, bytes(hong), md5=_md5(_cat(tep, 1)))
    assert r.status_code == 400
    assert a.get(f"{GOC}/{uid}").json()["da_co"] == []


def test_phan_SAI_KICH_THUOC_bi_tu_choi(mt):
    _app, a, csrf, _b, _cb = mt
    tep = _video(2 * CO)
    uid = _bat_dau(a, csrf, tep)["upload_id"]
    ngan = _cat(tep, 1)[:-1]
    assert _gui_phan(a, csrf, uid, 1, ngan).status_code == 400
    assert a.get(f"{GOC}/{uid}").json()["da_co"] == []


def test_ghep_khi_THIEU_phan_bi_tu_choi(mt):
    _app, a, csrf, _b, _cb = mt
    tep = _video(3 * CO)
    uid = _bat_dau(a, csrf, tep)["upload_id"]
    _gui_phan(a, csrf, uid, 1, _cat(tep, 1))
    _gui_phan(a, csrf, uid, 3, _cat(tep, 3))
    assert a.post(f"{GOC}/{uid}/xong", data={"csrf_token": csrf}).status_code == 400


def test_moi_route_ghi_doi_CSRF(mt):
    _app, a, csrf, _b, _cb = mt
    tep = _video(2 * CO)
    assert a.post(GOC, data={"csrf_token": "sai", "ten_tep": "a.mp4",
                             "kieu": "video/mp4", "co": str(len(tep))}).status_code == 400
    uid = _bat_dau(a, csrf, tep)["upload_id"]
    p1 = _cat(tep, 1)
    assert a.post(f"{GOC}/{uid}/phan/1/ve",
                  data={"csrf_token": "sai", "md5": _md5(p1)}).status_code == 400
    assert a.put(f"{GOC}/{uid}/phan/1", content=p1,
                 headers={"Content-MD5": _md5(p1)}).status_code == 400
    assert a.post(f"{GOC}/{uid}/xong", data={"csrf_token": "sai"}).status_code == 400


def test_so_phan_ngoai_ke_hoach_va_tep_qua_tran_bi_tu_choi(mt):
    _app, a, csrf, _b, _cb = mt
    tep = _video(2 * CO)
    uid = _bat_dau(a, csrf, tep)["upload_id"]
    for so in (0, 3):
        r = a.post(f"{GOC}/{uid}/phan/{so}/ve", data={"csrf_token": csrf, "md5": _md5(b"x")})
        assert r.status_code == 400
    from apps.auto_scan_video import tai_len
    r = a.post(GOC, data={"csrf_token": csrf, "ten_tep": "a.mp4", "kieu": "video/mp4",
                          "co": str(tai_len.TRAN_BYTE + 1)})
    assert r.status_code == 400


def test_huy_bo_luot_va_don_phan_ngay(mt):
    _app, a, csrf, _b, _cb = mt
    tep = _video(2 * CO)
    uid = _bat_dau(a, csrf, tep)["upload_id"]
    _gui_phan(a, csrf, uid, 1, _cat(tep, 1))
    assert a.post(f"{GOC}/{uid}/huy", data={"csrf_token": csrf}).status_code == 204
    assert a.get(f"{GOC}/{uid}").status_code == 400
    import platform_core.db as dbmod
    from platform_core import upload_sessions
    from platform_core.storage import get_storage
    db = next(dbmod.get_session())
    try:
        s = db.get(upload_sessions.UploadSession, uid)
        assert s.status == "deleted"
        assert not get_storage()._mp_dir(s.staging_key).exists()
    finally:
        db.close()


def test_tran_2GiB_KEP_duoi_int4_cua_cot_expected_size():
    """`upload_sessions.expected_size` la Integer (int4 tren PostgreSQL)."""
    from apps.auto_scan_video import tai_len
    assert tai_len.TRAN_BYTE <= 2 ** 31 - 1
    assert tai_len.so_phan(tai_len.TRAN_BYTE) <= 10000          # tran R2
    assert tai_len.CO_PHAN >= 5 * 1024 * 1024                   # san R2
    assert tai_len.CO_PHAN < 100 * 1000 * 1000                  # tran Cloudflare
