"""Mạng của một máy khách: địa chỉ riêng, card, và cấu hình tiêm vào QEMU.

## Từ 2026-08-24: mỗi máy một IP công khai riêng

Mô hình cũ chia một IP công khai thành nhiều cổng, và buộc cổng với địa chỉ riêng
bằng **một phép cộng** (`cong_ngoai = cong_goc + octet`) để chỉ phải cấp phát một
thứ. Nay mỗi máy có IP công khai của riêng nó, nên **địa chỉ trong mạng riêng là thứ
duy nhất cần cấp phát**, và phép cộng đó mất lý do tồn tại.

Trọng tài cấp phát chuyển sang ràng buộc duy nhất `(gateway_id, ip_noi_bo)` trên
`vps_instance` — cùng khuôn `IntegrityError` của `gpu_lease.py`. Điều phải giữ
nguyên từ mô hình cũ: **chỉ một nơi quyết định địa chỉ**. Hai nơi cùng quyết là mở
cửa cho hai máy nhận cùng một địa chỉ, và triệu chứng của lỗi đó là khách gõ đúng
địa chỉ rồi rơi vào máy người lạ — không lỗi nào được ghi ra.

## Vì sao máy khách CHỈ có một card, và cắm vào bridge cô lập

Tám máy sẵn có của chủ nhà mang hai card: một ra LAN nhà (để quản trị bằng WinRM)
và một vào bridge riêng. Máy **bán cho khách** thì khác: nó **không được** chạm vào
LAN nhà. Ta quản trị nó qua API/console của Proxmox, không qua WinRM, nên card LAN
chỉ là một đường để khách dò sang mạng nội bộ.

Một card, cắm bridge cô lập (`bridge-ports none`). Đường ra Internet đi qua VM router
rồi qua đường hầm; và VM router có luật `nftables` chặn hẳn khách sang `192.168.2.0/24`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from apps.vps.tables import VpsGateway

#: Kiểu card mạng ảo cấp cho máy khách.
#:
#: **Không phải virtio, và đó là một phép đo chứ không phải sở thích.** Proxmox
#: này chạy *lồng* trong VMware; ở đó guest ghi vào thanh ghi notify của
#: `virtio-pci` rồi không bao giờ quay ra. Triệu chứng nhìn từ ngoài: máy
#: `running`, CPU 0%, không một dòng nào trên màn hình. Serial của VM 200 in ra
#: nguyên ngăn xếp: `virtqueue_notify → vp_notify → iowrite16` treo, RCU stall.
#: Đối chiếu: cả 8 máy đang chạy thật trên cụm đều dùng `sata0` + `e1000`,
#: không máy nào dùng virtio. Xem NHAT_KY 2026-08-23.
#:
#: Đổi lại giá trị này khi (và chỉ khi) đã chạy được một máy virtio trên cụm —
#: `e1000` chậm hơn virtio, nên đây là cái giá phải trả, không phải lựa chọn tốt.
MO_HINH_CARD = "e1000"


class CauHinhMangError(ValueError):
    """Cổng vào khai thiếu thứ cần để dựng mạng cho khách."""


@dataclass(frozen=True)
class MangKhach:
    """Mọi thứ cần để cấu hình mạng cho một máy khách."""

    dia_chi: str            # 10.51.0.50
    cidr: str               # 10.51.0.50/24
    gateway: str            # 10.51.0.1
    dns: str                # "1.1.1.1 8.8.8.8"
    bridge: str             # vmbr1
    mtu: int                # 1420


def _tien_to(subnet_cidr: str) -> str:
    """`10.51.0.0/24` → `10.51.0`. Chỉ nhận /24 — xem chú thích dưới."""
    phan = str(subnet_cidr or "").strip().split("/")
    if len(phan) != 2:
        raise CauHinhMangError(f"subnet_cidr sai dang: {subnet_cidr!r}")
    try:
        mask = int(phan[1])
    except ValueError as exc:
        raise CauHinhMangError(f"subnet_cidr sai dang: {subnet_cidr!r}") from exc
    so = phan[0].split(".")
    if len(so) != 4:
        raise CauHinhMangError(f"subnet_cidr sai dang: {subnet_cidr!r}")
    if mask != 24:
        # Cố ý hẹp: hạ tầng đang chạy là /24, và phép ghép `tiền tố + octet` chỉ
        # đúng với /24. Nhận /16 rồi tính sai một octet là cấp trùng địa chỉ.
        # Muốn mở rộng thì viết hẳn phép tính cho mask đó, đừng để nó "gần đúng".
        raise CauHinhMangError(
            f"chi ho tro /24, nhan duoc /{mask} — xem chu thich trong mang.py")
    return ".".join(so[:3])


def _kiem_khai_bao(gateway: VpsGateway) -> None:
    for ten, gt in (("bridge", gateway.bridge),
                    ("subnet_cidr", gateway.subnet_cidr),
                    ("subnet_gw", gateway.subnet_gw)):
        if not str(gt or "").strip():
            raise CauHinhMangError(f"cong vao {gateway.ten!r} thieu {ten}")


def dai_dia_chi(gateway: VpsGateway) -> Iterator[str]:
    """Các địa chỉ ứng viên trong mạng riêng của cổng vào, theo thứ tự.

    Bỏ qua chính địa chỉ của cổng: `10.51.0.1` là VM router, không phải chỗ trống.
    """
    _kiem_khai_bao(gateway)
    tien_to = _tien_to(gateway.subnet_cidr)
    dau = max(2, int(gateway.octet_dau or 2))
    cuoi = min(254, int(gateway.octet_cuoi or 254))
    if dau > cuoi:
        raise CauHinhMangError(
            f"cong vao {gateway.ten!r} co octet_dau {dau} > octet_cuoi {cuoi}")
    cua_router = str(gateway.subnet_gw).strip()
    for octet in range(dau, cuoi + 1):
        dia_chi = f"{tien_to}.{octet}"
        if dia_chi != cua_router:
            yield dia_chi


def so_dia_chi(gateway: VpsGateway) -> int:
    """Tổng số địa chỉ cấp được — dùng để đo sức chứa của một cổng vào."""
    return sum(1 for _ in dai_dia_chi(gateway))


def mang_cho_may(gateway: VpsGateway, ip_noi_bo: str) -> MangKhach:
    """Dựng cấu hình mạng cho một máy đã được cấp địa chỉ."""
    _kiem_khai_bao(gateway)
    dia_chi = str(ip_noi_bo or "").strip()
    if not dia_chi:
        raise CauHinhMangError("may chua duoc cap dia chi trong mang rieng")
    tien_to = _tien_to(gateway.subnet_cidr)
    if not dia_chi.startswith(tien_to + "."):
        raise CauHinhMangError(
            f"dia chi {dia_chi!r} khong thuoc mang {gateway.subnet_cidr!r}")
    if dia_chi == str(gateway.subnet_gw).strip():
        raise CauHinhMangError(f"dia chi {dia_chi!r} trung dia chi cong vao")

    return MangKhach(
        dia_chi=dia_chi,
        cidr=f"{dia_chi}/24",
        gateway=str(gateway.subnet_gw).strip(),
        dns=str(gateway.dns or "").strip(),
        bridge=str(gateway.bridge).strip(),
        mtu=int(gateway.mtu or 0),
    )


def cau_hinh_qemu(mang: MangKhach, *, co_cloud_init: bool = True,
                  mac: str = "") -> dict:
    """Tham số `qm set` để cắm máy vào mạng riêng.

    `net0` là card **duy nhất**: máy khách chỉ được có một đường ra, và nó không
    đi qua LAN nhà.

    `co_cloud_init=False` cho máy **khách tự cài** (Windows): máy đó không có ổ
    cloud-init, nên tiêm `ipconfig0` vào là vô nghĩa — Proxmox nhận tham số
    nhưng **không có gì đọc nó**, và ta sẽ tưởng đã cấu hình mạng trong khi máy
    thì không có địa chỉ nào. Máy đó nhận địa chỉ từ **DHCP theo MAC** trên VM
    router; xem `services/gateway.py`.

    ## `mac` không phải tuỳ chọn trang trí

    Hàm này **ghi đè** `net0`, và job tạo máy chạy lại được. Không truyền `mac`
    thì mỗi lần chạy lại Proxmox sinh một MAC mới, kéo theo hai hỏng hóc lặng lẽ:
    máy mất chỗ neo DHCP nên đổi địa chỉ trong mạng riêng, và Windows đã cài xong
    thấy một card "mới" nên đặt hồ sơ mạng về *Public* — **tường lửa chặn RDP**,
    khách mất đường vào máy của chính họ và không đọc được lý do ở đâu cả.

    MAC ổn định suy ra từ `instance_id`; xem `services/dinh_danh.py`.
    """
    net = f"{MO_HINH_CARD}"
    if str(mac or "").strip():
        net += f"={str(mac).strip().upper()}"
    net += f",bridge={mang.bridge},firewall=0"
    if mang.mtu:
        net += f",mtu={mang.mtu}"
    cau_hinh = {"net0": net}
    if co_cloud_init:
        cau_hinh["ipconfig0"] = f"ip={mang.cidr},gw={mang.gateway}"
        if mang.dns:
            cau_hinh["nameserver"] = mang.dns
    return cau_hinh
