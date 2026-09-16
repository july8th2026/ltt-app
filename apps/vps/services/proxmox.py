"""Driver nói chuyện với Proxmox VE. Đây là chỗ DUY NHẤT biết Proxmox tồn tại.

## Vì sao tự viết thay vì dùng `proxmoxer`

Kế hoạch ban đầu ghi `proxmoxer`. Đổi ý sau khi đọc kỹ, và ghi lại lý do để không
ai phải suy diễn:

* Proxmox là **REST/JSON thuần**; phần ta cần là ~10 endpoint. `proxmoxer` chủ yếu
  bọc chúng thành cú pháp thuộc tính (`px.nodes('pve').qemu.post(...)`) — tiện khi
  gõ tay, nhưng giấu mất đúng ba thứ **phải** kiểm soát chặt ở đây: **timeout**,
  **có được thử lại hay không**, và **thông báo lỗi**.
* Thêm một phụ thuộc nghĩa là thêm một thứ phải ghim phiên bản, phải cài trên máy
  chủ, và phải có mặt thì bộ test mới chạy — cho khoảng 200 dòng ta muốn tự kiểm.
* `requests` đã là phụ thuộc lõi của dự án.

## Hai quy tắc an toàn nằm trong chính lớp này

**1. KHÔNG tự thử lại POST.** Clone một VM không idempotent: thử lại một request
đã tới nơi nhưng mất phản hồi sẽ tạo **hai** máy — một cái mồ côi, ăn đĩa, không ai
biết. Chỉ `GET` mới được thử lại. Việc "chạy lại cho tới khi xong" là của hàng đợi
job, và nó phải kiểm trạng thái thật trước khi làm lại.

**2. Timeout luôn hữu hạn.** Không có timeout thì một Proxmox treo sẽ giữ worker
vĩnh viễn, và với vài tiến trình worker thì đó là dừng cả nền tảng — im lặng.

## Bí mật

Token đọc từ biến môi trường (`secrets/app.env`), không bao giờ vào git. Dùng
**API token có bật privilege separation**, không dùng `root@pam`: quyền của token
luôn là tập con quyền của user, nên một token rò rỉ vẫn bị chặn ở tầng thứ hai.

## Chứng chỉ TLS — và vì sao production KHÔNG được lùi

Proxmox cài mặc định dùng chứng chỉ tự ký. Đường gọi là **LAN nội bộ**
(`192.168.2.17` → `192.168.2.168`), cổng 8006 **không bao giờ** ra Internet.

Bản trước VPS V2 lập luận từ đó rằng thiếu CA thì **bỏ qua xác minh** và ghi một
dòng cảnh báo. Lập luận ấy có hai chỗ hỏng:

1. *"LAN nội bộ"* là một tính chất của **triển khai hôm nay**, không phải của mã.
   Ngày người ta dời Proxmox sang một mạng khác, hoặc dựng đường hầm qua một nhà
   cung cấp, câu ấy thôi đúng — và không có gì kêu lên;
2. một dòng `log.warning` phát **một lần mỗi tiến trình** là một dòng không ai
   đọc. Nó không chặn được gì, nên nó không phải một hàng rào; nó là một ghi chú.

⇒ Từ VPS V2: `LTT_ENV=production` **và** không có CA ⇒ `ChuaCauHinh`, fail-closed.
Ngoài production thì vẫn chạy được, nhưng phải **khai tường minh**
`LTT_VPS_PROXMOX_TLS_BO_QUA=1` — một biến có tên nói đúng thứ nó làm, để không ai
bỏ qua xác minh mà không biết mình đang bỏ qua.

`san_sang_tls()` là phép kiểm để `/health/ready` gọi: nó trả lời câu *"cấu hình
này có phát hành được không"* mà không cần chạm mạng.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

#: Timeout mặc định (giây): (nối, đọc). Đọc dài hơn vì `clone` trả về sau khi
#: Proxmox đã nhận việc, không phải sau khi clone xong.
TIMEOUT_MAC_DINH = (5, 30)

#: Cổng mặc định của giao diện/API Proxmox.
CONG_MAC_DINH = 8006

_DA_CANH_BAO_TLS = False


class ProxmoxError(RuntimeError):
    """Mọi lỗi khi nói chuyện với Proxmox. Mang theo mã HTTP nếu có."""

    def __init__(self, thong_diep: str, *, status: int | None = None,
                 duong_dan: str = ""):
        super().__init__(thong_diep)
        self.status = status
        self.duong_dan = duong_dan


class ChuaCauHinh(ProxmoxError):
    """Thiếu biến môi trường. Tách riêng để routes phân biệt được với lỗi mạng."""


#: Biến bật đường bỏ qua xác minh TLS. Tên nói đúng thứ nó làm — cố ý.
#:
#: Một biến tên `LTT_VPS_PROXMOX_CA` để trống thì im lặng; một biến tên
#: `..._TLS_BO_QUA=1` thì người đặt nó biết mình vừa làm gì, và người đọc
#: `app.env` sau này cũng biết.
KHOA_BO_QUA_TLS = "LTT_VPS_PROXMOX_TLS_BO_QUA"


@dataclass(frozen=True)
class ProxmoxConfig:
    """Cấu hình kết nối. Đọc từ môi trường, không bao giờ từ CSDL hay code."""

    base_url: str
    token_id: str
    token_secret: str
    node: str = "pve"
    ca_bundle: str = ""
    #: DNS identity on the certificate when the transport URL intentionally
    #: uses a management IP that is not present in the certificate SAN.
    tls_name: str = ""
    #: Đã khai tường minh là chấp nhận không xác minh TLS. **Chỉ ngoài production.**
    bo_qua_tls: bool = False

    def __str__(self) -> str:
        """Không bao giờ in `token_secret`.

        `repr()` là thứ lọt vào traceback, log gỡ lỗi và Sentry — im lặng, và
        đúng vào lúc có sự cố nên có nhiều người đang đọc log nhất.
        """
        return (f"ProxmoxConfig({self.base_url} node={self.node} "
                f"token={self.token_id} ca={'co' if self.ca_bundle else 'khong'})")

    __repr__ = __str__

    @property
    def verify(self) -> Any:
        """Giá trị `verify` cho `requests`: đường dẫn CA, hoặc `False`.

        Tới được đây nghĩa là `doc_cau_hinh` đã cho phép — production không có CA
        thì đã ném từ lúc dựng cấu hình, không phải lúc gọi mạng. Đặt hàng rào ở
        chỗ **dựng** thay vì chỗ **dùng** là để nó nổ một lần lúc khởi động, thay
        vì nổ giữa một lần khôi phục dữ liệu của khách.
        """
        global _DA_CANH_BAO_TLS
        if self.ca_bundle:
            return self.ca_bundle
        if not _DA_CANH_BAO_TLS:
            _DA_CANH_BAO_TLS = True
            log.warning(
                "Proxmox: KHONG xac minh chung chi TLS — %s da duoc khai. "
                "Chi chap nhan duoc ngoai production.", KHOA_BO_QUA_TLS)
        return False


def doc_cau_hinh(env: dict | None = None) -> ProxmoxConfig:
    """Dựng cấu hình từ môi trường. Thiếu thứ bắt buộc → `ChuaCauHinh`.

    Ném lỗi rõ ràng chứ không trả về cấu hình rỗng: một client trỏ vào `""` sẽ
    hỏng ở tận tầng mạng với thông báo vô nghĩa.
    """
    src = os.environ if env is None else env

    url = str(src.get("LTT_VPS_PROXMOX_URL", "")).strip().rstrip("/")
    token_id = str(src.get("LTT_VPS_PROXMOX_TOKEN_ID", "")).strip()
    secret = str(src.get("LTT_VPS_PROXMOX_TOKEN_SECRET", "")).strip()
    node = str(src.get("LTT_VPS_PROXMOX_NODE", "pve")).strip() or "pve"
    ca = str(src.get("LTT_VPS_PROXMOX_CA", "")).strip()
    tls_name = str(src.get("LTT_VPS_PROXMOX_TLS_NAME", "")).strip()
    labels = tls_name.split(".")
    if tls_name and (
        len(tls_name) > 253
        or not all(
            part
            and len(part) <= 63
            and part[0].isalnum()
            and part[-1].isalnum()
            and part.replace("-", "").isalnum()
            for part in labels
        )
    ):
        raise ChuaCauHinh("LTT_VPS_PROXMOX_TLS_NAME khong hop le")

    thieu = [ten for ten, gt in (
        ("LTT_VPS_PROXMOX_URL", url),
        ("LTT_VPS_PROXMOX_TOKEN_ID", token_id),
        ("LTT_VPS_PROXMOX_TOKEN_SECRET", secret),
    ) if not gt]
    if thieu:
        raise ChuaCauHinh("thieu bien moi truong: " + ", ".join(thieu))

    if "!" not in token_id:
        # Dạng đúng là `user@realm!tenToken`. Sai dạng thì Proxmox trả 401 với
        # thông báo chung chung — bắt ở đây để khỏi mất một giờ dò.
        raise ChuaCauHinh(
            "LTT_VPS_PROXMOX_TOKEN_ID phai co dang 'user@realm!tenToken'")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    bo_qua = str(src.get(KHOA_BO_QUA_TLS, "")).strip().lower() in (
        "1", "true", "yes", "co")
    thieu_tls = _ly_do_tls_khong_dat(url, ca, bo_qua, src)
    if thieu_tls:
        raise ChuaCauHinh(thieu_tls)

    return ProxmoxConfig(base_url=url, token_id=token_id, token_secret=secret,
                         node=node, ca_bundle=ca, tls_name=tls_name,
                         bo_qua_tls=bo_qua)


def _ly_do_tls_khong_dat(url: str, ca: str, bo_qua: bool,
                         src) -> str:
    """Lý do cấu hình TLS này **không** dùng được, hoặc chuỗi rỗng.

    Tách khỏi `doc_cau_hinh` để `san_sang_tls()` hỏi được cùng một câu mà không
    phải dựng cấu hình — hai nơi hỏi cùng một câu bằng hai đoạn mã là hai câu trả
    lời sẽ lệch nhau.
    """
    from platform_core.settings import Environment, resolve_environment

    if ca or not url.startswith("https://"):
        # `http://` không có gì để xác minh — nó là một vấn đề khác, và nó đã bị
        # chặn ở chỗ khác (cổng 8006 của Proxmox luôn là HTTPS).
        return ""
    try:
        moi_truong = resolve_environment(src if isinstance(src, dict) else None)
    except Exception as exc:                     # noqa: BLE001
        # `LTT_ENV` lạ ⇒ coi như production. Đoán về phía an toàn: một lỗi gõ
        # phím trong biến môi trường không được mở ra một đường không xác minh.
        #
        # **Và phải kêu lên.** Nuốt im lặng ở đây nghĩa là một máy chủ gõ nhầm
        # `LTT_ENV` sẽ từ chối nối Proxmox mà không nói vì sao — người vận hành
        # đi tìm lỗi TLS trong khi lỗi thật nằm ở một chữ cái.
        log.warning("Proxmox: khong doc duoc ho so moi truong (%s) — coi nhu "
                    "production va doi CA that.", exc)
        moi_truong = Environment.PRODUCTION
    if moi_truong is Environment.PRODUCTION:
        return (f"production ma khong co {'LTT_VPS_PROXMOX_CA'}: tu choi noi toi "
                f"Proxmox khi khong xac minh duoc chung chi. Ghim CA that, "
                f"hoac chay o moi truong khac.")
    if not bo_qua:
        return (f"khong co LTT_VPS_PROXMOX_CA. Ngoai production van chay duoc, "
                f"nhung phai khai tuong minh {KHOA_BO_QUA_TLS}=1 de khong ai "
                f"bo qua xac minh ma khong biet.")
    return ""


def san_sang_tls(env: dict | None = None) -> tuple[bool, str]:
    """Cấu hình TLS hiện tại có phát hành được không, và vì sao không.

    Dành cho `/health/ready`. **Không chạm mạng** — nó trả lời câu hỏi về *cấu
    hình*, và một phép kiểm sẵn sàng gọi ra ngoài là một phép kiểm sẽ đỏ vì
    những lý do không liên quan tới nó.
    """
    src = os.environ if env is None else env
    url = str(src.get("LTT_VPS_PROXMOX_URL", "")).strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    ca = str(src.get("LTT_VPS_PROXMOX_CA", "")).strip()
    bo_qua = str(src.get(KHOA_BO_QUA_TLS, "")).strip().lower() in (
        "1", "true", "yes", "co")
    ly_do = _ly_do_tls_khong_dat(url, ca, bo_qua, src)
    return (not ly_do), ly_do


class ProxmoxClient:
    """Client mỏng. Mỗi phương thức là một endpoint, không có phép màu nào.

    `session` cho phép tiêm một đối tượng giả lúc test — nhờ đó toàn bộ tầng trên
    kiểm được mà không cần một cụm Proxmox thật. Đối tượng đó chỉ cần có
    `.request(method, url, **kwargs)` trả về thứ có `.status_code` và `.json()`.
    """

    def __init__(self, config: ProxmoxConfig, *, session: Any = None,
                 timeout: Any = TIMEOUT_MAC_DINH):
        self.config = config
        self.timeout = timeout
        if session is None:
            import requests  # nhập lười: test tiêm session giả thì không cần
            session = requests.Session()
            if config.tls_name:
                from requests.adapters import HTTPAdapter

                class _ExactTlsNameAdapter(HTTPAdapter):
                    def init_poolmanager(self, connections, maxsize, block=False,
                                         **pool_kwargs):
                        pool_kwargs["assert_hostname"] = config.tls_name
                        return super().init_poolmanager(
                            connections, maxsize, block=block, **pool_kwargs)

                session.mount("https://", _ExactTlsNameAdapter())
        self._session = session

    # ── tầng vận chuyển ──────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization":
                f"PVEAPIToken={self.config.token_id}={self.config.token_secret}",
            "Accept": "application/json",
        }

    def _goi(self, method: str, duong_dan: str, *, data: dict | None = None,
             params: dict | None = None) -> Any:
        """Gọi một endpoint. Trả về phần `data` trong phản hồi của Proxmox.

        Không thử lại gì cả — kể cả GET. Việc thử lại thuộc về người gọi, vì chỉ
        người gọi biết thao tác đó có an toàn khi lặp không.

        **`params` chứ không phải `data` cho `DELETE`.** Proxmox trả **501 Not
        Implemented** khi tham số của `DELETE` nằm trong thân request — thông báo
        đó không nói gì về nguyên nhân, và đã tốn một lần thử thật để tìm ra.
        Tham số của `DELETE` (và `GET`) phải đi ở query string.
        """
        url = f"{self.config.base_url}/api2/json{duong_dan}"
        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode({k: v for k, v in params.items() if v is not None})}"
        try:
            r = self._session.request(
                method, url,
                headers=self._headers(),
                data=data or None,
                timeout=self.timeout,
                verify=self.config.verify,
            )
        except Exception as exc:      # lỗi mạng, DNS, TLS, timeout
            raise ProxmoxError(f"{type(exc).__name__}: {exc}",
                               duong_dan=duong_dan) from exc

        status = getattr(r, "status_code", 0)
        if status == 401:
            raise ProxmoxError("Proxmox tu choi token (401) — kiem token_id/secret "
                               "va quyen tren duong dan", status=401,
                               duong_dan=duong_dan)
        if status == 403:
            raise ProxmoxError("Proxmox tu choi quyen (403) — token thieu quyen tren "
                               "duong dan nay", status=403, duong_dan=duong_dan)
        if status >= 400:
            raise ProxmoxError(f"Proxmox tra {status}", status=status,
                               duong_dan=duong_dan)

        try:
            body = r.json()
        except Exception as exc:
            raise ProxmoxError("Proxmox tra ve khong phai JSON",
                               status=status, duong_dan=duong_dan) from exc
        if not isinstance(body, dict):
            raise ProxmoxError("Proxmox tra ve JSON khong phai object",
                               status=status, duong_dan=duong_dan)
        return body.get("data")

    # ── đọc ──────────────────────────────────────────────────────────────────

    def phien_ban(self) -> dict:
        """`/version` — dùng để kiểm đường nối còn sống và token còn hiệu lực."""
        return self._goi("GET", "/version") or {}

    def trang_thai_node(self) -> dict:
        """CPU/RAM/uptime của node. Nguồn số thật cho `capacity.py`."""
        return self._goi("GET", f"/nodes/{self.config.node}/status") or {}

    def kho_luu_tru(self) -> list:
        """Danh sách kho + dung lượng. Đây là chỗ biết còn bao nhiêu đĩa để bán."""
        return self._goi("GET", f"/nodes/{self.config.node}/storage") or []

    def danh_sach_vm(self) -> list:
        """Mọi VM trên node, kèm `vmid`, `status`, `maxmem`, `maxdisk`."""
        return self._goi("GET", f"/nodes/{self.config.node}/qemu") or []

    def trang_thai_vm(self, vmid: int) -> dict:
        """Trạng thái **hiện tại** của một VM: `status`, `qmpstatus`, `uptime`…

        Đây là *authority* về nguồn điện của máy — CSDL chỉ giữ một quan sát gần
        đây, không giữ sự thật. Trước VPS V2 không ai gọi endpoint này: mọi thứ
        suy từ chỗ ta vừa gửi lệnh gì, tức suy từ **ý định**.

        Đọc riêng từng máy thay vì lọc `danh_sach_vm()`: danh sách trả về cả
        chục VM của chủ nhà và tốn một lần duyệt cho một câu hỏi về một máy — mà
        vòng chờ ở `services/tac_vu.py` hỏi câu đó vài lần mỗi giây.
        """
        return self._goi(
            "GET",
            f"/nodes/{self.config.node}/qemu/{int(vmid)}/status/current") or {}

    def vmid_ke_tiep(self) -> int:
        """Số VMID trống theo Proxmox.

        **Chỉ là gợi ý.** Hai job song song hỏi cùng lúc sẽ nhận cùng một số; chốt
        thật nằm ở ràng buộc duy nhất trên `vps_instance.vmid`.
        """
        return int(self._goi("GET", "/cluster/nextid"))

    # ── ghi ──────────────────────────────────────────────────────────────────

    def clone(self, vmid_nguon: int, vmid_moi: int, *, ten: str,
              full: bool = False, storage: str = "") -> str:
        """Nhân bản một template. Trả về UPID của tác vụ nền.

        `full=False` là **linked clone**: máy mới chỉ lưu phần chênh so với
        template. Với catalog toàn Windows (mỗi template 20–25 GB) thì đây là
        khác biệt giữa bán được vài máy và bán được vài chục.
        """
        data: dict = {"newid": int(vmid_moi), "name": ten,
                      "full": 1 if full else 0}
        if storage:
            data["storage"] = storage
        return str(self._goi(
            "POST", f"/nodes/{self.config.node}/qemu/{int(vmid_nguon)}/clone",
            data=data))

    def tao_may(self, vmid: int, **cau_hinh) -> str:
        """Tạo một máy TRỐNG với cấu hình cho trước. Trả UPID.

        Dùng cho mô hình **khách tự cài**: máy sinh ra không có hệ điều hành,
        chỉ có đĩa trắng và một đĩa cài đặt gắn sẵn.

        **KHÔNG idempotent.** Gọi lại khi VMID đã tồn tại thì Proxmox trả lỗi —
        và đó là hành vi đúng: người gọi phải hỏi thế giới thật trước, y như với
        `clone`. Xem `_vm_da_ton_tai` trong `jobs.py`.
        """
        return str(self._goi("POST", f"/nodes/{self.config.node}/qemu",
                             data={"vmid": int(vmid), **cau_hinh}))

    def dat_cau_hinh(self, vmid: int, **cau_hinh) -> Any:
        """Đặt cấu hình VM (`cores`, `memory`, `net0`, `ipconfig0`, `ciuser`…)."""
        return self._goi("POST",
                         f"/nodes/{self.config.node}/qemu/{int(vmid)}/config",
                         data={k: v for k, v in cau_hinh.items() if v is not None})

    def nong_dia(self, vmid: int, dia: str, them: str) -> Any:
        """Nới một đĩa của VM. `them` dạng `+20G`. Proxmox không cho thu nhỏ."""
        return self._goi("PUT",
                         f"/nodes/{self.config.node}/qemu/{int(vmid)}/resize",
                         data={"disk": dia, "size": them})

    def bat(self, vmid: int) -> str:
        return str(self._goi(
            "POST", f"/nodes/{self.config.node}/qemu/{int(vmid)}/status/start"))

    def tat_mem(self, vmid: int) -> str:
        """Tắt máy tử tế (gửi ACPI). Dùng khi treo máy vì hết credit."""
        return str(self._goi(
            "POST", f"/nodes/{self.config.node}/qemu/{int(vmid)}/status/shutdown"))

    def tat_cung(self, vmid: int) -> str:
        """Cắt điện. Chỉ dùng khi `tat_mem` đã hết hạn chờ."""
        return str(self._goi(
            "POST", f"/nodes/{self.config.node}/qemu/{int(vmid)}/status/stop"))

    def xoa(self, vmid: int, *, xoa_luon_dia: bool = True) -> str:
        """Xoá VM. Không hoàn tác được — người gọi phải chắc đã tới mốc V8.

        `purge=1` gỡ luôn khỏi mọi cấu hình sao lưu/replication, để không còn
        tham chiếu mồ côi trỏ tới một VM đã biến mất.
        """
        return str(self._goi(
            "DELETE", f"/nodes/{self.config.node}/qemu/{int(vmid)}",
            params={"purge": 1,
                    "destroy-unreferenced-disks": 1 if xoa_luon_dia else 0}))

    def ve_console(self, vmid: int) -> dict:
        """Vé VNC dùng-một-lần cho console trong trình duyệt.

        Vé này đi tới **proxy WebSocket của mình**, không bao giờ tới trình duyệt
        khách kèm địa chỉ Proxmox: khách chạm được cổng 8006 là mất cả cụm.
        """
        return self._goi(
            "POST", f"/nodes/{self.config.node}/qemu/{int(vmid)}/vncproxy",
            data={"websocket": 1}) or {}

    # ── Ảnh chụp (snapshot) ──────────────────────────────────────────────────
    #
    # Ảnh chụp trên LVM-thin gần như **không tốn chỗ** lúc tạo (chỉ khối nào đổi
    # về sau mới chiếm), và tạo xong trong vài giây. Đó là lý do nó dùng được cho
    # mọi máy hằng tuần trong khi `vzdump` thì không — kho `local` chỉ còn 2,2 GiB.
    #
    # ⚠️ **Ảnh chụp KHÔNG phải bản sao lưu.** Nó nằm trên **cùng kho** với đĩa
    # gốc: pool hỏng là mất cả hai. Nó cứu khách khỏi *lỗi của chính họ* (xoá
    # nhầm, bản vá hỏng), không cứu khỏi hỏng phần cứng. Trang bán phải nói đúng
    # như vậy — xem `vps.html`.
    #
    # Máy khách không có guest agent (agent là thiết bị virtio, và virtio treo
    # trên cụm này), nên ảnh chụp là **crash-consistent**: giống như rút điện
    # rồi bật lại. NTFS có nhật ký nên thường lên bình thường, nhưng cơ sở dữ
    # liệu đang ghi dở thì không có gì bảo đảm.

    def danh_sach_anh(self, vmid: int) -> list:
        """Ảnh chụp của một máy. Proxmox luôn trả thêm mục giả `current`."""
        ra = self._goi("GET", f"/nodes/{self.config.node}/qemu/{int(vmid)}/snapshot")
        return [x for x in (ra or []) if str(x.get("name")) != "current"]

    def chup_anh(self, vmid: int, ten: str, *, mo_ta: str = "") -> str:
        """Tạo ảnh chụp. **Không** kèm RAM: `vmstate` ghi cả bộ nhớ ra đĩa, tức
        thêm vài GB mỗi máy mỗi tuần cho một thứ không ai cần khi khôi phục."""
        return self._goi(
            "POST", f"/nodes/{self.config.node}/qemu/{int(vmid)}/snapshot",
            data={"snapname": ten, "description": mo_ta, "vmstate": 0})

    def xoa_anh(self, vmid: int, ten: str) -> str:
        return self._goi(
            "DELETE",
            f"/nodes/{self.config.node}/qemu/{int(vmid)}/snapshot/{ten}")

    def khoi_phuc_anh(self, vmid: int, ten: str) -> str:
        """Quay máy về một ảnh chụp. **Không hoàn tác được** — mọi thay đổi sau
        thời điểm chụp mất hết. Người gọi phải bắt khách xác nhận."""
        return self._goi(
            "POST",
            f"/nodes/{self.config.node}/qemu/{int(vmid)}/snapshot/{ten}/rollback")

    def trang_thai_tac_vu(self, upid: str) -> dict:
        """Tác vụ nền (clone, xoá) đã xong chưa. `status`/`exitstatus`."""
        return self._goi(
            "GET", f"/nodes/{self.config.node}/tasks/{upid}/status") or {}


def client_tu_moi_truong(env: dict | None = None, *, session: Any = None
                         ) -> ProxmoxClient:
    """Đường tắt hay dùng: đọc môi trường rồi dựng client."""
    return ProxmoxClient(doc_cau_hinh(env), session=session)
