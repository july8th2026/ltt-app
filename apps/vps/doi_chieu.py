"""Đối chiếu CSDL với bốn nguồn sự thật nằm ngoài nó.

## Vì sao cần một phép đối chiếu riêng

App giữ trạng thái ở **năm** chỗ, và bốn trong số đó không phải CSDL của nó:

| Nguồn | Giữ gì | Mất đồng bộ thì sao |
|---|---|---|
| Proxmox | VM | VM mồ côi ăn RAM và đĩa thật, không ai trả tiền |
| router (dnsmasq) | đặt chỗ DHCP | giữ một địa chỉ trong mạng riêng, máy mới nhận địa chỉ đó bị kẹt |
| router (nftables) | bộ đếm băng thông, cờ hãm | bộ đếm cũ dính sang khách mới = hoá đơn sai |
| cổng vào (nftables) | đường NAT 1:1 | gói từ Internet vẫn được dẫn vào mạng riêng |
| Vultr | Reserved IP | **$3/tháng chảy mãi**, và không ai nhìn thấy |

Trước 2026-08-25 **không có gì đối chiếu chúng**. Mọi lần đọc chỉ xảy ra *bên
trong một job, cho đúng một máy đó*. Nghĩa là mọi thứ mồ côi đều sống mãi và
không lộ ra ở đâu cả — không log, không cảnh báo, không một dòng trên trang admin.

## Chỉ NÓI RA, không tự sửa

Hàm ở đây không xoá gì. Tự sửa là đặt cược rằng phép đối chiếu không bao giờ
sai — và một phép đối chiếu sai mà tự sửa thì **xoá đúng thứ nó hiểu nhầm**. Ví
dụ: một VM đang được job khác dựng dở sẽ trông y hệt một VM mồ côi.

Người đọc quyết định, và `tools/vps_treo_khan.py` hay job xoá là công cụ để làm.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LechLac:
    """Một nhóm thứ mồ côi cùng loại."""

    nhan: str
    muc: tuple
    hau_qua: str

    def __str__(self) -> str:
        return f"{self.nhan}: {list(self.muc)} -> {self.hau_qua}"


@dataclass
class KetQua:
    lech: list = field(default_factory=list)
    so_may: int = 0
    so_ip: int = 0
    khong_doc_duoc: list = field(default_factory=list)

    @property
    def tong_mo_coi(self) -> int:
        return sum(len(x.muc) for x in self.lech)

    def __bool__(self) -> bool:
        return bool(self.lech)


def _an_toan(ten: str, ham, mac_dinh, ket_qua: KetQua):
    """Gọi một nguồn ngoài; nguồn không trả lời thì ghi lại và đi tiếp.

    Một nguồn im lặng **không** được làm mất kết quả của các nguồn khác: người
    chạy phép này thường đang tìm một sự cố, và mất nửa báo cáo là mất đúng nửa
    họ cần.
    """
    try:
        return ham()
    except Exception as exc:                     # noqa: BLE001
        ket_qua.khong_doc_duoc.append(f"{ten}: {type(exc).__name__}: "
                                      f"{str(exc)[:80]}")
        return mac_dinh


def quet(db, client) -> KetQua:
    """Đối chiếu tất cả. `client` là ProxmoxClient đã nối được."""
    from sqlalchemy import select

    from apps.vps.services import dinh_danh, gateway, router, vultr
    from apps.vps.tables import VpsInstance, VpsIp

    kq = KetQua()

    may = list(db.execute(select(VpsInstance).where(
        VpsInstance.trang_thai != "da_xoa")).scalars())
    ip_db = list(db.execute(select(VpsIp)).scalars())
    kq.so_may, kq.so_ip = len(may), len(ip_db)

    vmid_db = {m.vmid for m in may if m.vmid}
    mac_db = {dinh_danh.mac(m.id).lower() for m in may}
    priv_db = {str(m.ip_noi_bo) for m in may if m.ip_noi_bo}
    pub_db = {x.dia_chi for x in ip_db}

    # Chỉ xét VM mang tên `vps-*`: 8 máy của chủ nhà trên cùng node KHÔNG phải
    # việc của app, và báo chúng là mồ côi mỗi ngày sẽ dạy người đọc bỏ qua báo
    # cáo này.
    vm_app = _an_toan("proxmox", lambda: {
        int(v["vmid"]) for v in client.danh_sach_vm()
        if str(v.get("name") or "").startswith("vps-")}, None, kq)

    rt = _an_toan("router", router.client_tu_moi_truong, None, kq)
    dat_cho = _an_toan("router/dhcp", rt.danh_sach_dat_cho, {}, kq) if rt else {}
    dang_do = _an_toan("router/bw", rt.doc_bang_thong, {}, kq) if rt else {}
    dang_ham = _an_toan("router/ham", rt.danh_sach_giam_toc, set(), kq) if rt else set()

    gw = _an_toan("gateway", gateway.client_tu_moi_truong, None, kq)
    duong = _an_toan("gateway/nat", gw.danh_sach_duong, {}, kq) if gw else {}

    vt = _an_toan("vultr", vultr.client_tu_moi_truong, None, kq)
    ip_vt = _an_toan("vultr/ip",
                     lambda: {r["subnet"] for r in vt.danh_sach_ip()},
                     None, kq) if vt else None

    def them(nhan, tap, hau_qua):
        if tap:
            kq.lech.append(LechLac(nhan, tuple(sorted(tap)), hau_qua))

    if vm_app is not None:
        them("VM tren Proxmox khong co trong CSDL", vm_app - vmid_db,
             "chiem RAM va dia that, khong ai tra tien")
        them("May trong CSDL khong co VM",
             {m.vmid for m in may if m.vmid and m.vmid not in vm_app},
             "khach tra tien cho mot may khong ton tai")
    them("Dat cho DHCP khong ung may nao",
         {k for k in dat_cho if k.lower() not in mac_db},
         "giu mot dia chi trong mang rieng")
    them("Dang do bang thong ma khong con may",
         {ip for ip in dang_do if ip not in priv_db},
         "bo dem cu dinh sang khach moi nhan cung dia chi = hoa don sai")
    them("Dang bi ham toc ma khong con may",
         {ip for ip in dang_ham if ip not in priv_db},
         "khach moi nhan dia chi do bi ham, khong ai hieu vi sao")
    them("Duong NAT khong co trong CSDL", set(duong) - pub_db,
         "goi tu Internet van duoc dan vao mang rieng")
    if ip_vt is not None:
        them("Reserved IP ben Vultr khong co trong CSDL", ip_vt - pub_db,
             "$3/thang chay mai, va khong ai nhin thay")
        them("Dong vps_ip khong co IP that ben Vultr", pub_db - ip_vt,
             "so sach noi ta co mot dia chi ma thuc te khong con")
    return kq
