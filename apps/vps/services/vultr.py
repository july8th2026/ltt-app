"""Driver Vultr — chỉ đủ để mua, gắn, gỡ và trả lại **IP công khai**.

## Vì sao viết tay chứ không dùng thư viện

Cùng lý do đã ghi ở `proxmox.py`: bề mặt ta cần là **năm endpoint**, còn thư viện
mang theo mọi endpoint của cả nền tảng — kể cả những cái xoá được máy chủ. Ở đây
điều đó không trừu tượng: tài khoản Vultr của chủ sản phẩm từng chạy **17 instance
phục vụ mảng kinh doanh khác**, và một lệnh `DELETE /instances` sai chỗ là xoá chúng.

Nên driver này **không có bất kỳ phương thức nào đụng tới instance**. Nó đọc được
danh sách instance (để tìm gateway theo nhãn) và đọc băng thông — hết. Muốn xoá một
máy chủ thì phải viết thêm mã, và lúc đó người viết sẽ phải nghĩ.

## Hàng rào thứ hai: chỉ xoá IP mang nhãn của ta

`xoa_ip` đọc lại IP trước khi xoá và **từ chối** nếu nhãn không bắt đầu bằng
`TIEN_TO_NHAN`. Một id truyền nhầm — từ log, từ chỗ khác, từ một bản ghi cũ — sẽ
dừng ở đó thay vì xoá một IP đang phục vụ ai đó.

## Thử lại

Không thử lại gì cả, kể cả GET. `POST /reserved-ips` **không idempotent**: thử lại
một lần là mua thừa một IP, $3/tháng chảy mãi mà không ai biết. Người gọi biết thao
tác nào lặp được, driver thì không.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

API = "https://api.vultr.com/v2"
TIMEOUT_MAC_DINH = (10, 90)

#: Mọi IP do app tạo đều mang nhãn bắt đầu bằng chuỗi này. Xem docstring đầu file.
TIEN_TO_NHAN = "ltt-vps-"


class VultrError(RuntimeError):
    """Vultr từ chối, hoặc không nói được chuyện gì."""

    def __init__(self, thong_diep: str, *, status: int | None = None,
                 duong_dan: str = ""):
        super().__init__(thong_diep)
        self.status = status
        self.duong_dan = duong_dan


@dataclass(frozen=True)
class VultrConfig:
    api_key: str
    vung: str = "sgp"

    def verify(self) -> "VultrConfig":
        if not self.api_key:
            raise VultrError(
                "thieu LTT_VULTR_API_KEY trong secrets/app.env — app se khong "
                "mua duoc IP cho khach")
        return self


def doc_cau_hinh(env: dict | None = None) -> VultrConfig:
    src = os.environ if env is None else env
    return VultrConfig(
        api_key=str(src.get("LTT_VULTR_API_KEY", "")).strip(),
        vung=str(src.get("LTT_VPS_VUNG", "sgp")).strip() or "sgp",
    ).verify()


class VultrClient:
    """Client mỏng. `session` cho phép tiêm đối tượng giả lúc test — chỉ cần có
    `.request(method, url, **kwargs)` trả về thứ có `.status_code` và `.json()`."""

    def __init__(self, config: VultrConfig, *, session: Any = None,
                 timeout: Any = TIMEOUT_MAC_DINH):
        self.config = config
        self.timeout = timeout
        if session is None:
            import requests          # nhập lười: test tiêm session giả
            session = requests.Session()
        self._session = session

    # ── tầng vận chuyển ──────────────────────────────────────────────────────

    def _goi(self, method: str, duong_dan: str, *, body: dict | None = None) -> Any:
        try:
            r = self._session.request(
                method, f"{API}{duong_dan}",
                headers={"Authorization": f"Bearer {self.config.api_key}",
                         "Content-Type": "application/json"},
                data=json.dumps(body).encode() if body is not None else None,
                timeout=self.timeout,
            )
        except Exception as exc:      # lỗi mạng, DNS, TLS, timeout
            raise VultrError(f"{type(exc).__name__}: {exc}",
                             duong_dan=duong_dan) from exc

        status = getattr(r, "status_code", 0)
        if status == 401:
            # Đã mất một lần để biết: ngay sau khi tạo khoá, Vultr trả 401
            # "Unauthorized IP address" vì ACL chưa lan truyền, chứ không phải
            # khoá sai. Nói ra ở đây để lần sau không ai đi đổi khoá vô ích.
            raise VultrError(
                "Vultr tu choi (401) — khoa sai, HOAC danh sach IP nguon chua "
                "cho phep may nay, HOAC khoa vua tao chua lan truyen (doi vai giay)",
                status=401, duong_dan=duong_dan)
        if status >= 400:
            # Thân lỗi của Vultr là JSON, nhưng khi nó trả HTML (lỗi tầng biên,
            # trang bảo trì) thì `.json()` ném. Ta vẫn phải báo được mã lỗi, nên
            # lấy chuỗi thô làm phương án lui — KHÔNG nuốt lỗi, chỉ đổi nguồn
            # thông tin, và mã trạng thái luôn được ném lên ở dòng dưới.
            than = getattr(r, "text", "") or ""
            if than.lstrip().startswith("{"):
                chi_tiet = str((r.json() or {}).get("error", ""))[:200]
            else:
                chi_tiet = than.strip()[:200]
            raise VultrError(f"Vultr tra {status} {chi_tiet}".strip(),
                             status=status, duong_dan=duong_dan)
        if status == 204 or not getattr(r, "text", "1"):
            return {}
        try:
            return r.json()
        except ValueError as exc:
            # Bắt HẸP: `JSONDecodeError` của cả stdlib lẫn requests đều là
            # `ValueError`. `except Exception` ở đây sẽ nuốt cả lỗi lập trình.
            raise VultrError(f"Vultr tra ve khong phai JSON: {exc}",
                             status=status, duong_dan=duong_dan) from exc

    # ── đọc ──────────────────────────────────────────────────────────────────

    def tai_khoan(self) -> dict:
        """Dùng để kiểm khoá còn sống và xem còn bao nhiêu tiền."""
        return (self._goi("GET", "/account") or {}).get("account") or {}

    def danh_sach_ip(self) -> list:
        return (self._goi("GET", "/reserved-ips") or {}).get("reserved_ips") or []

    def doc_ip(self, ip_id: str) -> dict:
        return (self._goi("GET", f"/reserved-ips/{ip_id}") or {}).get("reserved_ip") or {}

    def instance_theo_nhan(self, nhan: str) -> dict:
        """Tìm instance theo nhãn. **Chỉ đọc** — driver này không xoá instance."""
        for i in (self._goi("GET", "/instances") or {}).get("instances") or []:
            if i.get("label") == nhan:
                return i
        raise VultrError(f"khong thay instance nao mang nhan {nhan!r}")

    def bang_thong(self, instance_id: str) -> dict:
        """Băng thông theo ngày của một instance, đơn vị byte.

        Đây là tài nguyên khan hiếm nhất của mô hình này: hạn mức của gateway
        chia cho **tất cả** khách. Xem `docs/VPS/GIAO_DIEN.md`.
        """
        bw = (self._goi("GET", f"/instances/{instance_id}/bandwidth")
              or {}).get("bandwidth") or {}
        ra = sum(int(v.get("outgoing_bytes", 0)) for v in bw.values())
        vao = sum(int(v.get("incoming_bytes", 0)) for v in bw.values())
        return {"ra_byte": ra, "vao_byte": vao, "tong_byte": ra + vao,
                "theo_ngay": bw}

    # ── vòng đời một IP ──────────────────────────────────────────────────────

    def tao_ip(self, nhan_ngan: str) -> dict:
        """Mua một IP mới. **KHÔNG idempotent** — đừng bọc trong vòng thử lại.

        Trả `{"id", "dia_chi", "nhan"}`.
        """
        nhan = f"{TIEN_TO_NHAN}{nhan_ngan}"
        kq = self._goi("POST", "/reserved-ips", body={
            "region": self.config.vung, "ip_type": "v4", "label": nhan,
        }) or {}
        ip = kq.get("reserved_ip") or {}
        if not ip.get("id") or not ip.get("subnet"):
            raise VultrError(f"Vultr tra ve IP thieu id/subnet: {ip!r}")
        return {"id": ip["id"], "dia_chi": ip["subnet"], "nhan": nhan}

    def gan_ip(self, ip_id: str, instance_id: str) -> None:
        self._goi("POST", f"/reserved-ips/{ip_id}/attach",
                  body={"instance_id": instance_id})

    def go_ip(self, ip_id: str) -> None:
        self._goi("POST", f"/reserved-ips/{ip_id}/detach")

    def xoa_ip(self, ip_id: str) -> None:
        """Trả IP về cho nhà cung cấp — tức **ngừng tính tiền**.

        Đọc lại nhãn trước khi xoá: một id truyền nhầm sẽ dừng ở đây thay vì xoá
        một IP đang phục vụ ai đó.

        ⚠️ Vultr giữ IP đã xoá **24 giờ** trước khi trả về kho chung, nên đừng
        trông chờ mua lại được đúng địa chỉ đó ngay.
        """
        ip = self.doc_ip(ip_id)
        nhan = str(ip.get("label") or "")
        if not nhan.startswith(TIEN_TO_NHAN):
            raise VultrError(
                f"tu choi xoa IP {ip.get('subnet') or ip_id}: nhan {nhan!r} khong "
                f"bat dau bang {TIEN_TO_NHAN!r} — no khong phai cua app nay")
        self._goi("DELETE", f"/reserved-ips/{ip_id}")


def client_tu_moi_truong(env: dict | None = None, *, session: Any = None
                         ) -> VultrClient:
    return VultrClient(doc_cau_hinh(env), session=session)
