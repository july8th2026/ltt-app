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

#: Card của mạng khách trên VM router. `dhcp_release` cần biết nó.
NIC_KHACH = "eth1"


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


# ── Băng thông ──────────────────────────────────────────────────────────────
#
# Ba `set` trên router (xem `tools/vps_gateway/cai-dat-router.sh`):
#   `bw_len`    — đếm chiều lên  (khách → Internet), khớp bằng `ip saddr`
#   `bw_xuong`  — đếm chiều xuống (Internet → khách), khớp bằng `ip daddr`
#   `giam_toc`  — địa chỉ đang bị hãm tốc
#
# `counter` khai trong `set` nghĩa là **mỗi phần tử có bộ đếm riêng**. Nhờ đó đo
# được từng khách mà không cần một luật cho mỗi người — đúng lý do đã chọn `map`
# cho NAT bên cổng vào: ruleset dài làm chậm **mọi** kết nối.

SET_LEN, SET_XUONG, SET_GIAM_TOC = "bw_len", "bw_xuong", "giam_toc"


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

    def go_cho(self, mac: str, ip_noi_bo: str = "") -> None:
        """Gỡ chỗ **và trả lại lease**. Chạy lại được, không kêu nếu đã gỡ rồi.

        ## Vì sao phải trả lease, không chỉ xoá dòng đặt chỗ

        Xoá dòng trong `dhcp-hosts` chỉ nói "đừng cấp cho MAC này nữa". Nó
        **không** đụng tới lease đang sống. Địa chỉ đó vẫn bị dnsmasq coi là đã
        cấp cho tới khi lease hết hạn — và địa chỉ riêng thì được **cấp lại ngay**
        cho khách tiếp theo.

        Hậu quả đo được: máy mới xin DHCP và nhận `no address available`. Máy lên
        bình thường, chỉ là **không có mạng**, và không lỗi nào chỉ vào nguyên
        nhân. Đã dính thật 24/08 khi hai máy thử lần lượt nhận `10.51.0.99`.

        `ip_noi_bo` rỗng thì bỏ qua phần trả lease — người gọi không biết địa
        chỉ thì chỉ còn cách chờ lease hết hạn (một giờ, xem `cai-dat-router.sh`).
        """
        mac = kiem_mac(mac, loi=RouterError)
        tra_lease = ""
        if str(ip_noi_bo or "").strip():
            ip = kiem_dia_chi(ip_noi_bo, loi=RouterError)
            # `|| true`: máy chưa từng xin lease thì lệnh này báo lỗi, và đó
            # không phải chuyện đáng chặn việc xoá máy.
            tra_lease = (f"  sudo -n dhcp_release {NIC_KHACH} {ip} {mac} "
                         f"2>/dev/null || true; ")
        self._bash(
            f"if [ -f {TEP_DAT_CHO} ]; then "
            f"  grep -v '^{mac},' {TEP_DAT_CHO} > {TEP_DAT_CHO}.moi || true; "
            f"  mv {TEP_DAT_CHO}.moi {TEP_DAT_CHO}; "
            f"{tra_lease}"
            f"  sudo -n systemctl reload dnsmasq; "
            f"fi; true")

    def _them_phan_tu(self, ten_set: str, ip: str) -> None:
        ip = kiem_dia_chi(ip, loi=RouterError)
        self._bash(
            f"sudo -n nft add element inet ltt_rt {ten_set} {{ {ip} }} 2>/dev/null "
            f"|| true")



    def _bot_phan_tu(self, ten_set: str, ip: str) -> None:
        ip = kiem_dia_chi(ip, loi=RouterError)
        self._bash(
            f"sudo -n nft delete element inet ltt_rt {ten_set} {{ {ip} }} "
            f"2>/dev/null || true")



    def theo_doi_bang_thong(self, ip_noi_bo: str) -> None:
        """Bắt đầu đếm cho một máy. Chạy lại được.

        Máy **không** nằm trong hai set này thì gói của nó không khớp luật đếm nào —
        và nó dùng bao nhiêu cũng không ai biết. Im lặng, nên phải gọi cùng lúc với
        lúc cấp địa chỉ chứ không phải "khi nào nhớ ra".
        """
        self._them_phan_tu(SET_LEN, ip_noi_bo)
        self._them_phan_tu(SET_XUONG, ip_noi_bo)



    def thoi_theo_doi(self, ip_noi_bo: str) -> None:
        """Ngừng đếm và bỏ hãm tốc. Gọi khi xoá máy — địa chỉ sẽ được cấp lại cho
        khách khác, và bộ đếm cũ dính sang người mới là một hoá đơn sai."""
        for s in (SET_LEN, SET_XUONG, SET_GIAM_TOC):
            self._bot_phan_tu(s, ip_noi_bo)



    def doc_bang_thong(self) -> dict[str, tuple[int, int]]:
        """`{IP: (byte_lên, byte_xuống)}` — số **tích luỹ từ lúc nạp ruleset**.

        Đọc thẳng con số này như "đã dùng bao nhiêu tháng này" là **sai**: nó về 0
        mỗi lần router khởi động lại. Người gọi phải cộng phần chênh lệch so với mốc
        lần đọc trước — xem `apps/vps/bang_thong.py`.
        """
        import json

        ra: dict[str, list[int]] = {}
        for i, ten in enumerate((SET_LEN, SET_XUONG)):
            tho = self._bash(
                f"sudo -n nft -j list set inet ltt_rt {ten} 2>/dev/null || echo '{{}}'")
            try:
                doc = json.loads(tho or "{}")
            except json.JSONDecodeError as exc:
                raise RouterError(f"nft tra ve khong phai JSON ({exc}): "
                                  f"{(tho or '')[:200]}") from exc
            for muc in doc.get("nftables", []):
                for e in (muc.get("set") or {}).get("elem") or []:
                    pt = e.get("elem") if isinstance(e, dict) else None
                    if not isinstance(pt, dict):
                        continue
                    ip = str(pt.get("val") or "")
                    byte = int((pt.get("counter") or {}).get("bytes") or 0)
                    ra.setdefault(ip, [0, 0])[i] = byte
        return {ip: (v[0], v[1]) for ip, v in ra.items()}



    def dat_giam_toc(self, ip_noi_bo: str, bat: bool) -> None:
        """Bật/tắt hãm tốc cho một máy. Chạy lại được.

        Hãm chứ không cắt: trang bán hứa *"vượt hạn mức thì bị giảm tốc, không bị
        tính thêm tiền"*. Cắt hẳn biến một lời hứa thành một lời nói dối.
        """
        if bat:
            self._them_phan_tu(SET_GIAM_TOC, ip_noi_bo)
        else:
            self._bot_phan_tu(SET_GIAM_TOC, ip_noi_bo)



    def danh_sach_giam_toc(self) -> set[str]:
        import json

        tho = self._bash(f"sudo -n nft -j list set inet ltt_rt {SET_GIAM_TOC} "
                         f"2>/dev/null || echo '{{}}'")
        try:
            doc = json.loads(tho or "{}")
        except json.JSONDecodeError:
            return set()
        ra = set()
        for muc in doc.get("nftables", []):
            for e in (muc.get("set") or {}).get("elem") or []:
                ra.add(str(e.get("elem", {}).get("val") if isinstance(e, dict) else e))
        return {x for x in ra if x and x != "None"}


def client_tu_moi_truong(env: dict | None = None, *, chay=None) -> RouterClient:
    return RouterClient(doc_cau_hinh(env), chay=chay)
