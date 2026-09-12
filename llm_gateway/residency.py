"""
residency.py — cơ chế của ba lệnh residency phía cổng LLM. (Dual-model 5.4b)

⭐ ĐÂY LÀ **LỆNH**, KHÔNG PHẢI **QUYẾT ĐỊNH**. Ai được cầm 3090 lúc nào là việc
   của **trọng tài residency ở máy A** (Task 5.5, TD-D10) — nơi duy nhất thấy
   cùng lúc lease LLM, phòng chờ và hàng job ảnh. Cổng này chỉ thi hành và **báo
   lại sự thật đo được**. Đó chính là điều D01 B chốt: **một** trọng tài, không
   phải hai cơ chế cùng canh một card rồi lệch nhau.

🔴 VÌ SAO NHẢ **THEO TÊN MODEL** — ĐO ĐƯỢC 12/09/2026 TRÊN CHÍNH MÁY B (L-17).
   Một `llama-swap` thứ hai ở cổng 8390, hai hồ sơ giả (không chạm 3090):

       POST /api/models/unload/<model>   ->  /running mat DUNG mot cai
       GET  /unload                      ->  /running = []   (nha HET)
       POST /api/models/unload           ->  /running = []   (nha HET)

   Hai đường không tham số là lý do trọng tài cũ phải đi: từ khi máy B có hai
   model, chúng giết luôn LTT-3.5 trên card **không ai tranh** — ~38 lần/ngày
   theo lưu lượng 28 ngày. Bài học hình dạng của L-17: *một lệnh không mang tên
   đối tượng thì nó chỉ đúng khi hệ thống có đúng một đối tượng.*

⛔ VÀ KHÔNG BAO GIỜ GIẾT VIỆC ĐANG CHẠY (L-9). `nha` khi còn suất đang bay là
   **409**, hết câu — không "chờ một tí rồi ép", không hạn chờ leo thang. Việc
   drain là của máy A: ngừng nhận ⇒ chờ về 0 ⇒ rồi mới gọi. `unload` thủ công của
   llama-swap **không** drain (`fifo.go:222-270`), nên một lệnh nhả phát ra lúc
   còn in-flight là một lượt của khách bị cắt giữa chừng.

⛔ THÀNH CÔNG IM LẶNG LÀ KẾT CỤC TỆ NHẤT — cùng kỷ luật với `/v1/nha_comfy` của
   cổng render (5.4a). Một bước residency **tưởng** đã nhả card mà thật ra chưa
   là đúng hỏng hóc mà D01 B sinh ra để chặn. Nên mọi đường ra ở đây hoặc mang
   theo **số đo**, hoặc nói rõ điều kiện nào hỏng và với con số nào.
"""
from __future__ import annotations

import json as _json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import quote

log = logging.getLogger("llm_gateway.residency")

# ── Ba giá trị của `nap_ket_qua` ─────────────────────────────────────────────
#
# 🔴 `CHUA` KHÔNG PHẢI "CHƯA BAO GIỜ NẠP" — nó là *"lượt nạp GẦN NHẤT chưa có
#    kết quả"*. Hợp đồng ở `platform_core/llm/residency.QuanSat.nap_ket_qua`.
CHUA = ""
OK = "ok"
LOI = "loi"

#: Đường nhả **theo tên model** của llama-swap (đo 12/09, L-17 §🟢).
DUONG_NHA = "/api/models/unload/"
#: Đường hỏi model nào đang nằm trong VRAM.
DUONG_RUNNING = "/running"
#: llama-swap định tuyến `/upstream/<model>/…` tới đúng server của hồ sơ ấy —
#: cùng khuôn `_dem_token_that` đã dùng cho `/tokenize`.
DUONG_UPSTREAM = "/upstream/"

#: Trạng thái llama-swap dùng cho "hồ sơ đã nằm trong VRAM và phục vụ được".
SAN_SANG = "ready"

# ── Hạn giờ: đều là CHỐT CHẶN của tầng vận chuyển, không phải phép đo ────────
#
# ⚠️ Bộ nhớ dự án: *"ngưỡng thời gian của công cụ không phải phép đo"*. Ba con số
#    dưới đây không nói gì về máy B chạy nhanh chậm ra sao; chúng chỉ bảo đảm
#    không có lời gọi nào treo vô hạn và giữ một luồng nền mãi mãi.

#: Một lệnh điều khiển llama-swap (`unload`, `/running`, `/health`). Rộng hơn hẳn
#: mức thường (đo: mili-giây) mà vẫn ngắn hơn nhịp 2 s của trọng tài nhân vài lượt.
HET_GIO_LENH_S = 10.0

#: Xác minh sau `unload`: đọc lại `/running` tới khi model biến mất.
#: ⛔ Không tin lời của lệnh — cùng luật *"KHONG TIN, HAY DO"* mà 5.4a áp cho SCM.
HAN_XAC_MINH_NHA_S = 10.0
NHIP_XAC_MINH_S = 0.5

#: Một lượt `max_tokens=1` để buộc llama-swap nạp hồ sơ. Nạp LTT-3.8 (16,46 GB)
#: từ kho ấm đo được ~16 s (§G4/G5) — trần này rộng gấp nhiều lần để một lần nạp
#: từ kho **lạnh** hay một đĩa đang bận không bị gọi là "lỗi nạp".
HET_GIO_NAP_S = 300.0

#: Chờ `/health` xanh sau lượt nạp. Cùng lý do trên, cộng thêm: `/health` của
#: llama-server chỉ xanh khi model đã nạp xong hẳn.
HAN_CHO_HEALTH_S = 180.0
NHIP_HEALTH_S = 2.0

#: Nội dung lượt nạp. Ngắn nhất có thể: mục đích là **đánh thức hồ sơ**, không
#: phải sinh chữ. `max_tokens=1` nên phần sinh ra bị cắt ngay ở token đầu.
TIN_NHAN_NAP = "ok"


class SoNap:
    """Kết quả lượt `nap` **gần nhất**, dùng chung giữa endpoint và luồng nền.

    🔴 `bat_dau()` ĐẶT LẠI VỀ `""`, VÀ ĐÓ LÀ MỘT HỢP ĐỒNG VÔ HÌNH SANG MÁY A.
       Task 5.1/5.2 đã nêu nó thành lo ngại số 1: nếu một `"loi"` cũ sống sót qua
       một lệnh `nap` mới thì máy trạng thái quay vòng `LOI_NAP → NAP_LLM →
       LOI_NAP` và thời gian lùi phồng tới trần 480 s **vì một con số cũ**, chứ
       không vì một lần nạp hỏng thật. Không sai an toàn — nhưng im lặng, và
       "im lặng" là hạng khuyết tật đắt nhất của kho này. Máy A ghim hành vi ấy ở
       `test_1216::test_nap_ket_qua_cu_lam_phong_lui_dan_nen_may_b_phai_dat_lai`;
       đây là đầu dây bên này.

    ⚠️ Có khoá vì `nap` chạy ở **luồng nền** còn `trang_thai` đọc ở luồng của
       endpoint — hai luồng, một ô nhớ.
    """

    def __init__(self) -> None:
        self._khoa = threading.Lock()
        self._ket_qua = CHUA
        self._ly_do = ""
        self._dang_chay = False

    def bat_dau(self) -> bool:
        """Mở một lượt nạp. `False` = đã có một lượt đang chạy (⇒ đừng mở lượt hai).

        Đặt lại `nap_ket_qua` về `""` **trước** khi luồng nền chạy dòng nào: một
        lượt nạp mới không được mang theo phán quyết của lượt trước dù chỉ một
        nhịp thăm dò.
        """
        with self._khoa:
            if self._dang_chay:
                return False
            self._ket_qua = CHUA
            self._ly_do = ""
            self._dang_chay = True
            return True

    def xong(self, ket_qua: str, ly_do: str = "") -> None:
        with self._khoa:
            self._ket_qua = ket_qua
            self._ly_do = ly_do
            self._dang_chay = False
        if ket_qua == LOI:
            log.error("nap that bai: %s", ly_do)

    def doc(self) -> str:
        with self._khoa:
            return self._ket_qua

    def ly_do(self) -> str:
        with self._khoa:
            return self._ly_do

    def dang_chay(self) -> bool:
        with self._khoa:
            return self._dang_chay


def duong_nha(model: str) -> str:
    """Đường nhả của **đúng** hồ sơ này.

    `quote(safe="")` vì tên hồ sơ đi thẳng vào đường dẫn: một tên có `/` hay
    khoảng trắng sẽ đổi nghĩa cả lời gọi, và `/api/models/unload` **không tham
    số** là đường nhả **HẾT** (đo 12/09). Tức một lỗi thoát chuỗi ở đây không
    sinh ra 404 — nó sinh ra đúng hành vi mà cả Task 5.4 đi gỡ bỏ.
    """
    return DUONG_NHA + quote(str(model or "").strip(), safe="")


def models_dang_chay(upstream: Any, *,
                     timeout_s: float = HET_GIO_LENH_S) -> Optional[dict]:
    """`{tên hồ sơ: trạng thái}` theo llama-swap. `None` = **không hỏi được**.

    ⛔ `None` khác `{}`. "Không hỏi được máy B" và "máy B không giữ model nào" đòi
       hai phán xử ngược nhau ở trọng tài (fail-closed vs nhả cửa), nên hai thứ
       ấy không được gộp thành một giá trị.
    """
    ma, than = upstream.json("GET", DUONG_RUNNING, timeout=timeout_s)
    if ma != 200:
        log.warning("khong hoi duoc %s: ma=%s", DUONG_RUNNING, ma)
        return None
    try:
        d = _json.loads(than or b"{}")
    except (ValueError, TypeError):
        log.warning("%s tra ve than khong phai JSON", DUONG_RUNNING)
        return None
    ra: dict = {}
    for m in (d.get("running") or []):
        if isinstance(m, dict) and m.get("model"):
            ra[str(m["model"])] = str(m.get("state") or "")
    return ra


@dataclass(frozen=True)
class KetQuaNha:
    """Kết quả một lệnh nhả. `xong=False` ⇒ người gọi PHẢI báo lỗi ra ngoài."""

    xong: bool
    #: Mã HTTP của lời gọi `unload`. `0` = chưa gọi được.
    ma: int = 0
    #: `/running` sau lệnh — bằng chứng, không phải lời hứa. `None` = không đọc được.
    con_lai: Optional[tuple] = None
    ly_do: str = ""


def nha(upstream: Any, model: str, *,
        han_xac_minh_s: float = HAN_XAC_MINH_NHA_S,
        nhip_s: float = NHIP_XAC_MINH_S,
        now: Callable[[], float] = time.monotonic,
        ngu: Callable[[float], None] = time.sleep) -> KetQuaNha:
    """Nhả **đúng** `model` khỏi VRAM, rồi **đo lại** để biết nó đã đi.

    ⛔ Người gọi phải tự kiểm `inflight == 0` TRƯỚC. Hàm này không hỏi sổ suất và
       cố ý không hỏi: một chốt an toàn nằm ở hai chỗ là hai chỗ có thể lệch.
    """
    ma, than = upstream.json("POST", duong_nha(model), timeout=HET_GIO_LENH_S)
    if not (200 <= ma < 300):
        return KetQuaNha(
            False, ma, None,
            f"llama-swap tu choi lenh nha {model!r}: ma {ma} "
            f"({(than or b'')[:200]!r})")

    t0 = now()
    while True:
        dang = models_dang_chay(upstream)
        if dang is not None and model not in dang:
            return KetQuaNha(True, ma, tuple(sorted(dang)), "")
        if now() - t0 >= han_xac_minh_s:
            if dang is None:
                return KetQuaNha(
                    False, ma, None,
                    f"da gui lenh nha {model!r} (ma {ma}) nhung KHONG doc duoc "
                    f"{DUONG_RUNNING} de xac minh — khong the noi card da sach")
            return KetQuaNha(
                False, ma, tuple(sorted(dang)),
                f"da gui lenh nha {model!r} (ma {ma}) nhung sau "
                f"{han_xac_minh_s:.0f}s no VAN nam trong {DUONG_RUNNING}: "
                f"{sorted(dang)}")
        ngu(nhip_s)


def duong_health(model: str) -> str:
    return (DUONG_UPSTREAM + quote(str(model or "").strip(), safe="")
            + "/health")


def than_nap(model: str) -> dict:
    """Một lượt sinh **một** token — đủ để llama-swap nạp hồ sơ, không hơn."""
    return {"model": model,
            "messages": [{"role": "user", "content": TIN_NHAN_NAP}],
            "max_tokens": 1,
            "stream": False}


def chay_nap(upstream: Any, model: str, so: SoNap, *,
             han_health_s: float = HAN_CHO_HEALTH_S,
             nhip_s: float = NHIP_HEALTH_S,
             now: Callable[[], float] = time.monotonic,
             ngu: Callable[[float], None] = time.sleep) -> None:
    """Thân của lượt nạp — chạy ở **luồng nền**, không bao giờ ném.

    ⭐ VÌ SAO NỀN: nạp LTT-3.8 mất ~16 s và trọng tài máy A hỏi mỗi 2 s. Một
       endpoint chặn 16 s sẽ ăn hết tám nhịp thăm dò của nó, và bất cứ hạn chờ
       nào ở phía máy A cũng biến một lần nạp bình thường thành một lần "lỗi
       nạp" — tức đúng cái vòng lùi dần mà `SoNap.bat_dau` đi chặn.

    ⛔ Và nó KHÔNG ném: một ngoại lệ trong luồng nền chỉ ra log rồi biến mất, để
       `nap_ket_qua` ở `""` vĩnh viễn — trọng tài sẽ ngồi ở `NAP_LLM` mãi mãi.
       Mọi đường ra phải đi qua `so.xong(...)`.
    """
    try:
        ma, than = upstream.json("POST", "/v1/chat/completions",
                                 body=than_nap(model), timeout=HET_GIO_NAP_S)
        if not (200 <= ma < 300):
            so.xong(LOI, f"luot nap {model!r} (max_tokens=1) tra ma {ma}: "
                         f"{(than or b'')[:200]!r}")
            return

        t0 = now()
        while True:
            mh, _th = upstream.json("GET", duong_health(model),
                                    timeout=HET_GIO_LENH_S)
            if 200 <= mh < 300:
                so.xong(OK)
                return
            if now() - t0 >= han_health_s:
                so.xong(LOI, f"da nap {model!r} nhung {duong_health(model)} van "
                             f"tra ma {mh} sau {han_health_s:.0f}s")
                return
            ngu(nhip_s)
    except Exception as e:                                      # noqa: BLE001
        so.xong(LOI, f"{type(e).__name__}: {e}")
