"""
don_dep.py — bảo đảm card SẠCH trước khi nạp model. (H38, P6)

🔴 VÌ SAO TỆP NÀY TỒN TẠI — ĐO THẬT NGÀY 22/08/2026 TRÊN MÁY B.

   Cùng một cấu hình, cùng một model, cùng một prompt. Chỉ khác **trạng thái card
   ngay trước khi nạp**:

     card BAN   (ComfyUI con giu 6.211 MiB)  ->  18,2 tok/s   VRAM 24.102/24.576 (98,1%)
     card SACH  (sau khi goi /free)          ->  63,3 tok/s   VRAM 20.236/24.576 (82,3%)

   **Chênh 3,5 lần.** Và llama.cpp **KHÔNG báo lỗi gì cả** — nó nhét vừa rồi tràn
   trọng số sang RAM chủ qua PCIe, `/health` vẫn xanh, `/v1/models` vẫn đúng, nội
   dung sinh ra vẫn hợp lệ. Chỉ có tốc độ lặng lẽ còn một phần tư.

   ⚠️ Đây là **đính chính một điều tôi đã ghi sai** trong bản kế hoạch: tôi viết
   rằng llama.cpp "báo lỗi to khi GPU chưa sạch, khác vLLM". Sai. Số đo ở trên bác
   bỏ nó. Cả hai engine đều hỏng **trong im lặng**, chỉ khác cơ chế.

   Nó cũng khớp đúng **luật 7** của cộng đồng: *"A shared desktop halves everything,
   silently — spilled 3.5 GB of weights to host RAM over PCIe while /health stayed
   green; decode halved with no error anywhere."*

⭐ VÀ MỘT SỰ THẬT NỮA ĐO ĐƯỢC: **ComfyUI giữ model thường trú kể cả sau khi render
   xong.** Sau một lượt vẽ, nó vẫn ôm 6.211 MiB. Chỉ `POST /free` với
   `unload_models` mới đưa về 1.515 MiB. Nên "đợi ComfyUI rảnh" là **không đủ** —
   phải bảo nó nhả, rồi **tự đi đo lại**.

⛔ ĐO BẰNG `nvidia-smi`, KHÔNG BẰNG `/health` HAY `/system_stats` (D-013). Chính
   phase này chứng minh vì sao: `/health` xanh trong khi tốc độ đã mất 73 %.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger("llm_gateway.don_dep")

#: Card mà việc dọn nói về: **3090**. ComfyUI và LTT-3.8 dùng chung nó, nên
#: "card có sạch chưa" là một câu hỏi về đúng card ấy. 5060 Ti (`ltt35`) không
#: chạy ComfyUI, nên việc dọn không có nghĩa ở đó.
VAI_MAC_DINH = "ltt38"

#: Cùng trần với `render_gateway/busy.py`. Không đặt số khác.
NVIDIA_SMI_TIMEOUT_S = 8


def doc_vram_dung_mb(vai: str = VAI_MAC_DINH) -> Optional[int]:
    """VRAM đang dùng **trên card của `vai`**, MiB. `None` khi không hỏi được.

    ⛔ `nvidia-smi`, không phải `torch`, không phải `/system_stats`: hai nguồn kia
       mù với tiến trình khác trên Windows/WDDM (D-013).

    🔴 BẢN CŨ LẤY `dong[0]` VÀ ĐÓ LÀ MỘT PHÉP ĐO LỆCH CHIỀU TỪ 09/2026. Máy B có
       hai card; dòng đầu là card nào thì do driver quyết. Việc dọn card là việc
       của **3090** (ComfyUI và LTT-3.8 dùng chung nó), nên mặc định là `ltt38` —
       nhưng con số phải đến từ đúng card ấy, không từ "dòng đầu". Xem
       `gpu_uuid.py`.

    ⚠️ Không đọc được danh tính (tệp json thiếu) ⇒ `None`, **không** rơi về
       "dòng đầu". Rơi về đó là đổi một câu "không biết" lấy một câu sai.
    """
    from .gpu_uuid import VaiKhongCo, uuid_cua, vram_mib
    try:
        uu = uuid_cua(vai)
    except (VaiKhongCo, OSError, ValueError) as e:
        log.warning("khong doc duoc danh tinh GPU vai=%s: %s", vai, e)
        return None
    return vram_mib(uu)


def _bao_comfy_nha(comfy_url: str, timeout_s: float = 20.0) -> bool:
    """Bảo ComfyUI nhả model khỏi VRAM. Trả `True` nếu nó nhận lệnh.

    ⚠️ `/free` **KHÔNG nhả ngay** — đọc `server.py` của ComfyUI:

        if unload_models: self.prompt_queue.set_flag("unload_models", True)

    Nó chỉ **đặt cờ**, và hàng đợi xử lý cờ **giữa các prompt**. Nên `True` ở đây
    nghĩa là *"đã nhận lệnh"*, không phải *"đã nhả"*. Phải tự đo lại.
    """
    try:
        import httpx
        r = httpx.post(f"{comfy_url.rstrip('/')}/free",
                       json={"unload_models": True, "free_memory": True},
                       timeout=timeout_s)
        return 200 <= r.status_code < 300
    except Exception as e:                              # pragma: no cover
        log.warning("goi /free cua ComfyUI that bai: %s", type(e).__name__)
        return False


def _comfy_dang_chay(comfy_url: str, timeout_s: float = 8.0) -> Optional[bool]:
    """ComfyUI có job đang chạy không. `None` = không hỏi được.

    🔴 VÌ SAO PHẢI HỎI TRƯỚC KHI GỌI `/free`:

       `/free` chỉ **đặt cờ**, và cờ nổ **sau khi lượt hiện tại xong**. Một lượt
       video trên máy B từng chạy **72,5 phút**. Nếu ta đặt cờ giữa lượt đó:

         1. ta chờ vô ích 18 giây rồi vẫn trả 429 — chậm hơn cần thiết;
         2. và tệ hơn: cờ sẽ nổ **ngay khi video xong**, nên nếu dự án video xếp
            nhiều lượt liên tiếp thì ta vừa bắt họ nạp lại model giữa chừng.

       Hỏi `/queue` trước thì cả hai đều biến mất: bận ⇒ trả 429 **ngay**, và
       **không đụng gì** vào hàng xóm.

    ⛔ Không hỏi được thì trả `None`, và bên gọi phải coi đó là **có thể đang bận**
       — cùng nguyên tắc không-lạc-quan của `busy.py`.
    """
    try:
        import httpx
        r = httpx.get(f"{comfy_url.rstrip('/')}/queue", timeout=timeout_s)
        if r.status_code != 200:
            return None
        d = r.json()
    except Exception as e:
        log.info("khong hoi duoc /queue cua ComfyUI: %s", type(e).__name__)
        return None
    if not isinstance(d, dict):
        return None
    return bool(d.get("queue_running"))


@dataclass(frozen=True)
class KetQuaDonDep:
    sach: bool
    vram_dau_mb: Optional[int]
    vram_cuoi_mb: Optional[int]
    da_goi_free: bool
    ly_do: str = ""
    #: ComfyUI có job đang chạy không (`None` = không hỏi được).
    comfy_dang_chay: Optional[bool] = None


class DonDepGpu:
    """Dọn card trước khi nạp model. Mọi nguồn tiêm được để test không cần GPU."""

    def __init__(self, *, comfy_url: str, nguong_sach_mb: int = 2500,
                 so_lan_thu: int = 6, cho_moi_lan_s: float = 3.0,
                 doc_vram: Callable[[], Optional[int]] = doc_vram_dung_mb,
                 bao_nha: Optional[Callable[[], bool]] = None,
                 comfy_ban: Optional[Callable[[], Optional[bool]]] = None,
                 ngu: Callable[[float], None] = time.sleep):
        self.comfy_url = comfy_url
        # Nền đo được trên máy B: desktop chiếm 1.515–1.612 MiB; ComfyUI thường trú
        # 6.211–16.620 MiB. 2.500 nằm gọn giữa hai vùng đó.
        self.nguong_sach_mb = nguong_sach_mb
        self.so_lan_thu = so_lan_thu
        self.cho_moi_lan_s = cho_moi_lan_s
        self._doc = doc_vram
        self._nha = bao_nha or (lambda: _bao_comfy_nha(self.comfy_url))
        self._comfy_ban = comfy_ban or (lambda: _comfy_dang_chay(self.comfy_url))
        self._ngu = ngu

    def bao_dam_sach(self) -> KetQuaDonDep:
        """Bảo ComfyUI nhả rồi **tự đo lại** cho tới khi card thật sự sạch."""
        dau = self._doc()

        if dau is None:
            # Không đo được ⇒ không lạc quan. Cùng nguyên tắc `busy.py`: thà báo
            # bận rồi để bên gọi chọn đường khác, còn hơn nạp lên một card có thể
            # bẩn và phục vụ ở một phần tư tốc độ mà không ai biết.
            return KetQuaDonDep(False, None, None, False,
                                "khong hoi duoc nvidia-smi")

        if dau <= self.nguong_sach_mb:
            return KetQuaDonDep(True, dau, dau, False, "card da sach san")

        # 🔴 HỎI HÀNG ĐỢI TRƯỚC KHI ĐẶT CỜ. Xem `_comfy_dang_chay`.
        #    Đang render ⇒ trả lời NGAY (không chờ 18 giây vô ích) và **không đụng
        #    gì** vào ComfyUI — cờ `/free` đặt lúc này sẽ nổ ngay sau lượt của họ.
        dang_chay = self._comfy_ban()
        if dang_chay is not False:
            ly_do = ("ComfyUI dang render" if dang_chay
                     else "khong hoi duoc /queue cua ComfyUI")
            return KetQuaDonDep(False, dau, dau, False, ly_do,
                                comfy_dang_chay=dang_chay)

        da_goi = self._nha()
        cuoi = dau
        for _ in range(self.so_lan_thu):
            self._ngu(self.cho_moi_lan_s)
            cuoi = self._doc()
            if cuoi is None:
                return KetQuaDonDep(False, dau, None, da_goi,
                                    "mat lien lac voi nvidia-smi giua chung")
            if cuoi <= self.nguong_sach_mb:
                log.info("card da sach: %s -> %s MiB", dau, cuoi)
                return KetQuaDonDep(True, dau, cuoi, da_goi, "",
                                    comfy_dang_chay=False)

        # Vẫn bẩn. Có thể dự án video đang chạy — nó KHÔNG nghe `/free` của ta.
        # ⛔ Trả "chưa sạch" để bên gọi ra 429. **Không** nạp đè lên: nạp đè là
        #    tự chọn phục vụ ở 1/4 tốc độ.
        return KetQuaDonDep(False, dau, cuoi, da_goi,
                            f"VRAM van {cuoi} MiB > nguong {self.nguong_sach_mb} MiB",
                            comfy_dang_chay=False)
