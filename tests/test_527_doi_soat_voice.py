"""Công cụ đối soát sổ cái hợp nhất Voice — INV-CHU-1 (spec §5, §6.5).

⛔ KHÔNG khẳng định "kho thật có 0 commit chưa đối soát": con số ấy phụ thuộc
   nhánh của phiên KHÁC, và một test phụ thuộc trạng thái ngoài là test đỏ vì
   người khác. Kho thật được đo ở Task 16, bằng tay, không bằng pytest.
"""
from __future__ import annotations

import json
import pathlib
import subprocess

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap_cong_cu():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "doi_soat_voice", GOC / "tools" / "doi_soat_voice.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def kho(tmp_path):
    r = tmp_path / "kho"
    r.mkdir()
    _git(r, "init", "-q", "-b", "trunk")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "apps" / "ltt_voice").mkdir(parents=True)
    (r / "khac").mkdir()
    (r / "apps" / "ltt_voice" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "goc")
    _git(r, "checkout", "-q", "-b", "nhanh-voice")
    (r / "apps" / "ltt_voice" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _git(r, "commit", "-q", "-am", "sua voice")
    sha_voice = _git(r, "rev-parse", "HEAD")
    _git(r, "checkout", "-q", "trunk")
    _git(r, "checkout", "-q", "-b", "nhanh-khac")
    (r / "khac" / "b.txt").write_text("b\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "khong phai voice")
    _git(r, "checkout", "-q", "trunk")
    return r, sha_voice


def _so(nguon=()):
    return {"phien_ban": 1, "trunk": "trunk",
            "rc": {"nhanh": "rc", "goc": "0" * 40},
            "vung": ["apps/ltt_voice"],
            "nguon": list(nguon), "yeu_cau": [], "cap_phat_test": {}}


def test_bat_duoc_commit_vung_voice_chua_co_dong(kho):
    m = _nap_cong_cu()
    r, sha = kho
    ra = m.commit_chua_doi_soat(_so(), goc=r, trunk="trunk")
    assert [x["sha"] for x in ra] == [sha], ra
    assert ra[0]["nhanh"] == "nhanh-voice"


def test_commit_da_co_dong_thi_khong_bao(kho):
    m = _nap_cong_cu()
    r, sha = kho
    dong = {"sha": sha[:8], "nhanh": "nhanh-voice", "hang_muc": "x",
            "ket_cuc": "DROP", "ly_do": "T-03", "rc_sha": "", "test": ""}
    assert m.commit_chua_doi_soat(_so([dong]), goc=r, trunk="trunk") == []


def test_commit_ngoai_vung_KHONG_bi_dem(kho):
    m = _nap_cong_cu()
    r, _ = kho
    ra = m.commit_chua_doi_soat(_so(), goc=r, trunk="trunk")
    assert all(x["nhanh"] != "nhanh-khac" for x in ra)


@pytest.mark.parametrize("hong, can", [
    ({"ket_cuc": "MAYBE"}, "ket_cuc"),
    ({"ly_do": ""}, "ly_do"),
    ({"sha": "abc"}, "sha"),
])
def test_hinh_dang_sai_thi_noi_ra(hong, can):
    m = _nap_cong_cu()
    dong = {"sha": "a" * 8, "nhanh": "n", "hang_muc": "x", "ket_cuc": "KEEP",
            "ly_do": "D002", "rc_sha": "", "test": ""}
    dong.update(hong)
    loi = m.kiem_hinh_dang(_so([dong]))
    assert any(can in s for s in loi), loi


def test_so_cai_THAT_dung_hinh_dang():
    m = _nap_cong_cu()
    so = m.nap_so_cai(GOC / "docs" / "LTT_VOICE" / "HOP_NHAT" / "SO_CAI.json")
    assert m.kiem_hinh_dang(so) == []
    # Đối chứng: sổ cái thật phải chứa đủ 9 commit nguồn của spec §1.3.
    co = {d["sha"][:8] for d in so["nguon"]}
    for sha in ("65e099af", "0915f1f3", "29ac2300", "27baa1a8", "31878cc2",
                "dca96e84", "ca6a00ce", "a3a2a46e", "3634412a"):
        assert sha in co, sha
