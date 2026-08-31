"""
trong_tai.py — card có đang bị người khác chiếm không.

⭐ DÙNG LẠI, KHÔNG CHÉP LẠI. Phép đo "ai đang dùng GPU" đã được `render_gateway`
   giải xong bằng hai quyết định đắt giá:

     D-013  Hỏi `nvidia-smi`, KHÔNG hỏi `/system_stats` của ComfyUI và KHÔNG hỏi
            `torch` — cả hai đều mù với tiến trình khác trên Windows/WDDM.
     D-022  Đếm **tiến trình python đang tính trên card**, KHÔNG lấy ngưỡng VRAM.
            Vì ComfyUI giữ model thường trú: sau một lô 30 ảnh, VRAM ở lì
            23.967/24.576 MB (97,5 %) mà chẳng có ai đang chạy cả. Chốt theo VRAM
            sẽ tự báo bận vĩnh viễn kể từ lô đầu tiên.

   Chép 275 dòng đó sang đây là đúng loại lỗi mà `AGENTS.md` mục 8 cấm. Hai gói
   này deploy sang máy B **cùng nhau**, nên `llm_gateway` gọi thẳng `render_gateway`.

⭐ NGƯỠNG LÀ **≥ 2**, KHÔNG PHẢI **> 0**. Đây là ngữ nghĩa `render_gateway` đã chốt
   sau khi đo thật: WDDM tính cả `dwm.exe` và trình duyệt vào danh sách compute,
   nhưng **đúng một** tiến trình là python — và nó chính là ComfyUI.

        1 python  -> chi co ComfyUI dang thuong tru: BINH THUONG
        >= 2      -> co tien trinh KHAC dang tinh tren card: BAN

   ⚠️ Bản đầu của tệp này đặt ngưỡng `> 0`. Sai, và sai theo kiểu tệ nhất: trên máy
   B ComfyUI **luôn** chạy, nên cổng sẽ trả 429 **vĩnh viễn** và model nhà không
   bao giờ phục vụ được lượt nào.

   `llama-server.exe` **không phải** python, nên phép đếm này không tự đếm chính ta.

⭐ PHÂN CÔNG VỚI `don_dep.py` — hai câu hỏi khác nhau, đừng trộn:

     trong_tai:  co VIEC KHAC dang chay khong?      -> ban -> 429
     don_dep  :  VRAM co dang bi GIU khong?         -> bao ComfyUI nha roi do lai

   Một ComfyUI *nằm im nhưng vẫn ôm 6,2 GB* **không** làm ta bận — nó chỉ cần được
   bảo nhả. Đó là việc của `don_dep`, và số đo P6 cho thấy bỏ qua nó thì tốc độ
   còn một phần tư mà không có lỗi nào.

⛔ BẬN KHÔNG PHẢI LỖI. Bên gọi phải dịch kết quả `ban=True` thành **HTTP 429**,
   không phải 5xx. Xem đầu `__init__.py`.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger("llm_gateway.trong_tai")

#: Cùng trần với `render_gateway/busy.py` và `platform_core/gpu.py`. Không đặt số khác.
NVIDIA_SMI_TIMEOUT_S = 8

#: Số tiến trình python trên card kể từ đó coi là BẬN. **2**, không phải 1:
#: một python là ComfyUI thường trú, đó là trạng thái bình thường của máy B.
#: Đặt 1 ở đây làm cổng trả 429 vĩnh viễn — xem chú thích đầu tệp.
TRAN_PYTHON_GPU = 2

#: Mức tải GPU coi là "có người đang TÍNH", không phải chỉ đang giữ bộ nhớ.
#:
#: 🔴 VÌ SAO ĐẾM TIẾN TRÌNH KHÔNG ĐỦ. Chốt dưới đây coi *"1 tiến trình python =
#:    chỉ ComfyUI thường trú = RẢNH"*. Đó đúng khi ComfyUI ngồi im giữ model.
#:    Nhưng ComfyUI **đang vẽ** cũng là **đúng 1 tiến trình python** — đếm không
#:    phân biệt được hai chuyện đó.
#:
#:    Hệ quả đo thật 24/08: nạp Qwen trong lúc HiDream đang vẽ ⇒ card lên
#:    **24.213 MB / 24.576 = 98,5 %**, và **cả hai** cùng chậm.
#:
#: ⭐ Thứ phân biệt được là **mức tải**: ComfyUI ngồi im ở 0–1 %, ComfyUI đang vẽ
#:    ở ~100 %. Kết hợp hai tín hiệu cho đúng bốn trường hợp:
#:
#:      python có + tải cao  ⇒ BẬN   (ComfyUI đang vẽ, hoặc dự án video đang chạy)
#:      python có + tải thấp ⇒ rảnh  (ComfyUI chỉ thường trú)
#:      python không + tải cao ⇒ rảnh (chính `llama-server` đang trả lời — tải
#:                                     của CHÍNH TA, và `gioi_han` đã chặn đồng thời)
#:      python không + tải thấp ⇒ rảnh
#:
#: ⚠️ `llama-server.exe` **không phải** python — đó là lý do phép đếm bỏ sót nó
#:    (D-037), và cũng là lý do phép kết hợp này không tự chặn chính mình.
TAI_GPU_DANG_TINH = 50


def _tai_gpu_mac_dinh() -> Optional[int]:
    """Phần trăm tải GPU. `None` = không hỏi được."""
    import subprocess
    try:
        ra = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8)
        if ra.returncode != 0:
            return None
        dong = (ra.stdout or "").strip().splitlines()
        return int(dong[0].strip()) if dong else None
    except Exception:                                           # noqa: BLE001
        return None


def _dem_python_gpu_mac_dinh() -> Optional[int]:
    """Số tiến trình python đang tính trên GPU. `None` = không hỏi được.

    Uỷ quyền cho `render_gateway.busy` nếu có; nếu gói đó chưa được deploy cùng
    (ví dụ đang chạy test trên máy A) thì rơi về một phép đếm tối thiểu tại chỗ.
    """
    try:
        from render_gateway.busy import so_python_tinh_tren_gpu
    except ImportError:
        return _dem_toi_thieu()
    return so_python_tinh_tren_gpu()


def _dem_toi_thieu() -> Optional[int]:
    """Đường lùi khi không có `render_gateway`. Cố ý thô."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    try:
        r = subprocess.run(
            [smi, "--query-compute-apps=process_name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=NVIDIA_SMI_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return sum(1 for d in r.stdout.splitlines() if "python" in d.lower())


def _ram_trong_gb_mac_dinh() -> Optional[float]:
    try:
        import psutil
    except ImportError:
        return None
    try:
        return psutil.virtual_memory().available / (1024 ** 3)
    except (OSError, RuntimeError) as e:               # pragma: no cover
        # Khong nuot lang le: khong doc duoc RAM la mot su that van hanh, va
        # `phan_xu()` se coi "khong biet" la BAN. Phai thay duoc vi sao.
        log.warning("khong doc duoc RAM trong: %s", type(e).__name__)
        return None


@dataclass(frozen=True)
class PhanXu:
    """Phán xử một yêu cầu: cho chạy, hay bảo bên gọi đi tìm đám mây."""

    ban: bool
    ly_do: str = ""
    so_python_gpu: Optional[int] = None
    ram_trong_gb: Optional[float] = None


class TrongTai:
    """Quyết định card có rảnh cho một lượt suy luận không.

    Cả hai nguồn đều tiêm được, để test chạy trên máy không có GPU.
    """

    def __init__(self, *, ram_trong_toi_thieu_gb: float, bat: bool = True,
                 tran_python_gpu: int = TRAN_PYTHON_GPU,
                 dem_python_gpu: Callable[[], Optional[int]] = _dem_python_gpu_mac_dinh,
                 ram_trong_gb: Callable[[], Optional[float]] = _ram_trong_gb_mac_dinh,
                 tai_gpu: Callable[[], Optional[int]] = _tai_gpu_mac_dinh,
                 tai_dang_tinh: int = TAI_GPU_DANG_TINH,
                 model_cua_ta_dang_chay: Callable[[], bool] = lambda: False):
        self.ram_toi_thieu = ram_trong_toi_thieu_gb
        self.bat = bat
        self.tran_python_gpu = tran_python_gpu
        self._dem = dem_python_gpu
        self._ram = ram_trong_gb
        self._tai = tai_gpu
        self.tai_dang_tinh = tai_dang_tinh
        #: Model CUA TA co dang nap va san sang khong. Mac dinh `False` de giu
        #: nguyen hanh vi cu khi ben goi khong noi day — xem `phan_xu`.
        self._model_cua_ta = model_cua_ta_dang_chay

    def phan_xu(self) -> PhanXu:
        if not self.bat:
            return PhanXu(ban=False, ly_do="trong tai tat")

        ram = self._ram()
        if ram is not None and ram < self.ram_toi_thieu:
            # ⛔ Ngưỡng RAM là LƯỢNG TUYỆT ĐỐI (GB), không phải tỉ lệ. Dự án video
            #    máy B đã học điều này bằng một chốt chặn oan khi nâng RAM 96 → 192 GB.
            return PhanXu(ban=True, ram_trong_gb=ram,
                          ly_do=f"RAM trong {ram:.1f} GB duoi nguong {self.ram_toi_thieu:.0f} GB")

        n = self._dem()
        if n is None:
            # Không hỏi được card. **Không lạc quan** — cùng nguyên tắc với
            # `render_gateway/busy.py`: thà báo bận rồi để khách chọn đám mây.
            return PhanXu(ban=True, ly_do="khong hoi duoc nvidia-smi", ram_trong_gb=ram)

        if n >= self.tran_python_gpu:
            return PhanXu(ban=True, so_python_gpu=n, ram_trong_gb=ram,
                          ly_do=(f"co {n} tien trinh python tren card "
                                 f"(>= {self.tran_python_gpu}) — co viec khac dang chay"))

        # n == 1 co the la ComfyUI THUONG TRU (ranh) hoac ComfyUI DANG VE (ban).
        # Dem khong phan biet duoc — muc tai thi co. Xem `TAI_GPU_DANG_TINH`.
        if n >= 1:
            tai = self._tai()
            if tai is not None and tai >= self.tai_dang_tinh:
                # 🔴 TẢI CAO CỦA CHÍNH TA KHÔNG PHẢI TẢI CỦA NGƯỜI KHÁC.
                #
                #    `llama-server.exe` **không phải python** nên nó không bị
                #    đếm ở `n`. Nhưng khi nó đang sinh chữ, card lên 89–100 % —
                #    và nhánh trên quy mức tải ấy cho **ComfyUI**, cái python duy
                #    nhất được đếm. ComfyUI lúc đó đang ngồi im.
                #
                # ⛔ Đo 31/08, hai lượt độc lập: **14/20 = 70 %** yêu cầu bị từ
                #    chối oan. Máy khoẻ, model sẵn sàng, ComfyUI im — và cổng vẫn
                #    trả 429 vì nó thấy tải do **chính nó** tạo ra. Mọi lượt đều
                #    thành công khi thử lại.
                #
                # 🔴 Với khách thật, triệu chứng là: một client tuần tự (Codex,
                #    Claude Code — hỏi, đọc, hỏi tiếp) ngẫu nhiên nhận
                #    `503 model is busy` vì GPU còn nóng từ **lượt trước của
                #    chính họ**, và không có cách nào phân biệt với "máy B bận
                #    thật".
                #
                # ⭐ Vì sao điều kiện là "model của ta đang chạy" chứ không phải
                #    một ngưỡng tải khác: nhánh này sinh ra để tránh **NẠP** model
                #    đè lên việc người khác — chính câu cuối của thông điệp nói
                #    thế. Model đã nạp rồi thì **không có gì để nạp**, nên lý do
                #    tồn tại của nhánh đã hết.
                #
                # ⚠️ Cái giá, nói thẳng: nếu model ta đã nạp **và** ComfyUI bắt
                #    đầu vẽ thật, ta sẽ không còn từ chối. Chấp nhận được vì
                #    `--reserve-vram 3` đã có và VRAM của ta ổn định ở 22,4 GB;
                #    đổi lại là chấm dứt 70 % lượt từ chối oan.
                if self._model_cua_ta():
                    return PhanXu(ban=False, so_python_gpu=n, ram_trong_gb=ram,
                                  ly_do=(f"tai GPU {tai}% nhung model cua ta dang "
                                         f"chay — tai nay la CUA TA"))
                return PhanXu(ban=True, so_python_gpu=n, ram_trong_gb=ram,
                              ly_do=(f"co tien trinh python tren card va tai GPU "
                                     f"{tai}% (>= {self.tai_dang_tinh}%) — dang ve, "
                                     f"nap model bay gio se de len nhau"))

        # n == 0 (khong ai), hoac python co mat nhung tai thap (chi thuong tru).
        return PhanXu(ban=False, so_python_gpu=n, ram_trong_gb=ram)
