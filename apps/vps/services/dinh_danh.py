"""Danh tính phần cứng của một máy khách: MAC, UUID, số hiệu đĩa.

## Vì sao có file này: hai máy khách KHÔNG được giống hệt nhau

Một cụm ảo hoá mặc định phát ra những máy giống nhau đến mức khó tin. Proxmox
có sinh MAC và UUID ngẫu nhiên cho mỗi máy, nhưng **số hiệu đĩa thì không**:
QEMU đặt nó theo *chỉ số ổ*, nên mọi máy dùng `sata0` đều báo cùng một chuỗi
`QM00005`. Số hiệu hệ thống trong SMBIOS cũng bỏ trống ở mọi máy.

Đó là một lỗi thật, không phải chuyện làm đẹp:

* **Sao lưu và phần mềm cấp phép** nhận diện máy bằng bộ ba (UUID, số hiệu đĩa,
  MAC). Hai máy trùng bộ ba đó thì bản sao lưu của người này đè lên người kia,
  và giấy phép của người này bị tính là cài lại trên máy người kia.
* **Máy này bị chặn thì máy kia chịu chung.** Khi hai khách không phân biệt được
  với nhau ở tầng phần cứng, hành vi của một người dán vào người còn lại. Người
  trả tiền tử tế mất dịch vụ vì hàng xóm, và họ không có cách nào tự chứng minh.

## Vì sao SUY RA từ `instance_id`, không phải bốc ngẫu nhiên

Job tạo máy **chạy lại được** — mất mạng giữa chừng, worker chết, khách bấm hai
lần. Bốc ngẫu nhiên thì mỗi lần chạy lại là một MAC khác, và:

* DHCP theo MAC trên VM router mất chỗ neo — máy đổi địa chỉ trong mạng riêng;
* Windows đã cài xong thấy card mạng "mới", đặt lại hồ sơ mạng về *Public*, và
  **tường lửa chặn RDP** — khách mất đường vào máy của chính họ.

Suy ra từ `instance_id` cho ta cả hai: khác nhau giữa các máy, và **không đổi**
qua mọi lần chạy lại. Cùng khuôn với `_bam` trong `console.py`.

## Một ranh giới cố ý

Ta giữ nguyên OUI `BC:24:11` — OUI đã đăng ký của Proxmox. Máy này **là** máy ảo
và ta không giả nó thành máy Dell hay HP: chuỗi SMBIOS của nhà sản xuất để
nguyên. Việc ở đây là *phân biệt máy khách này với máy khách kia*, không phải
làm cho máy ảo trông như máy vật lý.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

#: OUI của Proxmox. Xem chú thích cuối docstring module: cố ý không giả OUI của
#: một hãng phần cứng thật.
OUI = "BC:24:11"


@dataclass(frozen=True)
class DanhTinh:
    mac: str            # BC:24:11:3A:A6:95
    uuid: str           # 8-4-4-4-12
    so_hieu_dia: str    # <= 20 ký tự, chữ và số
    so_hieu_may: str


def _bit(instance_id: str, muc: str, so_byte: int) -> bytes:
    """Byte suy ra từ (máy, mục). Mỗi mục một chuỗi riêng nên đổi một mục không
    kéo theo mục khác."""
    goc = f"ltt-vps/{muc}/{str(instance_id or '')}".encode("utf-8")
    return hashlib.sha256(goc).digest()[:so_byte]


def mac(instance_id: str) -> str:
    """MAC ổn định cho một máy. Giữ OUI Proxmox, suy ra 3 octet cuối.

    Không gian 3 octet = 16,7 triệu. Với vài nghìn máy, xác suất trùng theo
    nghịch lý ngày sinh vẫn dưới một phần triệu — và dù có trùng thì hai máy
    cũng phải nằm cùng một bridge mới va nhau.
    """
    b = _bit(instance_id, "mac", 3)
    return OUI + ":" + ":".join(f"{x:02X}" for x in b)


def uuid_smbios(instance_id: str) -> str:
    """UUID hệ thống. Đặt tường minh để nó **sống sót qua lần cài lại**.

    Proxmox sinh UUID lúc tạo máy; cài lại máy (xoá rồi dựng lại cùng
    `instance_id`) sẽ cho UUID khác, và với khách thì đó là "một máy khác".
    """
    b = _bit(instance_id, "uuid", 16)
    # Ép về UUID phiên bản 4, biến thể RFC 4122 — để công cụ trong máy khách
    # đọc nó như một UUID hợp lệ chứ không phải 16 byte tuỳ tiện.
    x = bytearray(b)
    x[6] = (x[6] & 0x0F) | 0x40
    x[8] = (x[8] & 0x3F) | 0x80
    h = x.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _chu_so(instance_id: str, muc: str, do_dai: int) -> str:
    bang = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"     # bỏ I và O
    b = _bit(instance_id, muc, do_dai)
    return "".join(bang[x % len(bang)] for x in b)


def so_hieu_dia(instance_id: str) -> str:
    """Số hiệu ổ cứng ảo. QEMU mặc định đặt theo chỉ số ổ nên **mọi máy trùng
    nhau**; đây là chỗ khác biệt bị bỏ sót dễ nhất.

    Giới hạn 20 ký tự là của chuẩn ATA; dài hơn bị cắt cụt lặng lẽ.
    """
    return "LTT" + _chu_so(instance_id, "dia", 13)


def so_hieu_may(instance_id: str) -> str:
    return "LTT-" + _chu_so(instance_id, "may", 10)


def danh_tinh(instance_id: str) -> DanhTinh:
    if not str(instance_id or "").strip():
        raise ValueError("instance_id rong: khong suy ra duoc danh tinh")
    return DanhTinh(mac=mac(instance_id), uuid=uuid_smbios(instance_id),
                    so_hieu_dia=so_hieu_dia(instance_id),
                    so_hieu_may=so_hieu_may(instance_id))


def smbios1(instance_id: str) -> str:
    """Giá trị `smbios1` cho `qm set`.

    Chỉ đặt `uuid` và `serial`. **Không** đặt `manufacturer`/`product`: giả nhà
    sản xuất là việc khác với việc phân biệt hai máy khách, và ta không làm.
    """
    import base64

    dt = danh_tinh(instance_id)
    ma = base64.b64encode(dt.so_hieu_may.encode("ascii")).decode("ascii")
    return f"uuid={dt.uuid},serial={ma},base64=1"
