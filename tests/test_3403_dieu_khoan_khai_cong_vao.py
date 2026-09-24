"""Điều khoản phải khai **cổng nào đi VÀO được** — không chỉ cổng ra bị chặn.

🔴 Đo trên production 24/09/2026, ngay sau khi máy thật đầu tiên lên:
   `table ip gwnat` chỉ DNAT **3389** (TCP+UDP), và `inet gw` chain `forward` chỉ
   accept `tcp/udp dport 3389`. Chain `input` là `policy drop`. Nghĩa là khách
   mua một máy chủ nhưng **chỉ có RDP đi vào được**: web (80/443), WinRM, hay
   bất cứ dịch vụ nào họ dựng đều không tới được từ Internet.

   Điều khoản khi đó khai **cổng RA bị chặn** (25/465/587…) nhưng **không một
   chữ nào** về cổng vào. Chủ dự án chốt 24/09: giữ nguyên chỉ RDP, nhưng
   **phải khai rõ** — bán một thứ khác với thứ giao là rủi ro pháp lý, và là
   lá thư hỗ trợ đầu tiên của mọi khách dựng web trên máy.
"""
import pytest

from tests.test_298_vps_dieu_khoan import _render  # noqa: F401  (dùng lại bộ render)


@pytest.fixture(scope="module")
def vi() -> str:
    return _render("/vps/dieu-khoan")


@pytest.fixture(scope="module")
def en() -> str:
    return _render("/en/vps/dieu-khoan")


def test_noi_ro_chi_RDP_di_vao(vi):
    """Phải có con số cổng, không chỉ chữ 'RDP' — khách cần tra được."""
    assert "3389" in vi
    thap = vi.lower()
    assert "chỉ" in thap and "rdp" in thap


def test_noi_ro_dich_vu_khac_KHONG_tu_ra_Internet(vi):
    """Câu phải nói hệ quả, không chỉ nói sự kiện."""
    thap = vi.lower()
    assert any(k in thap for k in ("không mở", "không tới được", "không truy cập được",
                                   "không vào được từ internet"))


def test_ban_EN_cung_khai(en):
    assert "3389" in en and "rdp" in en.lower()
