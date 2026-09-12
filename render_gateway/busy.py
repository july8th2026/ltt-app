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

🔴 MỌI PHÉP ĐO GPU Ở ĐÂY LỌC THEO **UUID CARD 3090** (Task 6.1, 12/09/2026). Máy B
   có hai card từ 11/09 và **cả hai** chạy `llama-server`:

       RTX 3090     GPU-26623278-…   LTT-3.8 + model ảnh   <- card TRANH CHẤP (D01 B)
       RTX 5060 Ti  GPU-ebecd0a4-…   LTT-3.5               <- KHÔNG AI TRANH

   Cổng render chỉ tranh 3090. Một tiến trình giữ VRAM hay đang tính trên 5060 Ti
   **không** được làm render "bận" — L-7: hai GPU là hai pool độc lập, không gộp
   24+16. UUID lấy từ `danh_tinh_gpu.py` (đọc `llm_gateway/deploy/gpu_may_b.json`,
   nguồn duy nhất, Task 0.2); **không** hằng số UUID trong tệp này.

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
from .danh_tinh_gpu import VAI_38, uuid_38, vram_tong_mib

log = logging.getLogger("render_gateway.busy")

#: Biên độ cho phép giữa VRAM `/system_stats` khai và VRAM danh nghĩa của 3090.
#:
#: 🔴 VÌ SAO PHẢI SO. `vram_ngoai_nhan_mb` trừ "ComfyUI tự dùng" (từ
#:    `/system_stats`, `devices[0]`) khỏi "cả card dùng" (từ `nvidia-smi`, đã lọc
#:    theo UUID 3090). Phép trừ ấy chỉ có nghĩa khi **cả hai số nói về cùng một
#:    card**. ComfyUI được ghim vào 3090 bằng `CUDA_VISIBLE_DEVICES=GPU-2662…`
#:    (`deploy/cai_dat_dich_vu.ps1`) — nhưng một cái ghim là thứ **hỏng được**
#:    (env dịch vụ bị nssm nướng lúc cài, service cài lại tay…). Ghim rơi ⇒
#:    `devices[0]` là 5060 Ti (16.311 MiB) ⇒ hiệu của hai card là một con số vô
#:    nghĩa chảy thẳng vào quyết định bận/rảnh.
#:
#: ⭐ Dung sai, không phải bằng nhau: `/system_stats` khai theo byte thô của
#:    driver (24.575 MiB cho một card ghi 24.576 MiB trên nhãn). 1 GiB đủ rộng
#:    cho sai số ấy và vẫn hẹp hơn khoảng cách 3090 ↔ 5060 Ti (8.265 MiB).
LECH_TONG_VRAM_CHO_PHEP_MB = 1024

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
#: Số tiến trình python trên card kể từ đó coi là **có người đang tính**.
#:
#: ⭐ **2**, không phải 1: trên máy B ComfyUI luôn chạy, nên một python là trạng
#:    thái bình thường. `llm_gateway/trong_tai.py` chốt cùng con số này và ghi rõ
#:    vì sao đặt 1 là sai — cổng sẽ trả 429 vĩnh viễn.
#:
#: ⚠️ Trước 04/09 số này được gõ thẳng vào giữa `observe()`. Đặt tên vì nó nay
#:    được đọc ở **hai** chỗ, và một hằng số vô danh dùng hai nơi là một hằng số
#:    sẽ lệch.
TRAN_PYTHON_GPU = 2

#: nhận một job rồi hết VRAM giữa chừng đắt hơn nhiều so với báo bận.
#:
#: ⛔ ÁP TRÊN **CARD 3090** (vai `ltt38` trong `gpu_may_b.json`), không trên một
#:    tổng hai card và không trên "dòng đầu" của `nvidia-smi`. 5060 Ti có 16.311 MiB
#:    — nhỏ hơn cả con số này — nên đem nó ra so là vừa sai card vừa sai thang.
VRAM_CAN_TOI_THIEU_MB = 20_500


def _hoi_smi(doi_so: list[str]) -> Optional[str]:
    """Gọi `nvidia-smi`. `None` = **không biết** (không có smi, lỗi, hết giờ).

    ⛔ `None` KHÁC 0 và khác chuỗi rỗng. Bên gọi phải phân biệt "card đang trống"
       với "không hỏi được card" — hai thứ đòi hai hành động khác nhau
       (lệnh residency `/v1/nha_comfy` **từ chối báo thành công** khi không đọc
       được, đúng vậy — `api.py`).
    """
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, *doi_so], capture_output=True, text=True,
                           timeout=NVIDIA_SMI_TIMEOUT_S,
                           encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("khong hoi duoc nvidia-smi (%s): %s", " ".join(doi_so), e)
        return None
    if getattr(r, "returncode", 1) != 0:
        return None
    return r.stdout or ""


def _o_cua_card_3090(truong: str) -> Optional[list[str]]:
    """Các ô của **đúng card 3090**, lọc theo cột `uuid`. `None` = không biết.

    🔴 ĐÂY LÀ CHỖ BẢN CŨ HỎNG, VÀ NÓ HỎNG THEO BA KIỂU CÙNG MỘT GỐC — đọc
       `nvidia-smi` của **cả máy** rồi kết luận về **một** card:

         `tai_gpu_phan_tram`   lấy `dong[0]`  → card nào là do driver xếp
         `vram_dung_mb_qua_smi` lấy `max()`   → 5060 Ti bận thì 3090 "bận"
         `so_python_tinh_tren_gpu` đếm hết    → python trên 5060 Ti làm render bận

       Từ 11/09 máy B có hai card và **cả hai** chạy `llama-server` (Task 3.3), nên
       cả ba trở thành phép đo **lệch chiều**: chúng trả về số của card khác.

    ⭐ LỌC THEO CỘT `uuid`, KHÔNG TRUYỀN `-i <uuid>` — cùng lý do đã ghi ở
       `llm_gateway/gpu_uuid.py`: `-i` là một bảo đảm đi mượn (driver không hiểu
       dạng UUID thì trả mã khác 0, hoặc tệ hơn, trả toàn bộ card). Hỏi cả hai card
       rồi tự lọc thì đúng trong cả hai trường hợp, và biến "dòng nào" thành một
       câu hỏi không còn tồn tại.

    ⛔ Không thấy dòng của UUID ấy ⇒ `None`, **không** rơi sang dòng khác. Card
       rụng khỏi hệ thống là ca đã xảy ra thật (`test_329_chot_so_gpu`), và câu trả
       lời đúng cho nó là "không biết" ⇒ bên gọi từ chối, không chạy mù.
    """
    uu = uuid_38()
    if not uu:
        return None
    ra = _hoi_smi(["--query-gpu=uuid," + truong, "--format=csv,noheader,nounits"])
    if ra is None:
        return None
    for dong in ra.splitlines():
        o = [x.strip() for x in dong.split(",")]
        if len(o) >= 2 and o[0] == uu:
            return o[1:]
    log.warning("nvidia-smi khong thay card 3090 (%s) — coi nhu KHONG BIET", uu)
    return None


def so_python_tinh_tren_gpu() -> Optional[int]:
    """Số tiến trình **python** đang TÍNH TOÁN **trên card 3090**. `None` = không biết.

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

    ⭐ TỪ 11/09: ĐẾM THEO UUID 3090, KHÔNG ĐẾM CẢ MÁY. `--query-compute-apps`
       **không** lọc theo card nếu ta không xin cột `gpu_uuid`. Máy B có hai card và
       LTT-3.5 sống trên 5060 Ti — card **không ai tranh**. Đếm cả máy thì một
       tiến trình python trên 5060 Ti (hoặc màn hình Windows, hoặc một script của
       dự án video đã chuyển sang card đó) làm cổng render báo bận cho một card nó
       không hề chạm. Đó là 429 cho khách vì một phép đo nhìn sai chỗ.

    ⛔ THIẾU CỘT `gpu_uuid` ⇒ `None`, không đếm tạm. Không lọc được thì con số duy
       nhất ta có là "python trên **một** card nào đó" — dùng nó cho câu hỏi về
       3090 là chạy mù.
    """
    uu = uuid_38()
    if not uu:
        return None
    ra = _hoi_smi(["--query-compute-apps=pid,process_name,gpu_uuid",
                   "--format=csv,noheader"])
    if ra is None:
        return None
    dem = 0
    for dong in ra.splitlines():
        if not dong.strip():
            continue
        o = [x.strip() for x in dong.split(",")]
        if len(o) < 3:
            # Driver trả thiếu cột ⇒ không lọc được theo card ⇒ KHÔNG BIẾT.
            log.warning("compute-apps thieu cot gpu_uuid: %r", dong)
            return None
        if o[2] != uu:
            continue
        if "python" in o[1].lower():
            dem += 1
    return dem


#: Mức tải GPU (%) coi là **có người đang TÍNH**, không phải chỉ đang giữ bộ nhớ.
#:
#: 🔴 VÌ SAO ĐẾM TIẾN TRÌNH KHÔNG ĐỦ. `TRAN_PYTHON_GPU` coi "1 python = ComfyUI
#:    thường trú = rảnh". Đúng khi ComfyUI ngồi im. Nhưng ComfyUI **đang vẽ** cũng
#:    là đúng 1 python — phép đếm không phân biệt được. Và `llama-server.exe`
#:    **không phải python**, nên nó vô hình với phép đếm hoàn toàn.
#:
#: ⭐ Mức tải phân biệt được: ngồi im 0–1 %, đang làm ~100 %.
#:
#: ⚠️ Con số 50 và bảng bốn trường hợp đến từ `llm_gateway/trong_tai.py`, đo
#:    24/08. Nay nó nằm ở ĐÂY vì cả hai cổng cùng cần, và hướng phụ thuộc đã chốt
#:    là `llm_gateway` → `render_gateway` (xem đầu `trong_tai.py`). Một hằng số ở
#:    hai nơi là một hằng số sẽ lệch.
TAI_GPU_DANG_TINH = 50


def tai_gpu_phan_tram() -> Optional[int]:
    """Phần trăm tải GPU, hỏi `nvidia-smi`. `None` khi không hỏi được.

    Cùng lý do dùng `nvidia-smi` như `vram_dung_mb_qua_smi` ngay dưới: trên
    Windows/WDDM mọi nguồn trong tiến trình đều chỉ thấy chính nó.

    ⛔ Tải của **card 3090**, không phải `splitlines()[0]`. Dòng đầu là card nào thì
       phụ thuộc thứ tự liệt kê của driver — một thứ ta không kiểm soát và nó đổi
       khi đổi khe card. `api.py::_ho_khac_dang_tinh` dùng con số này để quyết định
       **có đuổi Qwen hay không**; đọc tải của 5060 Ti ở đó là đuổi (hoặc không
       đuổi) vì việc của một card khác.
    """
    o = _o_cua_card_3090("utilization.gpu")
    if not o:
        return None
    try:
        return int(float(o[0]))
    except ValueError:
        return None


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

    🔴 TỪ 11/09: VRAM CỦA **CARD 3090**, KHÔNG PHẢI `max()` CỦA CẢ MÁY. Bản cũ lấy
       giá trị lớn nhất trên mọi card với lý lẽ *"máy A có hai card, trả lời theo
       card bận nhất"*. Lý lẽ ấy chết ngày máy B có hai card: LTT-3.5 thường trú
       trên 5060 Ti giữ ~10 GB, nên `max()` trả **số của 5060 Ti** cho mọi câu hỏi
       về 3090 — và lệnh residency `/v1/nha_comfy` đọc chính hàm này để **xác minh
       card đã sạch sau khi dừng ComfyUI**. Một phép đo gộp sẽ luôn nói "card vẫn
       bẩn" và trọng tài sẽ kẹt ở `TRA_ANH` vĩnh viễn. Cùng lớp khuyết tật với thứ
       `llm_gateway/gpu_uuid.py` sinh ra để chặn — chỉ là nó quay lại bằng cửa render.
    """
    o = _o_cua_card_3090("memory.used")
    if not o:
        return None
    try:
        return int(float(o[0]))
    except ValueError:
        return None


def vram_ngoai_nhan_mb(smi_dung_mb: Optional[int],
                       stats: Optional[dict],
                       *, tong_card_mb: Optional[int] = None) -> Optional[int]:
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

    ⚠️ `tong_card_mb` — VRAM danh nghĩa của **card ta đang nói về** (3090). Truyền
       vào thì hàm kiểm rằng `/system_stats` cũng đang nói về card ấy; lệch quá
       `LECH_TONG_VRAM_CHO_PHEP_MB` ⇒ `None` (không biết), vì `smi_dung_mb` đã lọc
       theo UUID 3090 mà `devices[0]` thì không — trừ hai card cho nhau là một con
       số không có nghĩa. Không truyền ⇒ giữ hành vi cũ (cho bên gọi cũ).
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
    if tong_card_mb and abs(tong - tong_card_mb) > LECH_TONG_VRAM_CHO_PHEP_MB:
        # ComfyUI đang khai một card KHÁC card ta đo (ghim `CUDA_VISIBLE_DEVICES`
        # rơi?). Hiệu của hai card không phải "người khác giữ bao nhiêu".
        log.warning("system_stats khai card %d MB, card ta do %d MB — khong quy "
                    "duoc VRAM ngoai nhan", tong, tong_card_mb)
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
    #: Có hộ **bảo-được** nào giữ card không (ta gọi được đường nhả của nó).
    #:
    #: ⛔ TỪ TASK 5.4: **KHÔNG AI TRUYỀN NÓ NỪA**, và mặc định `False` là câu trả
    #:    lời đúng. Nó mở nhánh *"card đang bị giữ nhưng ta lấy lại được, nên đừng
    #:    báo bận"*, và vế **"lấy lại được"** đã không còn thật: cổng render
    #:    không còn trọng tài nào để đòi card về — quyền ấy về trọng tài residency
    #:    ở máy A (D01 B, TD-D10), và ở đó job ảnh chỉ được gửi sang khi cửa sổ ảnh
    #:    đã mở, tức 3090 đã sạch. Bật lại nhánh này là báo rảnh trong khi LTT-3.8
    #:    còn nằm trên card — tức mời một lần OOM.
    #:
    #: ⭐ Giữ trường này (thay vì xóa) vì nó ghi lại một **khoá chết theo thứ tự** đã
    #:    đo 04/09/2026: máy A hỏi `/health` TRƯỚC khi gửi lệnh vẽ và hoãn job nếu
    #:    `busy` (`apps/anhnoibo/jobs.py::_xep_lai_neu_may_ban`); nhánh VRAM bên
    #:    dưới bật `busy` mỗi khi **bất kỳ ai** giữ card. Bằng chứng: `gateway.log`
    #:    không có **một** `POST` nào, job ảnh nằm `queued` vô hạn trong khi ComfyUI
    #:    sống và hàng đợi trống. Kiểu khoá chết ấy không biến mất cùng trọng tài cũ —
    #:    nó chỉ đổi chủ: nay trọng tài máy A phải lo, và ai đọc `_nhuong_duoc` cần
    #:    biết vì sao đường tắt này từng tồn tại.
    #:
    #: ⛔ KHÔNG bỏ hẳn nhánh VRAM. Nó cứu một ca thật 22/08: `llama-server` ôm
    #:    15,9 GB, GPU 0 % tải, phép đếm python trả về 1 ⇒ cổng báo rảnh trong khi
    #:    card chỉ còn 4,6 GB.
    co_ho_bao_duoc: Callable[[], bool] = lambda: False

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
    def _nhuong_duoc(self) -> bool:
        """Card đang bị giữ, nhưng ta **lấy lại được** — nên đừng báo bận.

        Đúng khi có hộ bảo-được, **và** không ai đang tính trên card. Hai điều
        kiện, không phải một:

          · có hộ bảo-được  → có đường lấy lại card
          · không ai đang tính → lấy lại **không cắt ngang việc của ai**

        ⛔ Từ Task 5.4 vế thứ nhất không còn ai bật (`co_ho_bao_duoc` mặc định
           `False`), nên hàm này luôn trả `False` ở bản cài thật. Xem chú thích
           của trường ấy: đường đuổi cũ không drain và **giết một lượt đang
           chạy** (đo 03/09: lượt bị giết chỉ nhận `ConnectionReset`, trông y hệt
           một lần OOM), nên nó đã bị gỡ chứ không phải được thu hẹp.
        """
        try:
            if not self.co_ho_bao_duoc():
                return False
        except Exception:                                       # noqa: BLE001
            return False
        so_py = self.dem_python_gpu()
        # Không đọc được ⇒ coi như KHÔNG nhường được: giữ hành vi cũ (báo bận),
        # vì "không biết" ở đây phải xử như "không an toàn".
        return so_py is not None and so_py < TRAN_PYTHON_GPU

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
        if so_py is not None and so_py >= TRAN_PYTHON_GPU:
            return BusyState(True,
                             f"co {so_py - 1} tien trinh khac dang tinh tren GPU",
                             None, 0, len(dang_chay) + len(dang_cho), vram_mb, ram_gb,
                             ngoai_mb)
        # ⛔ Chốt thứ hai, và nó bắt thứ phép đếm trên KHÔNG bắt được: bộ nhớ bị một
        #    tiến trình **không phải python** giữ mà **không tính toán gì**. Đo thật
        #    22/08 22:27: `llama-server.exe` giữ 15,9 GB, GPU 0 % tải, phép đếm trả
        #    về 1 ⇒ cổng báo rảnh trong khi card chỉ còn 4,6 GB.
        #
        #    ⭐ VÀ NÓ ÁP TRÊN **CARD 3090**, không phải trên một tổng hay một dòng
        #    đầu: `ngoai_mb` suy từ `nvidia-smi` đã lọc UUID 3090, `_vram_tong_mb()`
        #    lấy dung lượng 3090 từ `gpu_may_b.json`. Cùng một card ở cả hai vế —
        #    nếu không, `VRAM_CAN_TOI_THIEU_MB` đang so với một đại lượng khác.
        tong_mb = self._vram_tong_mb()
        if ngoai_mb is not None and tong_mb > 0:
            kha_dung = tong_mb - ngoai_mb
            if kha_dung < self.vram_can_toi_thieu_mb and not self._nhuong_duoc():
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
        """VRAM danh nghĩa của **card 3090**, MiB. `0` = không biết.

        ⭐ ƯU TIÊN TỆP DANH TÍNH (`gpu_may_b.json`), rồi mới tới `/system_stats`.
           Trước 12/09 dòng này là `self._tong_mb or 24_576` — một hằng số gõ tay
           cho một card cụ thể, tức đúng thứ Task 0.2 đã bỏ: đo lại card thì phải
           sửa **một** tệp, không phải đi tìm các hằng số rải rác.

        ⛔ Không còn số mặc định. Không biết dung lượng card ⇒ `0`, và
           `observe()` **bỏ qua** nhánh VRAM thay vì tính `0 - ngoai` rồi kết luận
           bận — một con số bịa đặt không được biến thành một phán quyết.
        """
        return vram_tong_mib(VAI_38) or self._tong_mb or 0

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
        ngoai = vram_ngoai_nhan_mb(vram_used, st,
                                   tong_card_mb=vram_tong_mib(VAI_38))
        thiet_bi = ((st or {}).get("devices") or [{}])[0] or {}
        try:
            self._tong_mb = int(thiet_bi.get("vram_total") or 0) // (1024 * 1024)
        except (TypeError, ValueError):
            self._tong_mb = 0
        return (vram_used if vram_used is not None else 0), ram_free, ngoai
