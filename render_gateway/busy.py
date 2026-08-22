"""
busy.py — máy B có đang bận không, và nếu bận thì còn bao lâu.

⭐ VÌ SAO KHÔNG DÙNG WEBSOCKET (đọc từ mã ComfyUI, không phải suy đoán):
   `progress` / `executing` / `executed` / `execution_error` đều gửi kèm
   `server.client_id` — **chỉ tới client đã gửi prompt đó**. Chỉ `status` là quảng
   bá. ⇒ Ta **không thể** nghe tiến độ của lượt VIDEO do dự án `E:\\LTT AI` gửi.

   Nên ETA cho việc lạ suy từ **lịch sử thời lượng** mà chính module này tự đo:
   thấy một `prompt_id` lạ xuất hiện trong `/queue` → bấm giờ; thấy nó biến mất →
   ghi lại thời lượng. Trung vị của các lần trước là ước tính cho lần sau.

⭐ NGUYÊN TẮC ƯỚC LƯỢNG: **không bao giờ lạc quan.** Thà báo ETA dài hơn thật rồi
   để khách chọn đám mây, còn hơn hứa 20 giây rồi bắt chờ 4 phút. Khi chưa có lịch
   sử, trả `None` (không biết) — bên gọi phải coi "không biết" là "lâu".

⛔ Ngưỡng RAM là **LƯỢNG TUYỆT ĐỐI (GB), không phải tỉ lệ.** Dự án video trên máy B
   đã học điều này bằng một chốt chặn oan: ngưỡng 40 % đặt trên máy 96 GB, sau khi
   nâng lên 192 GB thì cùng con số đó đòi 115 GB trống. Nâng RAM lần nữa là nó sai
   lần nữa.
"""
from __future__ import annotations

import logging
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .comfy import ComfyClient, ComfyError

log = logging.getLogger("render_gateway.busy")

#: nvidia-smi treo duoc (driver loi, card ket). Vong do khong duoc dung cho vo han.
#: Cung tran voi `platform_core/gpu.py` cua nen tang, khong dat so khac.
NVIDIA_SMI_TIMEOUT_S = 8

#: Số lần đo giữ lại cho mỗi loại việc. Đủ để có trung vị, đủ ngắn để bám theo
#: thực tế khi lượt video nhanh dần lên (chủ dự án cho biết sẽ nhanh lên nhiều).
SO_MAU_GIU = 12

#: VRAM tối thiểu phải còn dùng được cho MỘT lượt vẽ, tính bằng MB.
#:
#: Từ số đo thật trên máy B (bf16, `--reserve-vram 3`): t2i đỉnh **17.600 MB**, có
#: ảnh tham chiếu đỉnh **20.000 MB**. Lấy mức cao hơn cộng một khoảng đệm nhỏ, vì
#: nhận một job rồi hết VRAM giữa chừng đắt hơn nhiều so với báo bận.
VRAM_CAN_TOI_THIEU_MB = 20_500


def so_python_tinh_tren_gpu() -> Optional[int]:
    """Số tiến trình **python** đang TÍNH TOÁN trên GPU. `None` nếu không hỏi được.

    ⭐ Đây là chốt "có ai khác đang dùng card không", **thay cho ngưỡng VRAM**.

    ⛔ VÌ SAO NGƯỠNG VRAM KHÔNG DÙNG ĐƯỢC — đo thật 2026-08-22: chạy 30 ảnh liên
    tiếp, VRAM đỉnh lên **23.967 / 24.576 MB (97,5 %)** và **ở lì đó giữa các job**,
    vì ComfyUI giữ model thường trú. Cùng cấu hình đó khi chỉ chạy 3 ảnh thì đỉnh
    chỉ 16,8 GB. ⇒ "VRAM đang dùng nhiều" **không phân biệt được** giữa *cache của
    chính ComfyUI* và *một tiến trình khác đang chiếm card*. Giữ ngưỡng đó thì cổng
    sẽ tự báo bận vĩnh viễn sau lô đầu tiên.

    ⛔ Và **không quy được VRAM theo tiến trình** trên máy này:
    `nvidia-smi --query-compute-apps=pid,used_memory` trả `[N/A]` cho mọi PID
    (WDDM) — khớp với `per_process_vram_available: false` mà Nexus báo.

    ⭐ Cái ĐẾM ĐƯỢC là **danh sách tiến trình compute**. Đo thật: 26 PID compute
    (WDDM tính cả `dwm.exe`, trình duyệt…), trong đó **đúng 1 là python** — và nó
    chính là ComfyUI (chủ cổng 8188). Nên:

        1 python  → chỉ có ComfyUI, không ai khác
        ≥ 2       → **có tiến trình khác đang tính trên card**

    Bắt được cả loại việc chạy NGOÀI ComfyUI (`E:\\AI\\tools\\vlm_worker.py` và các
    script torch tương tự của dự án video) — đúng thứ mà hàng đợi ComfyUI không thấy.
    """
    if not shutil.which("nvidia-smi"):
        return None
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=NVIDIA_SMI_TIMEOUT_S,
            encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("khong hoi duoc compute-apps: %s", e)
        return None
    if r.returncode != 0:
        return None
    dem = 0
    for dong in (r.stdout or "").splitlines():
        if "python" in dong.lower():
            dem += 1
    return dem


def vram_dung_mb_qua_smi() -> Optional[int]:
    """VRAM đang dùng THẬT trên card, hỏi `nvidia-smi`. `None` nếu không hỏi được.

    ⛔ **KHÔNG dùng ComfyUI `/system_stats` hay `torch.cuda.mem_get_info()` cho câu
    hỏi này.** Đo thật trên máy B ngày 2026-08-21: một tiến trình khác giữ 8 GB,
    ba nguồn trả lời "VRAM còn trống bao nhiêu" như sau —

        nvidia-smi              15.308 MiB   <- ĐÚNG
        ComfyUI /system_stats   23.165 MiB   <- MÙ, không thấy tiến trình khác
        torch mem_get_info      23.217 MiB   <- MÙ

    Trên Windows/WDDM hai nguồn sau chỉ thấy tiến trình của chính mình. Nếu để
    `busy.py` dựa vào chúng thì chốt "VRAM đang bị giữ bởi tiến trình khác" **sẽ
    không bao giờ bắn** — và một lượt video chạy NGOÀI ComfyUI (máy B có sẵn nhiều
    script torch chạy trực tiếp, ví dụ `E:\\AI\\tools\\vlm_worker.py`) sẽ đi lọt.

    Nền tảng đã chọn đúng đường này từ trước: `platform_core/gpu.py` cũng hỏi
    `nvidia-smi` chứ không dùng thư viện. Nay có số đo giải thích vì sao.
    """
    if not shutil.which("nvidia-smi"):
        return None
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=NVIDIA_SMI_TIMEOUT_S,
            encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("khong hoi duoc nvidia-smi: %s", e)
        return None
    if r.returncode != 0:
        return None
    dung = 0
    for dong in (r.stdout or "").splitlines():
        dong = dong.strip()
        if not dong:
            continue
        try:
            dung = max(dung, int(float(dong)))
        except ValueError:
            continue
    return dung


def vram_ngoai_nhan_mb(smi_dung_mb: Optional[int],
                       stats: Optional[dict]) -> Optional[int]:
    """VRAM đang bị **tiến trình NGOÀI ComfyUI** giữ, tính bằng MB. `None` = không biết.

    ⭐ ĐÂY LÀ CON SỐ MÀ CẢ HAI CHỐT TRƯỚC ĐỀU KHÔNG CÓ, và nó đến từ chỗ không ngờ:
    **chính sự "mù" của ComfyUI**.

    Trên Windows/WDDM, `/system_stats` chỉ thấy bộ nhớ của **chính nó**, còn
    `nvidia-smi` thấy **toàn card**. Hiệu của hai nguồn chính là phần người khác giữ:

        ngoại nhân giữ  =  (nvidia-smi dùng)  −  (ComfyUI tự dùng)

    ⛔ VÌ SAO HAI CHỐT TRƯỚC ĐỀU HỞ — mỗi cái hở một kiểu, và cả hai đều **im lặng**:

    · **Ngưỡng VRAM tuyệt đối** (bản đầu): ComfyUI giữ model thường trú nên sau lô
      đầu tiên VRAM ở lì 23,9/24,6 GB. Ngưỡng đó làm cổng **tự báo bận vĩnh viễn**.
      Công thức trên miễn nhiễm: phần ComfyUI tự giữ **bị trừ đi**, nên nó không
      tính vào "người khác".

    · **Đếm tiến trình python** (bản thay thế): đo thật 22/08 lúc 22:27 — máy B có
      `llama-server.exe` giữ **15,9 GB** cho một model LLM 27B của dự án `H:\\LTT_LLM`.
      Nó **không phải python**, nên phép đếm trả về đúng 1 (chỉ ComfyUI) và cổng
      báo **RẢNH** trong khi card chỉ còn **4,6 GB**. Nhận một job lúc đó là hết
      VRAM giữa chừng. Tiền đề của phép đếm — *"tiến trình lạ trên card đều là
      python"* — đúng khi chỉ có dự án video, và **sai từ lúc dự án LLM lên**.

    ⇒ Giữ **cả hai**: phép đếm bắt việc **đang tính** dù chiếm ít bộ nhớ; công thức
      này bắt việc **đang giữ bộ nhớ** dù không tính và dù không phải python.
    """
    if smi_dung_mb is None or not stats:
        return None
    thiet_bi = (stats.get("devices") or [])
    if not thiet_bi:
        return None
    d = thiet_bi[0] or {}
    try:
        tong = int(d.get("vram_total") or 0) // (1024 * 1024)
        trong = int(d.get("vram_free") or 0) // (1024 * 1024)
    except (TypeError, ValueError):
        return None
    if tong <= 0 or trong < 0 or trong > tong:
        return None
    comfy_tu_dung = tong - trong
    # Kẹp về 0: đồng hồ hai nguồn đọc lệch nhau vài chục MB là chuyện thường, và một
    # số âm nhỏ không có nghĩa là "người khác trả lại bộ nhớ".
    return max(0, smi_dung_mb - comfy_tu_dung)


@dataclass(frozen=True)
class BusyState:
    busy: bool
    #: Vì sao bận — hiện thẳng cho người dùng, nên phải đọc được bằng tiếng người.
    reason: str
    #: Giây còn lại, ước tính. `None` = **không biết**, và không biết nghĩa là lâu.
    eta_s: Optional[float]
    foreign_running: int
    queue_remaining: int
    vram_used_mb: int
    ram_free_gb: float
    #: VRAM do tiến trình NGOÀI ComfyUI giữ. `None` = không đo được.
    vram_ngoai_mb: Optional[int] = None

    def as_dict(self) -> dict:
        return {
            "busy": self.busy, "reason": self.reason, "eta_s": self.eta_s,
            "foreign_running": self.foreign_running,
            "queue_remaining": self.queue_remaining,
            "vram_used_mb": self.vram_used_mb,
            "ram_free_gb": round(self.ram_free_gb, 1),
            "vram_ngoai_mb": self.vram_ngoai_mb,
        }


@dataclass
class BusyWatcher:
    comfy: ComfyClient
    ram_trong_toi_thieu_gb: float = 48.0
    #: Đồng hồ tiêm được để test không phải ngủ.
    now: Callable[[], float] = time.monotonic
    #: Đọc VRAM đang dùng thật. Tiêm được để test không cần GPU.
    #: Mặc định là `nvidia-smi` — xem docstring của nó để biết vì sao KHÔNG dùng
    #: `/system_stats` cho việc này.
    #: ⚠️ Con số này chỉ để BÁO CÁO trong `/health`. Nó **không** còn được dùng để
    #: quyết định bận/rảnh — xem `so_python_tinh_tren_gpu`.
    doc_vram_mb: Callable[[], Optional[int]] = vram_dung_mb_qua_smi
    #: Đếm tiến trình python đang tính trên GPU. Bắt việc **đang tính**.
    dem_python_gpu: Callable[[], Optional[int]] = so_python_tinh_tren_gpu
    #: VRAM tối thiểu phải còn dùng được. Bắt việc **đang giữ bộ nhớ** — kể cả khi
    #: nó không tính gì và không phải python (`llama-server.exe`, 22/08).
    vram_can_toi_thieu_mb: int = VRAM_CAN_TOI_THIEU_MB

    _bat_dau: dict[str, float] = field(default_factory=dict, init=False)
    _thoi_luong: list[float] = field(default_factory=list, init=False)
    _doc_chiem_den: Optional[float] = field(default=None, init=False)
    _doc_chiem_ly_do: str = field(default="", init=False)
    #: Dung lượng card, đọc từ `/system_stats`. 0 = chưa đọc được lần nào.
    _tong_mb: int = field(default=0, init=False)

    # ── chế độ độc chiếm ─────────────────────────────────────────────────────
    def doc_chiem(self, *, bat: bool, ly_do: str = "", het_han_s: float = 7200.0) -> None:
        """Dự án video bật cờ này khi đang đo benchmark — job ảnh chen vào sẽ làm
        bẩn số đo VRAM/RAM/nhiệt của họ. **Tự hết hạn** để không ai quên tắt."""
        if bat:
            self._doc_chiem_den = self.now() + max(1.0, het_han_s)
            self._doc_chiem_ly_do = ly_do or "doc chiem"
        else:
            self._doc_chiem_den = None
            self._doc_chiem_ly_do = ""

    def _dang_doc_chiem(self) -> bool:
        if self._doc_chiem_den is None:
            return False
        if self.now() >= self._doc_chiem_den:
            self._doc_chiem_den = None
            self._doc_chiem_ly_do = ""
            return False
        return True

    # ── quan sát ─────────────────────────────────────────────────────────────
    def observe(self, cua_ta: set[str]) -> BusyState:
        """Đọc một lần trạng thái máy. `cua_ta` = tập `prompt_id` của cổng này."""
        if self._dang_doc_chiem():
            return BusyState(True, f"doc chiem: {self._doc_chiem_ly_do}", None,
                             0, 0, 0, 0.0)
        try:
            dang_chay, dang_cho = self.comfy.queue_prompt_ids()
        except ComfyError as e:
            return BusyState(True, f"ComfyUI khong tra loi: {e}", None, 0, 0, 0, 0.0)

        la_chay = [p for p in dang_chay if p not in cua_ta]
        la_cho = [p for p in dang_cho if p not in cua_ta]
        self._cap_nhat_lich_su(set(la_chay))

        vram_mb, ram_gb, ngoai_mb = self._tai_nguyen()

        if la_chay:
            return BusyState(True, "may dang chay viec khac (video)",
                             self._eta(la_chay), len(la_chay),
                             len(dang_chay) + len(dang_cho), vram_mb, ram_gb)
        if la_cho:
            return BusyState(True, "co viec khac dang xep hang", None, 0,
                             len(dang_chay) + len(dang_cho), vram_mb, ram_gb)
        if ram_gb and ram_gb < self.ram_trong_toi_thieu_gb:
            return BusyState(True,
                             f"RAM trong {ram_gb:.0f} GB < nguong {self.ram_trong_toi_thieu_gb:.0f} GB",
                             None, 0, len(dang_chay) + len(dang_cho), vram_mb, ram_gb)
        # ⛔ KHÔNG dùng ngưỡng VRAM ở đây. Đo thật 2026-08-22: chạy 30 ảnh liên tiếp
        #    thì VRAM ở lì 23,9/24,6 GB **giữa các job** vì ComfyUI giữ model thường
        #    trú. Ngưỡng VRAM sẽ làm cổng tự báo bận vĩnh viễn sau lô đầu tiên.
        #    Cái phân biệt được là SỐ TIẾN TRÌNH python đang tính trên card.
        so_py = self.dem_python_gpu()
        if so_py is not None and so_py >= 2:
            return BusyState(True,
                             f"co {so_py - 1} tien trinh khac dang tinh tren GPU",
                             None, 0, len(dang_chay) + len(dang_cho), vram_mb, ram_gb,
                             ngoai_mb)
        # ⛔ Chốt thứ hai, và nó bắt thứ phép đếm trên KHÔNG bắt được: bộ nhớ bị một
        #    tiến trình **không phải python** giữ mà **không tính toán gì**. Đo thật
        #    22/08 22:27: `llama-server.exe` giữ 15,9 GB, GPU 0 % tải, phép đếm trả
        #    về 1 ⇒ cổng báo rảnh trong khi card chỉ còn 4,6 GB.
        if ngoai_mb is not None:
            kha_dung = self._vram_tong_mb() - ngoai_mb
            if kha_dung < self.vram_can_toi_thieu_mb:
                return BusyState(
                    True,
                    f"tien trinh khac dang giu {ngoai_mb} MB VRAM, "
                    f"chi con {kha_dung} MB dung duoc (can {self.vram_can_toi_thieu_mb})",
                    None, 0, len(dang_chay) + len(dang_cho), vram_mb, ram_gb, ngoai_mb)
        return BusyState(False, "", 0.0, 0, len(dang_chay) + len(dang_cho), vram_mb,
                         ram_gb, ngoai_mb)

    # ── nội bộ ───────────────────────────────────────────────────────────────
    def _cap_nhat_lich_su(self, la_chay: set[str]) -> None:
        t = self.now()
        for pid in la_chay:
            self._bat_dau.setdefault(pid, t)
        for pid in list(self._bat_dau):
            if pid not in la_chay:
                keo_dai = t - self._bat_dau.pop(pid)
                # Bỏ mẫu quá ngắn: đó thường là lượt chạy khô hoặc lượt hỏng ngay,
                # gộp vào sẽ kéo trung vị xuống và làm ta hứa hão.
                if keo_dai >= 5.0:
                    self._thoi_luong.append(keo_dai)
                    del self._thoi_luong[:-SO_MAU_GIU]

    def _eta(self, la_chay: list[str]) -> Optional[float]:
        if not self._thoi_luong:
            return None          # chưa có lịch sử ⇒ không biết ⇒ coi như lâu
        trung_vi = statistics.median(self._thoi_luong)
        t = self.now()
        con_lai = [max(0.0, trung_vi - (t - self._bat_dau.get(p, t))) for p in la_chay]
        # Nhiều việc lạ cùng chạy thì lấy cái LÂU nhất, không phải cái sớm nhất.
        return max(con_lai) if con_lai else None

    def _vram_tong_mb(self) -> int:
        return self._tong_mb or 24_576

    def _tai_nguyen(self) -> tuple[int, float, Optional[int]]:
        """(VRAM đang dùng MB, RAM còn trống GB, VRAM do người khác giữ MB).

        Hai con số này đến từ **hai nguồn khác nhau, có chủ ý**:

        - **VRAM: `nvidia-smi`.** `/system_stats` của ComfyUI mù với tiến trình
          khác trên Windows/WDDM — đã đo, xem `vram_dung_mb_qua_smi`.
        - **RAM: `/system_stats`.** Con số RAM không bị giới hạn theo tiến trình
          nên nó đúng, và lấy ở đây thì đỡ một lời gọi hệ thống nữa.
        """
        ram_free = 0.0
        st: Optional[dict] = None
        try:
            st = self.comfy.system_stats()
            ram_free = float((st.get("system") or {}).get("ram_free") or 0) / (1024 ** 3)
        except ComfyError:
            st = None
        vram_used = self.doc_vram_mb()
        # Gọi `/system_stats` ĐÚNG MỘT LẦN rồi dùng lại: mỗi lượt `observe()` chạy
        # theo nhịp hỏi trạng thái, gọi hai lần là gấp đôi tải lên ComfyUI cho không.
        ngoai = vram_ngoai_nhan_mb(vram_used, st)
        thiet_bi = ((st or {}).get("devices") or [{}])[0] or {}
        try:
            self._tong_mb = int(thiet_bi.get("vram_total") or 0) // (1024 * 1024)
        except (TypeError, ValueError):
            self._tong_mb = 0
        return (vram_used if vram_used is not None else 0), ram_free, ngoai
