"""`restore.ps1` phai nang luoc do sau khi nap dump - lo hong tim ra o dien tap D1.

Ngay 23/09/2026, duong dien tap khoi phuc do duoc: dump trong ban sao 02:30 mang
`alembic_version = e4a19c07b5d2` trong khi ma dang chay o `5e1a9c46b2d7` - lech dung
3 migration. Do KHONG phai loi cua ban sao: migration chi ap luc deploy, con backup
chay luc 02:30, nen mot ban sao binh thuong van luon co the cu hon ma.

Loi that nam o `restore.ps1`: duong khoi phuc THAT khong co buoc `alembic upgrade
head`. Bo buoc do thi dich vu khoi dong lai tren mot CSDL cu hon ma - cot moi khong
ton tai, va loi hien ra hang gio sau khi da bao "khoi phuc thanh cong".

Doc TINH tren ma nguon, khong chay PowerShell (cung khuon test_2200 / test_2507).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

KICH_BAN = Path(__file__).resolve().parents[1] / "deploy" / "windows" / "restore.ps1"


@pytest.fixture(scope="module")
def ma() -> str:
    return KICH_BAN.read_text(encoding="ascii")


def test_thuan_ascii_va_khong_bom():
    raw = KICH_BAN.read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", "tep co BOM"
    xau = [i for i, b in enumerate(raw) if b > 127]
    assert not xau, f"co {len(xau)} byte ngoai ASCII, vi tri dau: {xau[:5]}"


def test_co_buoc_alembic_upgrade_head(ma: str):
    assert "alembic upgrade head" in ma, "duong khoi phuc that thieu buoc nang luoc do"


def test_alembic_chay_SAU_pg_restore(ma: str):
    """Thu tu quan trong: nang luoc do trUOC khi co du lieu la vo nghia."""
    i_restore = ma.index("pg_restore.exe") if "pg_restore.exe" in ma else -1
    i_goi = ma.index("-m alembic upgrade head")
    i_ok = ma.index("[OK] pg_restore")
    assert i_restore != -1
    assert i_ok < i_goi, "alembic phai chay SAU khi pg_restore bao OK"


def test_alembic_chay_TRUOC_khi_bat_dich_vu(ma: str):
    """Bat dich vu tren CSDL cu hon ma la dung thu loi nay sinh ra de chan."""
    i_goi = ma.index("-m alembic upgrade head")
    i_start = ma.index("Start-Service $ServiceName", i_goi - 4000 if i_goi > 4000 else 0)
    # Lay lan xuat hien Start-Service CUOI CUNG (buoc bat lai dich vu o cuoi tep).
    i_start = ma.rindex("Start-Service $ServiceName")
    assert i_goi < i_start, "alembic phai chay TRUOC Start-Service"


def test_alembic_hong_thi_NEM_chu_khong_di_tiep(ma: str):
    """Nang that bai ma van bat dich vu = khoi phuc nua voi, im lang."""
    sau = ma[ma.index("-m alembic upgrade head"):]
    khoi = sau[:800]
    assert "throw" in khoi, "alembic that bai ma khong nem"
    assert re.search(r"\$rcAl\s+-ne\s+0", khoi), "khong kiem ma thoat cua alembic"


def test_chay_tu_thu_muc_app(ma: str):
    """`alembic.ini` nam trong C:\\LTTPlatform\\app - chay sai thu muc la khong thay."""
    sau = ma[:ma.index("-m alembic upgrade head")]
    assert "Push-Location $Root\\app" in sau, "khong chuyen vao thu muc app truoc khi goi alembic"


def test_duong_dien_tap_khong_bi_dong_cham(ma: str):
    """Nhanh khong -Live van chi giai nen roi thoat - khong duoc chay alembic."""
    i_thoat = ma.index("Live data was NOT modified")
    i_goi = ma.index("-m alembic upgrade head")
    assert i_thoat < i_goi, "nhanh dien tap phai thoat TRUOC khi toi buoc alembic"
