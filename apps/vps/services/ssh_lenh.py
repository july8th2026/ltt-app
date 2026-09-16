"""Chạy lệnh trên một máy Linux của hạ tầng qua SSH bằng khoá.

Tách ra khỏi `gateway.py` vì nay có **hai** máy phải điều khiển, và chúng khác
nhau về vai trò chứ không khác nhau về cách nói chuyện:

* **cổng vào** (Vultr, ngoài Internet) — giữ IP công khai và NAT 1:1;
* **VM router** (`10.51.0.1`, trong nhà) — cấp DHCP theo MAC và chặn khách sang
  LAN nhà.

Chép tầng vận chuyển sang máy thứ hai nghĩa là chép cả bốn luật dưới đây, và
lần sửa sau sẽ chỉ sửa một bản. Ba trong bốn luật là thứ đã trả giá rồi.

## Bốn luật ở đây, và cái giá của việc quên từng cái

1. **`BatchMode=yes`** — thà hỏng ngay còn hơn treo chờ nhập mật khẩu trong một
   worker không có ai ngồi trước màn hình.
2. **Có `timeout`** — máy chết thì `subprocess.run` chờ vô hạn, và cái treo đó
   giữ luôn một tiến trình worker.
3. **`shlex.quote` một lần, ở đây** — dữ liệu của khách (địa chỉ IP, MAC) đi vào
   một shell TỪ XA. Ghép chuỗi trần qua hai lớp shell là chỗ AGENTS §5.3 nói rõ
   cái giá.
4. **Không dùng dấu huyền trong kịch bản bash truyền đi** — trong heredoc không
   nháy, dấu huyền là thay-thế-lệnh. Đã làm hỏng `cai-dat-router.sh` một lần:
   một dòng chú thích biến thành `bind-interfaces: command not found`.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass

TIMEOUT_GIAY = 60


class SshLenhError(RuntimeError):
    """Không chạy được lệnh trên máy từ xa, hoặc máy đó trả mã lỗi."""


@dataclass(frozen=True)
class DichDen:
    host: str
    user: str = "root"
    khoa: str = ""
    #: Tên hiển thị trong thông báo lỗi — "cong vao" hay "VM router".
    nhan: str = "may"
    #: Tiền tố chạy lệnh, vd `sudo -n `. Rỗng nếu đăng nhập thẳng bằng root.
    tien_to: str = ""
    known_hosts: str = ""

    def verify(self, khoa_env: str = "") -> "DichDen":
        if not self.host:
            raise SshLenhError(f"{self.nhan}: thieu host"
                               + (f" ({khoa_env})" if khoa_env else ""))
        if not self.khoa:
            raise SshLenhError(f"{self.nhan}: thieu duong dan khoa SSH")
        if not os.path.exists(self.khoa):
            raise SshLenhError(f"{self.nhan}: khong thay file khoa SSH: {self.khoa}")
        if self.known_hosts and not os.path.isfile(self.known_hosts):
            raise SshLenhError("canonical SSH known_hosts file is unavailable")
        return self


def chay_ssh(dich: DichDen, lenh: list[str], *,
             timeout: int = TIMEOUT_GIAY) -> str:
    ssh = ["ssh", "-i", dich.khoa, "-o", "BatchMode=yes",
           "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "ConnectTimeout=10",
           f"{dich.user}@{dich.host}", " ".join(lenh)]
    if dich.known_hosts:
        ssh[1:1] = ["-o", f"UserKnownHostsFile={dich.known_hosts}"]
    try:
        r = subprocess.run(ssh, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise SshLenhError(
            f"{dich.nhan} {dich.host} khong tra loi trong {timeout}s") from exc
    if r.returncode != 0:
        # Remote stderr/stdout may include an expanded command, token or key
        # path. The numeric status is sufficient and safe for operator logs.
        raise SshLenhError(f"{dich.nhan} tra ma {r.returncode}")
    return r.stdout


def bash_tu_xa(dich: DichDen, kich_ban: str, *, chay=None,
               timeout: int = TIMEOUT_GIAY) -> str:
    """Chạy một đoạn bash. `chay` cho phép tiêm hàm giả lúc test."""
    goi = chay or (lambda lenh: chay_ssh(dich, lenh, timeout=timeout))
    return goi([f"{dich.tien_to}bash", "-c", shlex.quote(kich_ban)])


def kiem_dia_chi(gt: str, *, loi=SshLenhError) -> str:
    """Chặn mọi thứ không phải IPv4 **trước khi** nó chạm shell từ xa."""
    phan = str(gt or "").split(".")
    if len(phan) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in phan):
        raise loi(f"khong phai dia chi IPv4: {gt!r}")
    return str(gt)


def kiem_mac(gt: str, *, loi=SshLenhError) -> str:
    """Chuẩn hoá MAC về `aa:bb:cc:dd:ee:ff` và từ chối mọi thứ khác.

    Không nới sang dấu `-` hay không dấu: dnsmasq chỉ đọc dạng hai chấm, và một
    MAC sai dạng lọt vào `dhcp-hosts` làm dnsmasq **bỏ qua cả tệp** — máy khách
    không nhận được địa chỉ nào và không có lỗi nào chỉ vào đây.
    """
    x = str(gt or "").strip().lower()
    phan = x.split(":")
    if len(phan) != 6 or not all(
            len(p) == 2 and all(c in "0123456789abcdef" for c in p) for p in phan):
        raise loi(f"khong phai dia chi MAC: {gt!r}")
    return x
