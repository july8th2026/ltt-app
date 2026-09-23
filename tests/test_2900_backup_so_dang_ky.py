"""test_2900 -- so dang ky phat hanh phai nam trong mau sao luu DU LIEU.

Boi canh: dien tap khoi phuc 23/09/2026
(docs/reports/dien-tap-khoi-phuc-2026-09-23.md, cau 4) do ra hai tep nam
NGOAI mau `deploy/windows/backup.ps1` va se mat khi dung may trang:

- `lttcode_releases.json` -- so dang ky phat hanh LTTCODE, ghi boi
  `tools/release.ps1` (kho LTTCODEAPP). Khong dung lai duoc: moi dong chua
  chu ky minisign + SHA-256 cua mot ban da phat hanh.
- `nexus_versions.json` -- so phien ban LTT Nexus, cung loai, sua tay theo
  `platform_core/nexus/versions.py`.

Chot cho lan sua nay: hai tep tren phai co trong mau BAN SAO DU LIEU
(`$BackupDir`, bien `$patterns` cua backup.ps1), va KHONG duoc lot vao mau
BAN SAO SECRETS (H35.9 -- gop chung la loi da sua mot lan). Doc TINH tren
ma nguon, khong chay PowerShell -- cung khuon voi
`tests/test_2507_dong_bo_off_site.py`.

Ghi chu pham vi: `data/translations/` (tep dich giao dien) KHONG nam trong
phep kiem nay. Tra cuu cho thay no la tai nguyen nguon di kem code --
`setup/2-cai-dat.ps1` (muc "Tai nguyen nguon di kem code") robocopy no tu
`$src\\data\\translations` vao `data\\translations` moi lan deploy/update,
nen no sinh lai duoc va khong can dua vao backup.ps1.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

KICH_BAN = Path(__file__).resolve().parents[1] / "deploy" / "windows" / "backup.ps1"

# Hai tep so dang ky phat hanh phai co trong mau du lieu (khong phai mau
# secrets). Xem docstring o tren.
TEP_SO_DANG_KY = ("lttcode_releases.json", "nexus_versions.json")


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


def _khoi_patterns(ma: str) -> str:
    """Cat rieng dong khai bao `$patterns = @(...)` de doi chieu."""
    khop = re.search(r"\$patterns\s*=\s*@\((.*?)\)", ma, re.S)
    assert khop, "khong tim thay khai bao $patterns trong backup.ps1"
    return khop.group(1)


@pytest.mark.parametrize("ten_tep", TEP_SO_DANG_KY)
def test_co_trong_mau_du_lieu(ma: str, ten_tep: str):
    """Ca hai so dang ky phai co mat trong $patterns (mau BAN SAO DU LIEU)."""
    khoi = _khoi_patterns(ma)
    assert f"'{ten_tep}'" in khoi, (
        f"{ten_tep} chua co trong $patterns cua backup.ps1 -- se mat khi "
        "dung may trang (dien tap 23/09/2026, cau 4)"
    )


def _khoi_secrets(ma: str) -> str:
    """Cat tu `if ($IncludeSecrets)` toi het tep -- vung ghi ra ban sao secrets."""
    vi_tri = ma.find("if ($IncludeSecrets)")
    assert vi_tri != -1, "khong tim thay khoi -IncludeSecrets trong backup.ps1"
    return ma[vi_tri:]


@pytest.mark.parametrize("ten_tep", TEP_SO_DANG_KY)
def test_khong_lot_vao_mau_secrets(ma: str, ten_tep: str):
    """Chot H35.9: hai so dang ky la du lieu, khong duoc xuat hien trong khoi secrets."""
    khoi = _khoi_secrets(ma)
    assert ten_tep not in khoi, (
        f"{ten_tep} xuat hien trong khoi -IncludeSecrets -- day la du lieu, "
        "phai o ban sao DU LIEU rieng voi ban sao secrets (H35.9)"
    )


def test_patterns_van_giu_danh_sach_cu(ma: str):
    """Sua khong duoc lam mat cac mau da co truoc do."""
    khoi = _khoi_patterns(ma)
    for mau_cu in ("config.json", "workers.json", "*.enc", "*.db", "*.sqlite3",
                   "audit_log.jsonl"):
        assert f"'{mau_cu}'" in khoi, f"mau cu bi mat: {mau_cu}"
