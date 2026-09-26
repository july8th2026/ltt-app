"""Máy mới phải được nạp `ipfilter-net0` và bật `dhcp` — nếu không thì **mất mạng**.

## Bật tường lửa cụm làm một dòng cấu hình VÔ HẠI trở thành NGUY HIỂM

`mang.cau_hinh_qemu` đặt `firewall=1` trên `net0` từ trước (`mang.py:173`). Suốt thời
gian tường lửa cụm **chưa bật**, cờ đó ⛔ không làm gì — nên ⛔ không ai thấy rằng hai
mảnh còn thiếu.

Ngày 26/09/2026 tường lửa cụm được bật. Từ giây đó, một máy mới sẽ có:

    net0 ... firewall=1        (da co tu truoc)
    ipfilter = 1               (`_firewall_may_khach`)
    ipset ipfilter-net0        -> RONG
    dhcp                       -> KHONG khai (mac dinh 0)

Tài liệu Proxmox: `ipfilter` *"is equivalent to adding an **empty** `ipfilter-net<id>`
ipset"*, và IP chỉ được **tự thêm cho container** — máy ảo thì không.

⇒ **Máy VPS tiếp theo khách mua sẽ không có IPv4 nào cả.** Và nó hỏng theo kiểu tệ
  nhất: máy dựng xong, Proxmox báo `running`, trang khách nói "Đang chạy", và khách
  RDP vào thì **không có gì**.

⭐ Khuôn đáng nhớ: **bật một cái công tắc làm đổi NGHĨA của cấu hình đã nằm sẵn.**
   Một dòng vô hại suốt nhiều tuần trở thành một lỗi chặn khách, mà ⛔ không ai sửa
   dòng nào cả. Nên khi bật một lớp bảo vệ toàn cục, câu phải hỏi ⛔ không phải *"ta
   vừa đổi gì"* mà là *"cái gì đang nằm sẵn vừa đổi nghĩa"*.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from apps.vps import jobs


def test_firewall_may_khach_co_dhcp():
    """Khách lấy địa chỉ qua DHCP từ VM199. `ipfilter` chặn luôn gói DHCP
    (nguồn `0.0.0.0`) nếu ⛔ không khai `dhcp: 1` — nên máy mất địa chỉ ngay từ
    lần xin lease đầu tiên."""
    assert jobs._firewall_may_khach().get("dhcp") == 1


def test_hai_policy_van_ACCEPT_tuong_minh():
    """⛔ Đừng để Proxmox dùng mặc định `policy_in = DROP`: đó là cắt mạng mọi
    khách bằng một bản vá an ninh."""
    fw = jobs._firewall_may_khach()
    assert fw["policy_in"] == "ACCEPT" and fw["policy_out"] == "ACCEPT"
    assert fw["ipfilter"] == 1 and fw["macfilter"] == 1 and fw["enable"] == 1


def test_dat_firewall_NAP_ipset_bang_IP_NOI_BO_that():
    """Ipset rỗng = chặn hết IPv4. Phải nạp đúng IP máy đang dùng."""
    da_goi = {}

    class _Cli:
        def dat_firewall(self, vmid, **kw):
            da_goi["fw"] = (vmid, kw)

        def dat_ipset_may(self, vmid, ten, cac_cidr):
            da_goi["ipset"] = (vmid, ten, list(cac_cidr))

    assert jobs._dat_firewall_may_khach(_Cli(), 900, "10.50.0.77") is True
    assert da_goi["ipset"] == (900, "ipfilter-net0", ["10.50.0.77"])
    assert da_goi["fw"][1].get("dhcp") == 1


def test_KHONG_co_ip_noi_bo_thi_KHONG_bat_ipfilter():
    """🔴 Ca nguy hiểm nhất: chưa biết IP mà vẫn bật `ipfilter` ⇒ ipset rỗng ⇒
    **máy khách không có mạng**, trong khi mọi thứ khác trông như đã xong.

    ⇒ Thà để máy **chưa được chống spoof** (trạng thái cũ, đã sống nhiều tuần) còn
      hơn giao cho khách một máy **không vào được**. `bao_tri` kiểm lại và ghi bản
      ghi sức khoẻ nên máy lệch chuẩn **hiện ra** chứ không biến mất.
    """
    da_goi = {}

    class _Cli:
        def dat_firewall(self, vmid, **kw):
            da_goi["fw"] = kw

        def dat_ipset_may(self, vmid, ten, cac_cidr):
            da_goi["ipset"] = True

    jobs._dat_firewall_may_khach(_Cli(), 900, "")
    assert "ipset" not in da_goi, "khong co IP ma van nap ipset"
    assert da_goi["fw"].get("ipfilter") == 0, (
        "khong biet IP thi KHONG duoc bat ipfilter — ipset rong la cat mang")


def test_duong_tao_may_TRUYEN_ip_noi_bo_vao_buoc_firewall():
    """Chốt chỗ NỐI, ⛔ không chỉ chốt hàm.

    Đây đúng là hình dạng đã hỏng hai lần trong kho này: hàm nhận tham số đúng,
    nhưng nơi gọi ⛔ không truyền nó (`client=None` ở vòng chụp ảnh).
    """
    cay = ast.parse(inspect.getsource(jobs._tao_may))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and getattr(n.func, "id", "") == "_dat_firewall_may_khach"]
    assert goi, "duong tao may khong con goi _dat_firewall_may_khach"
    assert all(len(g.args) >= 3 for g in goi), (
        "phai truyen ip_noi_bo lam tham so thu ba, neu khong ipset se RONG")


def test_net0_van_co_firewall_1():
    """Dòng này có từ trước và ⛔ không được mất — nó là tầng thứ hai của phép AND."""
    nguon = Path("apps/vps/services/mang.py").read_text(encoding="utf-8")
    assert "firewall=1" in nguon


def test_client_proxmox_co_duong_dat_ipset():
    from apps.vps.services import proxmox

    assert hasattr(proxmox.ProxmoxClient, "dat_ipset_may")
