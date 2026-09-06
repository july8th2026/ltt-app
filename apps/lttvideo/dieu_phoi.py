"""Điều phối vòng đời pod C-CLOUD: bật khi có việc, tắt khi rảnh (`B1`).

⭐ **Vì sao thành phần này được xây, trong khi 12 lớp khác bị xoá ở lượt audit.**
   Lượt audit xoá mọi lớp *diễn giải lại thứ WanGP đã làm*. Chỗ này thì ngược
   lại: **WanGP không biết gì về RunPod** — nó không biết máy có thể tắt, không
   biết card có thể hết, không biết một giờ tốn bao nhiêu. Kiến thức ấy không
   có ở thượng nguồn, nên nó phải sống ở đâu đó, và đây là chỗ.

⛔ Lớp này **không** biết credit, người dùng, hay job. Nó chỉ trả lời đúng hai
   câu: *"máy sẵn sàng chưa"* và *"tắt được chưa"*. Ai hoàn tiền là việc của
   `jobs.handle`.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable

#: Đo 06/09: ~40 giây container + ~40 giây apt + ~450 giây nạp/ghim model ở
#: profile 1 ⇒ ~530 giây. Cộng biên cho lượt cài lại nửa tạm và ổ mạng chậm.
#: Số đo ở `docs/VIDEO_AI_V2/DU_LIEU_DA_DO.md` §4 — đừng chép nó đi nơi khác.
CHO_TOI_DA_S: float = 900.0

#: Nhịp hỏi `/health`. Đủ thưa để không đập vào proxy, đủ dày để không phí phút.
NHIP_S: float = 10.0

#: Dấu hiệu RunPod dùng khi hết GPU. ⚠️ Đây là **so chuỗi trên lỗi của bên thứ
#: ba** — thứ có thể đổi mà không báo. Nên nó chỉ dùng để PHÂN LOẠI, và nhánh
#: mặc định là "hỏng thật", tức phía an toàn: hoàn tiền cho khách.
_DAU_HIEU_HET_CARD = ("not enough free gpu", "no gpu", "insufficient")


class TrangThaiMay(str, Enum):
    TAT = "tat"
    SAN_SANG = "san_sang"
    KHONG_CO_CARD = "khong_co_card"


class DieuPhoi:
    def __init__(self, *, api: Any, pod_id: str, client: Any,
                 cho_toi_da_s: float = CHO_TOI_DA_S,
                 nhip_s: float = NHIP_S,
                 ngu: Callable[[float], None] = time.sleep) -> None:
        self.api = api
        self.pod_id = pod_id
        self.client = client
        self.cho_toi_da_s = cho_toi_da_s
        self.nhip_s = nhip_s
        self._ngu = ngu          # tiêm được ⇒ phép kiểm không tốn thời gian thật

    # ── đọc ──

    def _trang_thai_pod(self) -> str:
        try:
            d = self.api._rest("GET", f"/pods/{self.pod_id}")
        except Exception:  # noqa: BLE001 — không đọc được thì coi như chưa chạy
            return "?"
        return str((d or {}).get("desiredStatus") or "?")

    # ── ghi ──

    def bat_va_cho(self) -> TrangThaiMay:
        """Bật pod nếu cần, rồi chờ `/health` trả lời.

        ⛔ Trả **trạng thái**, không ném ngoại lệ khi hết card: `B3` cần hoàn
           credit, mà muốn hoàn thì người gọi phải *nhận được* câu trả lời chứ
           không phải đi bắt chuỗi trong một `RuntimeError`.
        """
        if self._trang_thai_pod() != "RUNNING":
            try:
                self.api._rest("POST", f"/pods/{self.pod_id}/start")
            except Exception as e:  # noqa: BLE001
                thong_diep = str(e).lower()
                if any(d in thong_diep for d in _DAU_HIEU_HET_CARD):
                    return TrangThaiMay.KHONG_CO_CARD
                raise

        het_han = time.monotonic() + self.cho_toi_da_s
        while time.monotonic() < het_han:
            try:
                if (self.client.health() or {}).get("ok"):
                    return TrangThaiMay.SAN_SANG
            except Exception:  # noqa: BLE001 — chưa lên thì hỏi lại, đúng nghĩa
                pass
            self._ngu(self.nhip_s)
        # ⚠️ Hết giờ ≠ hết card. Máy có thể đang chạy mà dịch vụ hỏng — nên trả
        #    `TAT` (không phục vụ được) chứ không trả `KHONG_CO_CARD`.
        return TrangThaiMay.TAT

    def tat_neu_ranh(self, *, so_viec_dang_chay: int) -> bool:
        """Tắt pod **chỉ khi** sổ rỗng. Trả `True` nếu đã gửi lệnh tắt.

        ⛔ Tắt giữa một lượt sinh là mất cả video lẫn tiền của khách — và
           `POST /stop` **nhả card**, nên có thể không thuê lại được (06/09: hơn
           một giờ). Đây là lệnh đắt nhất trong tệp này.
        """
        if so_viec_dang_chay < 0:
            raise ValueError("so_viec_dang_chay must not be negative")
        if so_viec_dang_chay > 0:
            return False
        self.api._rest("POST", f"/pods/{self.pod_id}/stop")
        return True
