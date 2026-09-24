"""Do cong cua cong vao — mot nguon cho ca cong cu van hanh lan vong bao tri.

🔴 24/09/2026: `/etc/nftables.conf` cua cong vao viet `tcp dport 22 accept`, mot
   dieu kien **khong neu dia chi dich**, nen SSH quan tri tra loi tren ca 11 dia
   chi IPv4 — gom ca dia chi vua ban cho khach.

⭐ Do **tu ben ngoai**, khong doc lai cau hinh: cau hinh la **y dinh**, ket noi
   la **su that**. Mot luat dung nam trong tep ma bi mot luat khac di truoc thi
   tep van "dung" con cua van mo.
"""
from __future__ import annotations

import socket

#: Cong SSH quan tri.
CONG_QUAN_TRI = 22
#: Cong duy nhat gateway chuyen tiep vao may khach.
CONG_RDP = 3389
CHO_GIAY = 6.0


def cong_mo(ip: str, cong: int, cho: float = CHO_GIAY) -> tuple[bool, str]:
    """Ket noi TCP that. Tra `(mo, ly_do)`.

    ⛔ Khong nuot `OSError` lang le, va ⛔ khong tra mot `bool` tran: o mot phep
       kiem an ninh, hai cach "dong" la **hai the gioi khac han**:

         TimeoutError            goi tin bi DROP  -> CO luat chan, dung y muon
         ConnectionRefusedError  goi tin toi noi, khong ai nghe -> KHONG co luat
                                 chan; dich vu chi tinh co khong chay, va mai no
                                 chay lai la cua mo

       Vut ly do di thi ca hai in ra cung mot chu "dong", va phep kiem an ninh
       thanh phep kiem **may rui**. Day la khuon da can sau lan trong mot ngay o
       bon phien doc lap: mot gia tri mang hai nghia, va ta mat kha nang phan
       biet chung.
    """
    s = socket.socket()
    s.settimeout(cho)
    try:
        s.connect((ip, cong))
        return True, "bat tay duoc"
    except OSError as exc:
        return False, type(exc).__name__
    finally:
        s.close()


def luat_khop(chain_input: str, ip_quan_tri: str) -> tuple[bool, str]:
    """THUAN. Chain `input` co luat chan cong 22 dung dia chi quan tri hien tai?

    ⚠️ Ban va cho "cong quan tri lo" la mot **con so** go vao mot tep tren MOT
       MAY KHAC. Ngay OVH doi IP chinh cua cong vao, con so do het dung, luat van
       "co", va cua mo lai **trong im lang** — dung khuon cua chinh loi vua sua.
       Nen phai co mot phep so con so trong luat voi nguon chan ly trong so sach
       (`vps_gateway.ip_cong_khai`).
    """
    for dong in chain_input.splitlines():
        d = dong.strip()
        if "dport 22 drop" in d and "daddr" in d:
            if f"!= {ip_quan_tri}" in d:
                return True, d
            return False, f"luat co, nhung neu dia chi KHAC voi gateway hien tai: {d}"
    return False, "KHONG co luat chan cong 22 nao trong chain input"
