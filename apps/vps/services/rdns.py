"""rDNS cho IP khach: A record truoc, PTR sau — va khong bao gio chan viec giao may.

## Vi sao co tep nay

Do 25/09/2026 khi so voi Vultr: **khong mot IP nao cua ta co PTR**, trong khi moi
nha cung cap deu dat mac dinh (`*.vultrusercontent.com`, `*.compute.amazonaws.com`,
`*.ovh.net`). Mot dia chi datacenter khong co rDNS la mot diem tru voi cac he thong
chong lam dung.

## Thu tu la mot BAT BIEN, khong phai so thich

OVH **bat buoc forward-confirm**. Do that tren `51.79.202.1`:

    POST /ip/51.79.202.1%2F32/reverse
    400 {"message":"Cannot check if ip-51-79-202-1.vps.lttstudios.com. resolves to 51.79.202.1"}

Nen: tao A record -> cho no resolve -> moi dat PTR. Goi OVH truoc chi de nhan mot
loi kho doc hon.

## ⛔ Khong bao gio nem

Mot may khong co rDNS van la mot may **giao duoc**; mot may khong giao duoc vi DNS
la mot **su co**. Moi loi o day tra `False` va ghi canh bao. `bao_tri` kiem lai va
ghi ban ghi suc khoe, nen mot IP thieu PTR **hien ra** chu khong bien mat.

## Ten suy tu IP, ⛔ khong lay ten khach dat

Khach dat ten may tuy y. Ten do se nam **cong khai trong DNS** va khong xoa duoc
khoi lich su cac dich vu quet DNS. Ten suy tu IP thi khong lo gi ve khach.
"""
from __future__ import annotations

import ipaddress
import logging

log = logging.getLogger(__name__)

#: Vung dat A record cho IP khach. Mot hang so, khong go lai o cho khac.
MIEN_RDNS = "vps.lttstudios.com"


def ten_forward(ip: str) -> str:
    """`51.79.215.194` -> `ip-51-79-215-194.vps.lttstudios.com`.

    ⛔ Tu choi moi thu khong phai IPv4: chuoi nay di vao mot loi goi API va vao
       DNS cong khai.
    """
    dia_chi = ipaddress.IPv4Address(str(ip or "").strip())   # ValueError neu rac
    return "ip-" + str(dia_chi).replace(".", "-") + "." + MIEN_RDNS


def dat_rdns(dns, ovh, ip: str) -> bool:
    """A record truoc, PTR sau. Tra `True` khi ca hai buoc xong.

    `dns` co `dat_a_record(ten, ip)`; `ovh` co `dat_reverse(ip, ten)`.
    """
    try:
        ten = ten_forward(ip)
    except ValueError:
        log.warning("VPS rdns: dia chi khong hop le, bo qua: %r", ip)
        return False
    try:
        dns.dat_a_record(ten, str(ip))
    except Exception as exc:                  # noqa: BLE001 - xem docstring module
        log.warning("VPS rdns: khong tao duoc A record %s -> %s: %s", ten, ip, exc)
        return False
    try:
        ovh.dat_reverse(str(ip), ten)
    except Exception as exc:                  # noqa: BLE001
        log.warning("VPS rdns: A record %s da co nhung OVH tu choi PTR: %s", ten, exc)
        return False
    log.info("VPS rdns: %s -> %s", ip, ten)
    return True
