"""LTTCODE — logic kênh phát hành (spec updater LTTCODEAPP §2).

Hàm thuần `quyet_dinh` là nơi DUY NHẤT quyết định máy nào nhận bản nào: kill
switch, bản bị thu hồi, rollout %, bản tối thiểu (bắt buộc), và chặn phục vụ bản
có định dạng session DSH cũ hơn bản đang chạy (người dùng sẽ không mở được
session của mình).
"""
from __future__ import annotations

import hashlib

from apps.lttcode import phat_hanh

BASE = "https://app.lttstudios.com"
IID = "3f2b8c1e-6a4d-4e2f-9b1a-0c5d7e8f9a10"


def _ban(version, **kw):
    r = {
        "version": version,
        "pub_date": "2026-09-20T10:00:00Z",
        "file": f"LTTCODE_{version}_x64-setup.exe",
        "signature": f"sig-{version}",
        "sha256": "ab" * 32,
        "notes": f"notes {version}",
        "rollout_percent": 100,
        "session_format": 3,
        "revoked": False,
    }
    r.update(kw)
    return r


def _manifest(*releases, channel="stable", **kenh):
    k = {"kill_switch": False, "min_version": "0.0.0", "releases": list(releases)}
    k.update(kenh)
    return {"channels": {channel: k}}


def _hoi(manifest, current="0.1.0", channel="stable", install_id=IID, target="windows", arch="x86_64"):
    return phat_hanh.quyet_dinh(manifest, channel, target, arch, current, install_id, BASE)


def test_co_ban_moi_tra_json_dung_dinh_dang_tauri():
    code, body = _hoi(_manifest(_ban("0.2.0")))
    assert code == 200
    assert body == {
        "version": "0.2.0",
        "notes": "notes 0.2.0",
        "pub_date": "2026-09-20T10:00:00Z",
        "url": "https://app.lttstudios.com/lttcode/dl/LTTCODE_0.2.0_x64-setup.exe",
        "signature": "sig-0.2.0",
        "mandatory": False,
    }


def test_khong_co_ban_moi_hon_tra_204():
    assert _hoi(_manifest(_ban("0.1.0")), current="0.1.0") == (204, None)
    assert _hoi(_manifest(_ban("0.1.0")), current="0.2.0") == (204, None)


def test_chon_ban_cao_nhat_theo_so_khong_theo_chuoi():
    code, body = _hoi(_manifest(_ban("0.9.0"), _ban("0.10.0"), _ban("0.2.0")))
    assert code == 200 and body["version"] == "0.10.0"


def test_kill_switch_tat_moi_cap_nhat_ke_ca_bat_buoc():
    m = _manifest(_ban("0.2.0"), kill_switch=True, min_version="0.2.0")
    assert _hoi(m) == (204, None)


def test_ban_bi_thu_hoi_khong_duoc_phuc_vu():
    code, body = _hoi(_manifest(_ban("0.2.0"), _ban("0.3.0", revoked=True)))
    assert code == 200 and body["version"] == "0.2.0"


def test_khong_day_nguoi_dung_ve_dinh_dang_session_cu_hon():
    m = _manifest(_ban("0.2.0", session_format=4), _ban("0.3.0", session_format=3))
    code, body = _hoi(m, current="0.2.0")
    assert (code, body) == (204, None)
    # Đối chứng: cùng danh sách, máy đang ở bản chưa biết format ⇒ không lọc.
    code, body = _hoi(m, current="0.1.0")
    assert code == 200 and body["version"] == "0.3.0"


def test_duoi_min_version_la_bat_buoc_va_bo_qua_rollout():
    m = _manifest(_ban("0.2.0", rollout_percent=0), min_version="0.2.0")
    code, body = _hoi(m, current="0.1.0", install_id=None)
    assert code == 200 and body["mandatory"] is True


def test_rollout_0_khong_ai_100_tat_ca():
    assert _hoi(_manifest(_ban("0.2.0", rollout_percent=0))) == (204, None)
    assert _hoi(_manifest(_ban("0.2.0", rollout_percent=100)))[0] == 200


def test_trong_nhom_theo_hash_tinh_tay():
    version = "0.2.0"
    bucket = int(hashlib.sha256(f"{IID}:{version}".encode()).hexdigest()[:8], 16) % 100
    assert phat_hanh.trong_nhom(IID, version, bucket + 1) is True
    assert phat_hanh.trong_nhom(IID, version, bucket) is False
    code_in, _ = _hoi(_manifest(_ban(version, rollout_percent=bucket + 1)))
    code_out, _ = _hoi(_manifest(_ban(version, rollout_percent=bucket)))
    assert (code_in, code_out) == (200, 204)


def test_thieu_install_id_chi_nhan_khi_rollout_du_100():
    assert _hoi(_manifest(_ban("0.2.0", rollout_percent=99)), install_id=None) == (204, None)
    assert _hoi(_manifest(_ban("0.2.0", rollout_percent=100)), install_id=None)[0] == 200


def test_tham_so_sai_tra_400_kenh_la_tra_404():
    m = _manifest(_ban("0.2.0"))
    assert _hoi(m, target="darwin")[0] == 400
    assert _hoi(m, arch="aarch64")[0] == 400
    assert _hoi(m, current="1.0")[0] == 400
    assert _hoi(m, current="0.1.0-beta")[0] == 400
    assert _hoi(m, channel="nightly")[0] == 404


def test_manifest_thieu_hoac_hong_tra_204_khong_bao_gio_500():
    assert _hoi(None) == (204, None)
    assert _hoi({"channels": "rac"}) == (204, None)
    assert _hoi({"channels": {"stable": {"releases": [{"version": "x"}, "rac", None]}}}) == (204, None)
    assert _hoi(_manifest(_ban("0.2.0", file="../../secrets/app.env"))) == (204, None)


def test_doc_manifest_tu_thu_muc_du_lieu(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path))
    assert phat_hanh.doc_manifest() is None
    (tmp_path / "lttcode_releases.json").write_text("{hong", encoding="utf-8")
    assert phat_hanh.doc_manifest() is None
    (tmp_path / "lttcode_releases.json").write_text('{"channels": {}}', encoding="utf-8")
    assert phat_hanh.doc_manifest() == {"channels": {}}
