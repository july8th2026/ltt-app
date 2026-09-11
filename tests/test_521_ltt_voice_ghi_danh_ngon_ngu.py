"""D003/D004 — nguồn gốc làn của giọng nhân bản, và luật sửa làn."""
from __future__ import annotations

import pytest

from apps.ltt_voice import giong_vong_doi as V
from apps.ltt_voice import lan_ngon_ngu as L


@pytest.mark.parametrize("tu, den, duoc", [
    ("dang_ghi_danh", "active", True), ("dang_ghi_danh", "loi", True),
    ("dang_ghi_danh", "revoked", False),          # T-07: chặn thu hồi khi đang ghi danh
    ("active", "revoked", True), ("disabled", "revoked", True),
    ("revoked", "active", False), ("revoked", "disabled", False),  # INV-THU-HOI-1
    ("loi", "revoked", True), ("loi", "active", False),
])
def test_bang_chuyen_trang_thai(tu, den, duoc):
    assert V.co_the_chuyen(tu, den) is duoc


def test_khai_lan_la_hoac_rong_bi_tu_choi():
    for x in ("", "auto", "fr", "VN"):
        assert V.khai_lan_hop_le(x, lan_hien="vi", nguon_hien=V.NGUON_KHAI_BAO) \
            == "voice_language_required"


def test_khai_nguoc_PHEP_DO_bi_tu_choi_trung_thi_duoc():
    assert V.khai_lan_hop_le("en", lan_hien="vi", nguon_hien=V.NGUON_DO_ASR) \
        == "voice_language_measured"
    assert V.khai_lan_hop_le("vi", lan_hien="vi", nguon_hien=V.NGUON_DO_ASR) == ""


def test_khai_bao_va_mac_dinh_cu_sua_tu_do():
    for nguon in (V.NGUON_KHAI_BAO, V.NGUON_MAC_DINH_CU):
        assert V.khai_lan_hop_le("en", lan_hien="vi", nguon_hien=nguon) == ""


def test_lan_hop_le_lay_tu_tham_quyen():
    assert set(L.LAN_HOP_LE) == {"vi", "en"}


def test_migration_mot_head_va_danh_dau_dong_cu():
    import pathlib, re
    goc = pathlib.Path(__file__).resolve().parents[1]
    m = (goc / "alembic" / "versions" / "20260911_1000_voice_ngon_ngu_nguon.py").read_text(encoding="utf-8")
    assert re.search(r'down_revision\s*=\s*"d15b8c30f7a4"', m)
    assert "mac_dinh_cu" in m
    # Migration KHÔNG được gán lại `ngon_ngu` của dòng cũ (spec §6.2).
    assert not re.search(r"ngon_ngu\s*=\s*'", m.replace("ngon_ngu_nguon", ""))
