"""Chot cho `deploy/windows/dong_bo_off_site.ps1` - dong bo ban sao luu off-site.

Vi sao co tep nay: ngay 23/09/2026 dien tap khoi phuc chung minh ban sao luu dung
duoc, nhung toan bo ban sao nam tren CHINH may production. Dong bo off-site vi the
la lop phong thu cuoi cung - va no co MOT cach hong rat de xay ra ma rat kho thay:
day luon ca ban secrets len cung mot tai khoan dam may voi ban du lieu, tu tay go
bo lop tach biet ma `backup.ps1` (H35.9) dung nen.

Cac phep o day doc TINH tren ma nguon, khong chay PowerShell - cung khuon voi
`test_2200_dien_tap_khoi_phuc.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

KICH_BAN = Path(__file__).resolve().parents[1] / "deploy" / "windows" / "dong_bo_off_site.ps1"


@pytest.fixture(scope="module")
def ma() -> str:
    return KICH_BAN.read_text(encoding="ascii")


def test_kich_ban_ton_tai():
    assert KICH_BAN.is_file(), f"khong thay {KICH_BAN}"


def test_thuan_ascii_va_khong_bom():
    """Luat kho: .ps1 phai thuan ASCII, cau hinh khong BOM (AGENTS.md muc 5)."""
    raw = KICH_BAN.read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", "tep co BOM"
    xau = [i for i, b in enumerate(raw) if b > 127]
    assert not xau, f"co {len(xau)} byte ngoai ASCII, vi tri dau: {xau[:5]}"


def test_tu_choi_dong_bo_secrets(ma: str):
    """Chot quan trong nhat: nguon HOAC dich trong nhu secrets thi phai TU CHOI."""
    assert re.search(r"\$Nguon\s+-match\s+'\(\?i\)secret'", ma), \
        "thieu chot tu choi -Nguon la thu muc secrets"
    assert re.search(r"\$Dich\s+-match\s+'\(\?i\)secret'", ma), \
        "thieu chot tu choi -Dich la thu muc secrets"
    # Chot phai NEM, khong phai chi canh bao roi chay tiep.
    for khoi in re.findall(r"-match\s+'\(\?i\)secret'\s*\)\s*\{(.+?)\}", ma, re.S):
        assert "throw" in khoi, f"chot secrets khong nem: {khoi.strip()[:60]}"


def test_chi_nhan_mau_ten_ban_du_lieu(ma: str):
    """Chi dong bo `ltt_data_*.zip` - dung mau ten cua backup.ps1."""
    assert "ltt_data_*.zip" in ma
    assert "ltt_secrets_*" not in ma.split(".DESCRIPTION")[1].split("#>")[1], \
        "phan than kich ban khong duoc nhac toi mau ten secrets"


def test_doi_chieu_bam_sau_khi_chep(ma: str):
    """Chep xong phai doi chieu SHA-256; lech thi XOA ban hong o dich.

    Khong doi chieu thi ta chi biet "co mot tep o do", khong biet no con doc duoc
    khong - dung thu kho phat hien nhat: ban sao im lang hong.
    """
    assert ma.count("Get-FileHash") >= 2, "phai bam ca ban nguon lan ban dich"
    assert "bam LECH" in ma, "thieu nhanh xu ly khi bam lech"
    khoi_lech = ma.split("bamNguon -ne $bamDich")[1][:400]
    assert "Remove-Item" in khoi_lech, "bam lech ma khong xoa ban hong o dich"


def test_co_don_ban_cu_theo_tran_giu(ma: str):
    assert "-Skip $Giu" in ma, "thieu buoc don ban cu vuot tran -Giu"


def test_ma_thoat_khac_khong_khi_co_loi(ma: str):
    """Cam lich chay ma khong biet no hong: co loi phai thoat khac 0."""
    assert re.search(r"\$ketQua\.loi\.Count\s+-gt\s+0\s*\)\s*\{\s*exit\s+1", ma), \
        "co loi ma van thoat 0 thi lich chay se bao xanh vinh vien"


def test_co_che_do_chay_thu(ma: str):
    """Phai chay thu duoc truoc khi dong vao lich."""
    assert "[switch]$ChayThu" in ma
