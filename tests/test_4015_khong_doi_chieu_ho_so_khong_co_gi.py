"""Đối chiếu một hồ sơ KHÔNG CÓ GÌ là hỏi nhà cung cấp về một cái không tồn tại.

## Ca thật

Hồ sơ Vultr `...0401`: `STANDBY`, `accept_new=False`, **0 máy, 0 IP** — chủ dự án đã
chuyển hẳn sang OVH. Nhưng `_doi_chieu_profiles` vẫn gọi nhà cung cấp cho **mọi** hồ
sơ, và khoá Vultr đang bị từ chối (`401 Unauthorized IP address`). Kết quả:

    2026-09-26 09:37  WARNING  VPS reconciliation unavailable for profile ...0401
    2026-09-26 09:37  WARNING  VPS doi chieu: vultr/ip: VultrError: Vultr tu choi (401)
    ... lặp lại MỖI 10 PHÚT, suốt nhiều ngày

🔴 Hai dòng WARNING mỗi 10 phút cho một hồ sơ **không có gì để đối chiếu** là một
   **báo động giả vĩnh viễn**. Và cái giá của nó ⛔ không phải dung lượng log — nó là
   **người đọc thôi đọc WARNING**. Đúng khuôn đã ghi: báo động giả làm người ta TẮT
   cổng, và lúc ấy một cảnh báo thật sẽ trôi qua không ai thấy.

## Luật là TÍNH CHẤT, ⛔ không phải tên nhà cung cấp

⛔ Đừng viết *"bỏ qua hồ sơ Vultr"*. Đối chiếu tồn tại để **so sổ của ta với thế giới
thật**. Sổ của ta ⛔ không có dòng nào cho hồ sơ này ⇒ ⛔ không có gì để so, và một
lỗi nhà cung cấp ở đây ⛔ không nói gì về dữ liệu của ta.

⚠️ Điều kiện phải là **cả hai** đều rỗng (máy VÀ IP). Một hồ sơ 0 máy mà **còn IP**
   thì vẫn phải đối chiếu — đó đúng là ca *"IP đang tính tiền mà sổ không biết"*, thứ
   đắt nhất mà vòng này sinh ra để bắt.
"""
from __future__ import annotations

from apps.vps import bao_tri


class _HoSo:
    def __init__(self, ho_so_id, status="ACTIVE"):
        self.id = ho_so_id
        self.status = status


def test_ho_so_khong_may_khong_ip_thi_BO_QUA():
    assert bao_tri.co_gi_de_doi_chieu(so_may=0, so_ip=0) is False


def test_ho_so_con_IP_thi_VAN_phai_doi_chieu():
    """0 máy mà còn IP là ca "IP đang tính tiền mà sổ không biết" — đắt nhất."""
    assert bao_tri.co_gi_de_doi_chieu(so_may=0, so_ip=1) is True


def test_ho_so_con_MAY_thi_van_phai_doi_chieu():
    assert bao_tri.co_gi_de_doi_chieu(so_may=1, so_ip=0) is True


def test_ho_so_dang_chay_binh_thuong_thi_doi_chieu():
    assert bao_tri.co_gi_de_doi_chieu(so_may=2, so_ip=10) is True


def test_luat_KHONG_nhac_ten_nha_cung_cap_nao():
    """⛔ Bánh cóc: luật này phải nêu TÍNH CHẤT, không liệt kê tên.

    Một luật tả tên thì mỗi nhà cung cấp mới là một lần sửa — cùng bệnh với
    `.codex` trong danh sách loại trừ của `ruff.toml` (đã tái diễn 4 lần).
    """
    import inspect

    than = inspect.getsource(bao_tri.co_gi_de_doi_chieu)
    # Bo docstring truoc khi soi: docstring GIAI THICH ca that nen no duoc phep
    # nhac ten; than ham thi khong.
    than = than.split('"""')[-1]
    for ten in ("vultr", "ovh", "proxmox", "0401", "0402"):
        assert ten not in than.lower(), (
            f"luat nhac ten {ten!r} — phai neu tinh chat, khong liet ke ten")
