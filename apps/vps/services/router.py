"""VM router (`10.51.0.1`): đặt chỗ DHCP theo MAC cho từng máy khách.

## Vì sao phải có DHCP, khi trước đây không cần

Mô hình cũ nhân bản một template có sẵn ổ cloud-init, nên nền tảng tiêm thẳng
`ip=10.51.0.50/24,gw=10.51.0.1` vào máy. Từ 2026-08-24 khách **tự cài Windows**,
và trình cài đặt Windows không đọc cloud-init. Không còn đường nào khác để máy có
mạng mà khách không phải tự gõ địa chỉ — nên router phải cấp.

Cấp **theo MAC**, không phải cấp bừa trong một dải: nền tảng đã ghi
`vps_instance.ip_noi_bo` vào CSDL và mở NAT 1:1 tới đúng địa chỉ đó. Nếu DHCP
phát một địa chỉ khác thì gói từ Internet vẫn tới `10.51.0.50` trong khi máy
đang mang `10.51.0.73`, và triệu chứng là **máy chạy tốt nhưng không ai vào
được** — không lỗi nào được ghi ra ở bất cứ đâu.

Chỗ neo cho phép làm việc này là MAC ổn định: nó suy ra từ `instance_id` và
không đổi qua các lần chạy lại job. Xem `services/dinh_danh.py`.

## Vì sao ghi tệp rồi SIGHUP, không phải sinh lại cấu hình

`dhcp-hostsfile` được dnsmasq đọc lại khi nhận SIGHUP, **không** cần khởi động
lại. Khởi động lại dnsmasq giữa lúc một khách đang gia hạn thuê bao là cách để
máy họ rớt mạng vì một khách khác vừa được tạo.

## Cấp phát nằm ở CSDL, không nằm ở đây

`dhcp-range=...,static` nghĩa là dnsmasq **chỉ** cấp cho MAC đã khai; máy lạ cắm
vào bridge không nhận được gì. Router không tự chọn địa chỉ bao giờ — chọn địa
chỉ là việc của `provisioning.cap_ip_noi_bo`, và hai nơi cùng chọn là hai máy
cùng một địa chỉ.
"""
from __future__ import annotations

import os

from apps.vps.services.ssh_lenh import (DichDen, SshLenhError, bash_tu_xa,
                                        kiem_dia_chi, kiem_mac)

#: Tệp dnsmasq đọc lại mỗi lần nhận SIGHUP.
TEP_DAT_CHO = "/etc/ltt-vps/dhcp-hosts"


class RouterError(SshLenhError):
    """VM router không nhận lệnh, hoặc trả lỗi."""


def doc_cau_hinh(env: dict | None = None) -> DichDen:
    src = os.environ if env is None else env
    user = str(src.get("LTT_VPS_ROUTER_USER", "ltt")).strip() or "ltt"
    return DichDen(
        host=str(src.get("LTT_VPS_ROUTER_HOST", "")).strip(),
        user=user,
        khoa=str(src.get("LTT_VPS_ROUTER_SSH_KEY", "")).strip(),
        nhan="VM router",
        # KHÔNG chạy cả kịch bản bằng `sudo`. Tài khoản `ltt` ghi được
        # `dhcp-hosts` vì thư mục thuộc về nó (`cai-dat-router.sh` chown), nên
        # thứ duy nhất cần quyền root là **một lệnh**: nạp lại dnsmasq. Cho cả
        # đoạn bash chạy bằng root chỉ để tiện là mở rộng thiệt hại của mọi lỗi
        # trong đoạn đó, không đổi lại được gì.
        tien_to="",
    ).verify("LTT_VPS_ROUTER_HOST")


class RouterClient:
    """`chay` cho phép tiêm hàm giả lúc test — nhận `list[str]`, trả `str`."""

    def __init__(self, dich: DichDen, *, chay=None):
        self.dich = dich
        self._chay = chay

    def _bash(self, kich_ban: str) -> str:
        try:
            return bash_tu_xa(self.dich, kich_ban, chay=self._chay)
        except SshLenhError as exc:
            raise RouterError(str(exc)) from exc

    def con_song(self) -> bool:
        return self._bash("echo song").strip().endswith("song")

    def danh_sach_dat_cho(self) -> dict[str, str]:
        """Đọc `{MAC: IP}` từ router. Đây là **sự thật ngoài CSDL**.

        Đối chiếu nó với `vps_instance.ip_noi_bo` là cách duy nhất phát hiện lệch
        — mà lệch ở đây nghĩa là máy khách chạy tốt nhưng không ai vào được.
        """
        ra = self._bash(f"cat {TEP_DAT_CHO} 2>/dev/null || true")
        ket_qua: dict[str, str] = {}
        for dong in ra.splitlines():
            phan = dong.strip().split(",")
            if len(phan) >= 2 and phan[0]:
                ket_qua[phan[0].strip().lower()] = phan[1].strip()
        return ket_qua

    def dat_cho(self, mac: str, ip_noi_bo: str, ten: str = "") -> None:
        """Buộc một MAC vào một địa chỉ. Chạy lại được.

        Xoá dòng cũ **theo cả MAC lẫn địa chỉ** trước khi ghi dòng mới: bỏ sót vế
        địa chỉ thì một máy đã xoá còn giữ chỗ, và máy mới nhận đúng địa chỉ đó
        sẽ không bao giờ được cấp — dnsmasq gặp hai dòng cùng địa chỉ thì giữ
        dòng đầu.
        """
        mac = kiem_mac(mac, loi=RouterError)
        ip = kiem_dia_chi(ip_noi_bo, loi=RouterError)
        ten = "".join(c for c in str(ten or "") if c.isalnum() or c in "-")[:60]
        dong = f"{mac},{ip}" + (f",{ten}" if ten else "")
        self._bash(
            "set -e; "
            f"touch {TEP_DAT_CHO}; "
            f"grep -v -e '^{mac},' -e ',{ip},' -e ',{ip}$' {TEP_DAT_CHO} "
            f"  > {TEP_DAT_CHO}.moi || true; "
            f"echo '{dong}' >> {TEP_DAT_CHO}.moi; "
            f"mv {TEP_DAT_CHO}.moi {TEP_DAT_CHO}; "
            # SIGHUP chứ không `restart`: khởi động lại giữa lúc một khách đang
            # gia hạn là cách làm rớt mạng máy họ vì một khách khác vừa được tạo.
            "sudo -n systemctl reload dnsmasq")

    def go_cho(self, mac: str) -> None:
        """Gỡ chỗ. Chạy lại được, và không kêu nếu đã gỡ rồi."""
        mac = kiem_mac(mac, loi=RouterError)
        self._bash(
            f"if [ -f {TEP_DAT_CHO} ]; then "
            f"  grep -v '^{mac},' {TEP_DAT_CHO} > {TEP_DAT_CHO}.moi || true; "
            f"  mv {TEP_DAT_CHO}.moi {TEP_DAT_CHO}; "
            f"  sudo -n systemctl reload dnsmasq; "
            f"fi; true")


def client_tu_moi_truong(env: dict | None = None, *, chay=None) -> RouterClient:
    return RouterClient(doc_cau_hinh(env), chay=chay)
