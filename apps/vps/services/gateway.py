"""Điều khiển cổng vào Linux: mở và đóng đường NAT 1:1 cho một máy khách.

## Vì sao SSH chứ không phải một API

Cổng vào là một máy Debian trần. Dựng thêm một dịch vụ HTTP trên đó chỉ để nhận hai
lệnh `nft` là thêm một thứ phải vá, phải xoay khoá, và phải canh. SSH bằng **khoá**
thì đã có sẵn, đã được xác thực, và không mở thêm cổng nào ra Internet.

Khoá riêng nằm ở `secrets/`, **không phải mật khẩu**. Đây là điểm khác quan trọng so
với cổng vào Windows cũ: cái đó mở bằng file DPAPI buộc vào **một con người**, nên
worker không tự chạy được và mọi thao tác đều phải chờ người bấm.

## Vì sao dùng `map` của nftables chứ không phải mỗi khách một luật

Tài liệu hiệu năng WireGuard/nftables nói rõ: **ruleset càng dài thì mọi kết nối
càng chậm**, vì gói phải đi qua từng luật. Cách phổ biến — thêm một luật `dnat` cho
mỗi khách — làm chính điều đó. Ở đây một khách là **một phần tử trong `map`**, tra
cứu O(1) bất kể 5 hay 500 khách, và thêm/bớt là thao tác nguyên tử không nạp lại
ruleset.

## Bền qua khởi động lại

`nft add element` chỉ sống trong bộ nhớ, và `ip addr add` cũng vậy. Nếu chỉ làm hai
việc đó thì **gateway khởi động lại là toàn bộ khách mất đường vào**, im lặng, và
triệu chứng sẽ là "sáng nay không ai vào được máy nữa". Nên mỗi lần đổi, ta ghi lại
`/etc/ltt-vps/duong.conf` và một unit systemd phát lại nó lúc khởi động — xem
`tools/vps_gateway/cai-dat-cong-vao.sh`.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass

#: Nơi cổng vào ghi danh sách đường đang mở, để phát lại sau khi khởi động lại.
TEP_TRANG_THAI = "/etc/ltt-vps/duong.conf"
TIMEOUT_GIAY = 60


class GatewayError(RuntimeError):
    """Không chạy được lệnh trên cổng vào, hoặc cổng vào trả lỗi."""


@dataclass(frozen=True)
class GatewayConfig:
    host: str
    user: str = "root"
    khoa: str = ""
    #: Tên bảng nftables trên cổng vào. Hai map `vao` / `ra` nằm trong bảng này.
    bang: str = "ltt"

    def verify(self) -> "GatewayConfig":
        if not self.host:
            raise GatewayError("thieu LTT_VPS_GATEWAY_HOST trong secrets/app.env")
        if not self.khoa:
            raise GatewayError("thieu LTT_VPS_GATEWAY_SSH_KEY trong secrets/app.env")
        if not os.path.exists(self.khoa):
            raise GatewayError(f"khong thay file khoa SSH: {self.khoa}")
        return self


def doc_cau_hinh(env: dict | None = None) -> GatewayConfig:
    src = os.environ if env is None else env
    return GatewayConfig(
        host=str(src.get("LTT_VPS_GATEWAY_HOST", "")).strip(),
        user=str(src.get("LTT_VPS_GATEWAY_USER", "root")).strip() or "root",
        khoa=str(src.get("LTT_VPS_GATEWAY_SSH_KEY", "")).strip(),
        bang=str(src.get("LTT_VPS_GATEWAY_NFT_TABLE", "ltt")).strip() or "ltt",
    ).verify()


class GatewayClient:
    """`chay` cho phép tiêm hàm giả lúc test — nhận `list[str]`, trả `str`."""

    def __init__(self, config: GatewayConfig, *, chay=None):
        self.config = config
        self._chay = chay or self._chay_that

    # ── tầng vận chuyển ──────────────────────────────────────────────────────

    def _chay_that(self, lenh: list[str]) -> str:
        # `BatchMode=yes`: thà hỏng ngay còn hơn treo chờ nhập mật khẩu trong một
        # worker không có ai ngồi trước màn hình.
        ssh = ["ssh", "-i", self.config.khoa, "-o", "BatchMode=yes",
               "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new",
               "-o", "ConnectTimeout=10",
               f"{self.config.user}@{self.config.host}", " ".join(lenh)]
        try:
            r = subprocess.run(ssh, capture_output=True, text=True,
                               timeout=TIMEOUT_GIAY)
        except subprocess.TimeoutExpired as exc:
            raise GatewayError(
                f"cong vao {self.config.host} khong tra loi trong {TIMEOUT_GIAY}s"
            ) from exc
        if r.returncode != 0:
            raise GatewayError(
                f"cong vao tra ma {r.returncode}: "
                f"{(r.stderr or r.stdout).strip()[:300]}")
        return r.stdout

    def _bash(self, kich_ban: str) -> str:
        """Chạy một đoạn bash trên cổng vào.

        Truyền **một chuỗi đã bọc `shlex.quote`** chứ không ghép chuỗi trần: đây
        là chỗ dữ liệu của khách (địa chỉ IP) đi vào một shell từ xa, và AGENTS
        §5.3 đã ghi cái giá của việc ghép chuỗi qua nhiều lớp shell.
        """
        return self._chay(["bash", "-c", shlex.quote(kich_ban)])

    # ── đọc ──────────────────────────────────────────────────────────────────

    def con_song(self) -> bool:
        return self._bash("echo song").strip().endswith("song")

    def danh_sach_duong(self) -> dict:
        """Đọc map `vao` trên cổng vào: `{IP công khai: IP nội bộ}`.

        Đây là **sự thật ngoài CSDL**. Đối chiếu nó với `vps_ip` là cách duy nhất
        phát hiện lệch — mà lệch ở đây nghĩa là khách gõ đúng địa chỉ và rơi vào
        máy người khác.
        """
        ra = self._bash(f"nft -j list map ip {self.config.bang} vao")
        try:
            doc = json.loads(ra)
        except json.JSONDecodeError as exc:
            raise GatewayError(
                f"nft tra ve khong phai JSON ({exc}): {ra[:200]}") from exc
        ket_qua: dict[str, str] = {}
        for muc in doc.get("nftables", []):
            phan_tu = (muc.get("map") or {}).get("elem") or []
            for cap in phan_tu:
                if isinstance(cap, list) and len(cap) == 2:
                    ket_qua[str(cap[0])] = str(cap[1])
        return ket_qua

    # ── mở và đóng đường ─────────────────────────────────────────────────────

    def mo_duong(self, ip_cong_khai: str, ip_noi_bo: str) -> None:
        """Cho một IP công khai trỏ toàn bộ cổng vào một máy. Chạy lại được.

        Ba việc, và **thiếu việc nào cũng hỏng im lặng**:
          1. `ip addr add` — không có thì cổng vào không trả lời ARP cho IP đó và
             gói không bao giờ tới nơi;
          2. `map vao` — chiều vào;
          3. `map ra` — chiều ra; thiếu thì máy khách ra Internet bằng IP của
             cổng vào chứ không bằng IP của chính nó, và mọi dịch vụ đối chiếu
             địa chỉ (mail, API có allowlist) sẽ thấy sai địa chỉ.
        """
        _kiem_dia_chi(ip_cong_khai)
        _kiem_dia_chi(ip_noi_bo)
        b = self.config.bang
        self._bash(
            "set -e; "
            "WAN=$(ip -o -4 route show default | awk '{print $5; exit}'); "
            f"ip addr replace {ip_cong_khai}/32 dev $WAN; "
            # `delete` trước `add`: `nft add element` báo lỗi nếu khoá đã tồn tại
            # với giá trị khác, và ta muốn thao tác này chạy lại được.
            f"nft delete element ip {b} vao {{ {ip_cong_khai} }} 2>/dev/null || true; "
            f"nft delete element ip {b} ra  {{ {ip_noi_bo} }} 2>/dev/null || true; "
            f"nft add element ip {b} vao {{ {ip_cong_khai} : {ip_noi_bo} }}; "
            f"nft add element ip {b} ra  {{ {ip_noi_bo} : {ip_cong_khai} }}; "
            f"mkdir -p $(dirname {TEP_TRANG_THAI}); "
            f"touch {TEP_TRANG_THAI}; "
            f"grep -v '^{ip_cong_khai} ' {TEP_TRANG_THAI} > {TEP_TRANG_THAI}.moi || true; "
            f"echo '{ip_cong_khai} {ip_noi_bo}' >> {TEP_TRANG_THAI}.moi; "
            f"mv {TEP_TRANG_THAI}.moi {TEP_TRANG_THAI}")

    def dong_duong(self, ip_cong_khai: str, ip_noi_bo: str) -> None:
        """Gỡ đường. Chạy lại được, và không kêu nếu đã gỡ rồi."""
        _kiem_dia_chi(ip_cong_khai)
        _kiem_dia_chi(ip_noi_bo)
        b = self.config.bang
        self._bash(
            "WAN=$(ip -o -4 route show default | awk '{print $5; exit}'); "
            f"nft delete element ip {b} vao {{ {ip_cong_khai} }} 2>/dev/null || true; "
            f"nft delete element ip {b} ra  {{ {ip_noi_bo} }} 2>/dev/null || true; "
            f"ip addr del {ip_cong_khai}/32 dev $WAN 2>/dev/null || true; "
            f"if [ -f {TEP_TRANG_THAI} ]; then "
            f"  grep -v '^{ip_cong_khai} ' {TEP_TRANG_THAI} > {TEP_TRANG_THAI}.moi || true; "
            f"  mv {TEP_TRANG_THAI}.moi {TEP_TRANG_THAI}; "
            f"fi; true")


def _kiem_dia_chi(gt: str) -> None:
    """Chặn mọi thứ không phải IPv4 trước khi nó chạm tới shell của cổng vào."""
    phan = str(gt or "").split(".")
    if len(phan) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in phan):
        raise GatewayError(f"khong phai dia chi IPv4: {gt!r}")


def client_tu_moi_truong(env: dict | None = None, *, chay=None) -> GatewayClient:
    return GatewayClient(doc_cau_hinh(env), chay=chay)
