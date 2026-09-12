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

⛔ VÀ NÓ KHÔNG CÒN HỎI ComfyUI, BẰNG BẤT CỨ ĐƯỜNG NÀO (Dual-model 5.4b).
   `don_dep.py` (gọi `/free` rồi tự đo lại) đã bị **xoá**, cùng nhánh "1 python +
   tải cao" của tệp này. Cả hai là một **trọng tài thứ hai** cho card 3090, và
   D01 B thay hai trọng tài bằng **một**: trọng tài residency ở máy A, nơi duy
   nhất thấy cùng lúc lease LLM, phòng chờ và hàng job ảnh (TD-D10).

   Việc dọn card không mất đi — nó đổi chủ và đổi cả cơ chế: máy A phát
   `POST /v1/nha_comfy` để **dừng hẳn** dịch vụ LTTComfyUI (L-14 §3: `/free`
   không nhả 223,5 MiB ngữ cảnh CUDA, mà biên của LTT-3.8 chỉ 445 MiB), rồi mới
   phát `POST /v1/residency/nap`.

   Thứ còn lại ở đây là hai cái phanh thuần cơ học — RAM chủ, và số tiến trình
   python đang tính trên card — không cái nào đòi hỏi một câu chuyện về ai đang
   vẽ gì.

⛔ BẬN KHÔNG PHẢI LỖI. Bên gọi phải dịch kết quả `ban=True` thành **HTTP 429**,
   không phải 5xx. Xem đầu `__init__.py`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger("llm_gateway.trong_tai")

#: Cùng trần với `render_gateway/busy.py` và `platform_core/gpu.py`. Không đặt số khác.
NVIDIA_SMI_TIMEOUT_S = 8

#: Card mà trọng tài này nói về: **3090** (`ltt38`). Nó cân giữa ComfyUI và
#: LTT-3.8, hai hộ dùng chung đúng card ấy. LTT-3.5 ở trên 5060 Ti và **không**
#: tranh với ComfyUI, nên tải/tiến trình của card kia không được lọt vào đây.
VAI_TRONG_TAI = "ltt38"

#: Số tiến trình python trên card kể từ đó coi là BẬN. **2**, không phải 1:
#: một python là ComfyUI thường trú, đó là trạng thái bình thường của máy B.
#: Đặt 1 ở đây làm cổng trả 429 vĩnh viễn — xem chú thích đầu tệp.
TRAN_PYTHON_GPU = 2

# 🔴 `TAI_GPU_DANG_TINH` VÀ `_tai_gpu_mac_dinh` ĐÃ ĐI (Dual-model 5.4b).
#
#    Chúng phục vụ **một** nhánh: *"1 python + tải cao ⇒ bận"*, tức phép suy
#    "card nóng nên chắc ComfyUI đang vẽ". Phép suy ấy đã sai hai lần theo hai
#    chiều — 31/08 nó đọc tải của **chính ta** thành tải người khác (70 % lượt bị
#    chối oan), rồi 04/09 nó bỏ lọt ca hai model cùng làm việc — và cả hai lần
#    bản vá là **thêm một nguồn tin**, chứ ngưỡng không cứu được.
#
# ⭐ Lời giải không phải một ngưỡng thứ ba mà là một **quyền**: từ D01 B, ai cầm
#    3090 lúc nào do trọng tài residency ở máy A quyết, và trong cửa sổ LLM thì
#    ComfyUI đã bị dừng hẳn (5.4a). Không còn cuộc tranh nào cho cổng này phân
#    xử, nên không còn tín hiệu nào cho nó đọc. `render_gateway.busy` vẫn giữ
#    hằng số ấy cho **phía ảnh** — đó là người dùng thật sự của nó.


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
    """Đường lùi khi không có `render_gateway`. Cố ý thô, nhưng **đúng card**.

    ⛔ `--query-compute-apps` không xin cột `gpu_uuid` thì nó đếm tiến trình trên
       **mọi** card rồi ta kết luận về một card. Từ 09/2026 điều đó có nghĩa: một
       job ảnh trên 5060 Ti làm cổng của 3090 tưởng card mình có người khác —
       429 oan, trong khi 3090 hoàn toàn rảnh.
    """
    from .gpu_uuid import VaiKhongCo, doc_the, tien_trinh, uuid_cua
    try:
        uu = uuid_cua(VAI_TRONG_TAI)
    except (VaiKhongCo, OSError, ValueError):
        return None
    # Hỏi thẻ trước để phân biệt "không có tiến trình nào" với "không hỏi được":
    # `tien_trinh` trả danh sách rỗng cho **cả hai**, và hai thứ đó đòi hai phán
    # xử khác nhau ở `phan_xu()` (rảnh vs bận).
    if doc_the(uu) is None:
        return None
    return sum(1 for _pid, ten, _mib in tien_trinh(uu) if "python" in ten.lower())


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
                 ram_trong_gb: Callable[[], Optional[float]] = _ram_trong_gb_mac_dinh):
        self.ram_toi_thieu = ram_trong_toi_thieu_gb
        self.bat = bat
        self.tran_python_gpu = tran_python_gpu
        self._dem = dem_python_gpu
        self._ram = ram_trong_gb

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

        # 🔴 NHÁNH "1 python + tải cao" ĐÃ ĐI (Dual-model 5.4b), và nó đi vì
        #    quyền chứ không vì ngưỡng. Nó hỏi `utilization.gpu` rồi hỏi hàng đợi
        #    ComfyUI để tự phân xử cuộc tranh 3090 — tức nó là **trọng tài thứ
        #    hai**, đúng thứ D01 B thay bằng MỘT trọng tài residency ở máy A.
        #
        #    Hai nguồn tin của nó nay đều vô nghĩa ở đây: trong cửa sổ LLM,
        #    ComfyUI **đã bị dừng hẳn** (5.4a) nên `/queue` không trả lời và mức
        #    tải trên card chỉ còn là tải của **chính ta**; ngoài cửa sổ LLM, máy
        #    A đã chặn ở admission (Task 5.3) nên lượt không tới được đây. Giữ
        #    nhánh ấy chỉ còn sinh ra 429 oan — đúng 70 % lượt bị chối của 31/08
        #    (`test_368` cũ), lần này không có ai đi sửa.
        #
        # ⛔ Và cổng này **không được** hỏi ComfyUI nữa, bằng bất cứ đường nào:
        #    hai cơ chế cùng canh một card, không khoá chung, là hình dạng hỏng
        #    mà cả Task 5.4 đi gỡ. Chốt tĩnh ở `tests/test_1218_gateway_residency.py`.

        # n == 0 (khong ai), hoac python co mat nhung tai thap (chi thuong tru).
        return PhanXu(ban=False, so_python_gpu=n, ram_trong_gb=ram)
