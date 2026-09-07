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

import logging
import time
from enum import Enum
from typing import Any, Callable

_log = logging.getLogger(__name__)

#: Đo 06/09: ~40 giây container + ~40 giây apt + ~450 giây nạp/ghim model ở
#: profile 1 ⇒ ~530 giây. Cộng biên cho lượt cài lại nửa tạm và ổ mạng chậm.
#: Số đo ở `docs/VIDEO_AI_V2/DU_LIEU_DA_DO.md` §4 — đừng chép nó đi nơi khác.
CHO_TOI_DA_S: float = 900.0

#: Nhịp hỏi `/health`. Đủ thưa để không đập vào proxy, đủ dày để không phí phút.
NHIP_S: float = 10.0

#: Rảnh bao lâu thì tắt máy. `B1` chốt "bật theo nhu cầu, tắt khi rảnh", nhưng
#: **tắt ngay khi sổ rỗng là sai**: khởi động lại tốn ~9 phút (`DU_LIEU_DA_DO`
#: §4) và mang rủi ro không thuê lại được card (06/09: hơn một tiếng).
#:
#: ⭐ Chọn 15 phút vì nó **lớn hơn** khoảng nghỉ tự nhiên giữa hai lượt của cùng
#:    một người (xem kết quả rồi gõ prompt tiếp), và **nhỏ hơn nhiều** so với
#:    tiền một giờ máy. Đây là một đánh đổi, không phải một hằng số tự nhiên —
#:    đo lại khi có nhịp dùng thật.
NGHI_TAT_SAU_S: float = 15 * 60.0

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
                 nghi_tat_sau_s: float = NGHI_TAT_SAU_S,
                 ngu: Callable[[float], None] = time.sleep) -> None:
        self.api = api
        self.pod_id = pod_id
        self.client = client
        self.cho_toi_da_s = cho_toi_da_s
        self.nhip_s = nhip_s
        self.nghi_tat_sau_s = nghi_tat_sau_s
        self._ngu = ngu          # tiêm được ⇒ phép kiểm không tốn thời gian thật

    # ── đọc ──

    def _trang_thai_pod(self) -> str:
        try:
            d = self.api.rest("GET", f"/pods/{self.pod_id}")
        except Exception as e:  # noqa: BLE001 — đọc không được thì coi như chưa chạy
            # ⛔ Không nuốt: một lỗi mạng lặp lại ở đây là dấu hiệu khoá RunPod
            #    hỏng hoặc pod đã bị xoá, và nếu nó im lặng thì triệu chứng duy
            #    nhất là "máy mãi không lên" — đúng chỗ khó tìm nhất.
            _log.warning("khong doc duoc trang thai pod %s: %s: %s",
                         self.pod_id, type(e).__name__, e)
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
                self.api.rest("POST", f"/pods/{self.pod_id}/start")
            except Exception as e:  # noqa: BLE001
                thong_diep = str(e).lower()
                if any(d in thong_diep for d in _DAU_HIEU_HET_CARD):
                    return TrangThaiMay.KHONG_CO_CARD
                raise

        het_han = time.monotonic() + self.cho_toi_da_s
        loi_cuoi = ""
        while time.monotonic() < het_han:
            try:
                if (self.client.health() or {}).get("ok"):
                    return TrangThaiMay.SAN_SANG
            except Exception as e:  # noqa: BLE001 — chưa lên thì hỏi lại
                # ⛔ Giữ lỗi CUỐI thay vì nuốt. Một lượt hỏi hỏng là bình thường
                #    (máy đang lên); nhưng khi hết giờ thì lỗi cuối là câu trả
                #    lời duy nhất cho "vì sao không lên" — và nếu ta nuốt nó thì
                #    người vận hành chỉ còn một dòng "hết giờ" không kèm gì.
                loi_cuoi = f"{type(e).__name__}: {e}"
            self._ngu(self.nhip_s)
        # ⚠️ Hết giờ ≠ hết card. Máy có thể đang chạy mà dịch vụ hỏng — nên trả
        #    `TAT` (không phục vụ được) chứ không trả `KHONG_CO_CARD`.
        _log.warning("pod %s khong san sang sau %.0f giay; loi cuoi: %s",
                     self.pod_id, self.cho_toi_da_s, loi_cuoi or "(khong co)")
        return TrangThaiMay.TAT

    def nen_tat(self, *, so_viec_dang_chay: int,
                giay_ke_tu_viec_cuoi: float | None) -> bool:
        """Có nên tắt máy lúc này không? **Chỉ quyết định, không hành động.**

        ⭐ Tách quyết định khỏi hành động để phép kiểm hỏi được câu *"nó có
           định tắt không"* mà không cần một `api` giả nào — và để chỗ gọi có
           thể ghi log lý do trước khi tiêu một lệnh đắt.

        Hai điều kiện, **và**:
        - sổ rỗng;
        - lần cuối có việc đã quá `NGHI_TAT_SAU_S`.

        ⛔ Vế thứ hai không thừa. Giữa hai job liên tiếp của cùng một người
           dùng, sổ **có lúc rỗng** trong vài giây. Tắt ngay lúc ấy là bắt họ
           trả lại **9 phút** khởi động cho lượt kế — và gánh rủi ro không thuê
           lại được card.
        """
        if so_viec_dang_chay < 0:
            raise ValueError("so_viec_dang_chay must not be negative")
        if so_viec_dang_chay > 0:
            return False
        if giay_ke_tu_viec_cuoi is None:
            # Chua tung co viec nao => khong co gi de cho.
            return True
        return giay_ke_tu_viec_cuoi >= self.nghi_tat_sau_s

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
        self.api.rest("POST", f"/pods/{self.pod_id}/stop")
        return True
