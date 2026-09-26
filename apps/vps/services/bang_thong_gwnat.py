"""Đo băng thông từng máy khách tại **gateway OVH** — điểm đo mà R26 còn thiếu.

## Vì sao không đọc ở router VM199 như dải Vultr

`bao_tri._dong_bo_bang_thong` đọc bộ đếm qua `backend_factory.router_backend`, và
với hồ sơ OVH thì router đó là **VM199** (`192.168.2.2`). Nhưng lưu lượng VPS OVH
⛔ **không đi qua VM199**: gateway của máy khách là host Proxmox (`10.50.0.1`), và
NAT xảy ra ở gateway OVH (`51.79.166.36`).

⇒ Đo 26/09/2026 trên production: cả hai máy khách `bang_thong_byte = 0`, vĩnh viễn.
  Và trang bán thì hứa *"vượt hạn mức thì bị giảm tốc, không bị tính thêm tiền"* —
  một lời hứa **chưa bao giờ được thực thi**, vì không có số để so với hạn mức.

## Bộ đếm phải nằm ở chain `filter`, ⛔ KHÔNG phải `nat`

🔴 Đây là chỗ tôi suýt làm sai: chỗ tự nhiên nhất để thêm `counter` là các luật
   SNAT/DNAT đã có trong table `gwnat`. Hai lý do độc lập khiến nó **sai**:

   1. `ltt-gwnat` **xoá và dựng lại** cả table `gwnat` mỗi lần mapping đổi
      (`delete table ip gwnat`) ⇒ mỗi lần một khách mua máy là mọi bộ đếm về 0;
   2. quan trọng hơn: chain `nat` chỉ thấy **gói đầu tiên** của mỗi kết nối
      (conntrack). Một `counter` trong đó đếm **số kết nối**, không phải byte —
      nó cho ra một con số gần 0 trong khi trông như đã sửa xong.

⇒ Một table RIÊNG (`ip ltt_dem`), chain `filter hook forward` (thấy MỌI gói),
  `policy accept`, và **chỉ có luật counter** — nên nó ⛔ không thể làm rơi gói nào.

## Lớp hãm tốc: một `set` RỖNG là một cái phanh chưa đạp

Hãm cần một verdict `drop`, tức bảng đếm mất tính chất *"không thể làm rơi gói"*.
Nên nó đi sau, và nó an toàn được vì: hai luật `limit rate over ... drop` chỉ khớp
các địa chỉ **trong set `giam_toc`**, và set đó **rỗng** khi triển khai ⇒ luật không
khớp gì. Rủi ro chỉ xuất hiện đúng lúc một khách thật vượt hạn mức.

⛔ Và helper từ chối mọi địa chỉ **không có trong bảng mapping** (mã thoát 4): một IP
   lạ trong set đó là một cái phanh đặt lên lưu lượng không ai kiểm soát được.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

#: Chú thích trên luật đếm, do `ltt-gwnat ensure_dem` sinh: `<ip> len` / `<ip> xuong`.
HAU_TO_LEN = "len"
HAU_TO_XUONG = "xuong"


class BangThongGwNatError(RuntimeError):
    """Không đọc được bộ đếm ở gateway."""


def doc_tu_json(tho: str) -> dict[str, tuple[int, int]]:
    """`{ip_noi_bo: (byte_len, byte_xuong)}` từ đầu ra `nft -j list chain`.

    ⭐ Parse **JSON của nft**, ⛔ không parse văn bản người-đọc. Bài học 25/09: một
       phép đo đọc định dạng người-đọc (`nslookup`) chết im lặng khi định dạng đổi,
       và nửa phép kiểm đó **chưa từng chạy** mà không ai biết.
    """
    if not (tho or "").strip():
        # ⛔ Rong la KHONG DOC DUOC, khong phai "moi khach dung 0 byte". Tra `{}`
        #    o day la bien mot dut mach do luong thanh mot so lieu — va han muc
        #    thanh vo nghia, im lang. (Cung khuon da gap nhieu lan 25-26/09.)
        raise BangThongGwNatError("gateway tra ve rong")
    try:
        doc = json.loads(tho)
    except json.JSONDecodeError as exc:
        raise BangThongGwNatError(
            f"gateway tra ve khong phai JSON ({exc})") from exc
    ra: dict[str, list[int]] = {}
    for muc in doc.get("nftables", []):
        luat = muc.get("rule")
        if not isinstance(luat, dict):
            continue
        chu_thich = str(luat.get("comment") or "")
        phan = chu_thich.split()
        if len(phan) != 2 or phan[1] not in (HAU_TO_LEN, HAU_TO_XUONG):
            continue
        ip, chieu = phan
        byte = 0
        for e in luat.get("expr") or []:
            if isinstance(e, dict) and isinstance(e.get("counter"), dict):
                byte = int(e["counter"].get("bytes") or 0)
        ra.setdefault(ip, [0, 0])[0 if chieu == HAU_TO_LEN else 1] = byte
    return {ip: (v[0], v[1]) for ip, v in ra.items()}


class BangThongGwNat:
    """Cùng giao diện mà `bao_tri._dong_bo_bang_thong` đã dùng cho router VM199.

    Nhờ giữ đúng giao diện, vòng đồng bộ ⛔ không phải biết hồ sơ này đo ở đâu —
    không một dòng nào trong `_dong_bo_bang_thong` phải đổi.
    """

    def __init__(self, gwnat_client):
        self._gw = gwnat_client

    def con_song(self) -> bool:
        return bool(self._gw.con_song())

    def doc_bang_thong(self) -> dict[str, tuple[int, int]]:
        """Số **tích luỹ từ lúc nạp ruleset** — về 0 khi gateway nạp lại.

        Người gọi phải cộng phần chênh so với mốc lần trước (`bang_thong.cong_don`,
        nó đã xử đúng ca bộ đếm về 0). ⛔ Đọc thẳng như "đã dùng tháng này" là sai.
        """
        return doc_tu_json(self._gw.dem_tho())

    def theo_doi_bang_thong(self, ip_noi_bo: str) -> None:
        """Không cần làm gì: `ltt-gwnat dem` tự thêm luật còn thiếu theo bảng mapping.

        ⚠️ Khác router VM199, nơi một máy ngoài hai set thì **dùng bao nhiêu cũng
           không ai biết**. Ở đây nguồn sự thật là bảng mapping của gateway, nên một
           máy đã có mapping thì chắc chắn có luật đếm.
        """
        return None

    def thoi_theo_doi(self, ip_noi_bo: str) -> None:
        """Luật đếm đi theo mapping: `dong_duong` gỡ mapping là hết đếm.

        ⛔ Không tự xoá luật ở đây: xoá một luật giữa lượt là làm bộ đếm của máy đó
           nhảy về 0 và lượt sau cộng bù sai.
        """
        return None

    def danh_sach_giam_toc(self) -> set[str]:
        """Dia chi dang bi ham, doc tu set `giam_toc` o gateway.

        ⛔ Doc lai phia BEN KIA thay vi tin cot trong CSDL: set nft song trong bo
           nho, gateway nap lai ruleset la set rong — va luc do may dang bi ham
           **het bi ham** trong khi CSDL van ghi la co. Cung nguyen tac voi
           `danh_sach_duong`.
        """
        try:
            doc = json.loads(self._gw.dang_giam_toc_tho() or "{}")
        except json.JSONDecodeError as exc:
            raise BangThongGwNatError(
                f"gateway tra ve khong phai JSON cho set giam_toc ({exc})") from exc
        ra: set[str] = set()
        for muc in doc.get("nftables", []):
            for e in (muc.get("set") or {}).get("elem") or []:
                gia = e.get("elem", {}).get("val") if isinstance(e, dict) else e
                if isinstance(gia, str) and gia:
                    ra.add(gia)
        return ra

    def dat_giam_toc(self, ip_noi_bo: str, bat: bool) -> None:
        """Bat/tat ham toc cho mot may. Chay lai duoc.

        Ham chu KHONG cat: trang ban hua *"vuot han muc thi bi giam toc, khong bi
        tinh them tien"*. Luat o gateway la `limit rate over 1 mbytes/second drop`,
        va TCP tu lui toc khi mat goi — nen no la mot cai phanh, khong phai mot buc
        tuong. ⛔ Cat han bien mot loi hua thanh mot loi noi doi.
        """
        self._gw.dat_giam_toc_tho(ip_noi_bo, bool(bat))


def tu_profile(profile):
    """`BangThongGwNat` cho hồ sơ dùng gateway `ovh_gwnat`, hoặc `None`."""
    config = dict(getattr(profile, "network_config", None) or {})
    if config.get("mapping_strategy") != "ovh_gwnat":
        return None
    from apps.vps.services import backend_factory

    return BangThongGwNat(backend_factory.gateway_backend(profile).client)
