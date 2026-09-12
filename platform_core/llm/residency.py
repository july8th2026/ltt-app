"""residency.py — MÁY TRẠNG THÁI chia RTX 3090 giữa LTT-3.8 và model ảnh. (D01 B)

⭐ HÀM THUẦN, và đó là toàn bộ lý do tệp này tồn tại riêng: không CSDL, không
   HTTP, không đọc đồng hồ, không `sleep`. Thời gian và trạng thái đi VÀO bằng
   tham số (`bay_gio`, `TrangThai`, `QuanSat`), quyết định đi RA bằng giá trị
   trả về (`TrangThai` mới + các lệnh phải phát). Mọi tác dụng phụ — đọc lease,
   đọc hàng job, gọi gateway máy B, ghi dòng `gpu_residency` — nằm ở người gọi
   (Task 5.3 admission, Task 5.5 trọng tài).

   Nhờ vậy luật chia card kiểm được **không cần GPU, không cần máy B, không cần
   CSDL**: `tests/test_1216_residency_thuan.py` chạy nó qua mọi cặp
   trạng thái × quan sát trong vài giây.

⛔ LUẬT SÁNG LẬP CỦA CHƯƠNG TRÌNH (L-9, D01 B): **không lượt nào bị giết để đổi
   cư trú** — cả lượt LLM lẫn lượt vẽ. Vì llama.cpp không preempt được và ComfyUI
   cũng không, "đổi cư trú" chỉ có một cách đúng: **drain**. Máy này encode luật
   ấy bằng hai thứ cơ học chứ không bằng lời văn:

   1. `CHUYEN_HOP_LE` — bảng chuyển. `_sang()` là cửa DUY NHẤT đổi trạng thái và
      nó ném với mọi cặp ngoài bảng. Nên `LLM → NHA_LLM` (nhả model khi chưa
      drain) hay `ANH → NAP_LLM` (nạp lại khi lượt vẽ còn chạy) không phải là
      "một nhánh code cần cẩn thận" — chúng **không biểu đạt được**.
   2. Ba bất biến ở tầng LỆNH, vì lệnh mới là thứ giết việc:
      · `nha_llm` chỉ phát khi `da_drain_xong(qs)` — 0 lease LLM **và** gateway
        báo 0 in-flight (không đo được ⇒ coi như chưa drain);
      · `nap_llm` và `free_comfy` chỉ phát khi `dang_ve_anh(qs)` là False.
        Nạp 16 GB trọng số lên card đang vẽ, hay dọn VRAM của ComfyUI đang vẽ,
        là giết lượt vẽ bằng OOM.

📐 Các con số ĐÃ ĐO (12/09/2026, `docs/ltt_llm_dual/10_BENCHMARK_P3.md`) — đừng
   thay bằng phỏng đoán, và đừng đo lại ở đây:

   · `t_nap_llm_s = 16,3` (§G4, nạp LTT-3.8 từ kho ấm). Bản plan đầu đoán 45,0 —
     gấp 2,8 lần thật, và sai số ấy đẩy về phía **ngần ngại đổi cư trú**, tức
     3090 nằm sai chỗ lâu hơn cần.
   · **MỘT con số phủ cả kho ấm và kho lạnh** (§G5): kho lạnh chỉ đắt hơn 7–11 %
     (≈16,9 s cho 3.8), vì nút thắt của việc nạp không phải đọc tệp mà là đẩy
     trọng số lên GPU + cấp phát ngữ cảnh — hai thứ không đổi giữa ấm và lạnh.
     Cận trên 17 s phủ cả hai. Nên ở đây **không cần hai tham số**, và một tham
     số thứ hai sẽ là một nút không ai biết đặt bao nhiêu.
   · Và kho lạnh gần như không xảy ra: hồ sơ mới đặt `ttl: 0` + `preload`, hai
     model nằm thường trú, còn trọng tài chỉ tháo/nạp LTT-3.8 và lần nạp lại
     luôn cách lần trước vài phút — thừa sức còn trong standby cache 24,8 GB.
   · `t_anh_uoc_s = 110` — đo 92–110 s/ảnh (`docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md`,
     `CHIA_GPU_HAI_MODEL.md`). Lấy đầu **xấu** của dải: con số này dùng để đoán
     "vẽ thêm một ảnh nữa có làm người chờ LLM chết vì hết trần chờ không", và
     đoán thấp ở đó thì người chờ chết thật.

⚠️ `free_comfy` KHÔNG phải chỉ `POST /free` (L-14 §3, spec §0): ComfyUI ấm giữ
   **223,5 MiB** ngữ cảnh CUDA thường trú và `/free` **không** nhả nó — chỉ dừng
   dịch vụ mới nhả. Biên của LTT-3.8 ở `-c 221184` là **445 MiB** khi ComfyUI
   chưa nạp, nên 223,5 MiB không phải chuyện tối ưu, nó là **ràng buộc cứng**:
   người thực thi lệnh này (Task 5.4/5.5) phải dừng hẳn dịch vụ LTTComfyUI trong
   cửa sổ LLM. Tên lệnh giữ theo plan để Task 5.4 khớp chuỗi; nghĩa của nó là
   *"làm cho VRAM 3090 sạch"*, không phải *"gọi đúng endpoint /free"*.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

# ── Trạng thái của nhóm GPU ───────────────────────────────────────────────────
#
# Chuỗi ổn định: chúng vào cột `gpu_residency.trang_thai`, vào `/ops/jobs-metrics`
# và vào log. Đổi một giá trị ở đây là đổi dữ liệu đang nằm trong CSDL.
LLM, XA_LLM, NHA_LLM, ANH, TRA_ANH, NAP_LLM, LOI_NAP = (
    "llm", "xa_llm", "nha_llm", "anh", "tra_anh", "nap_llm", "loi_nap")

#: Thứ tự = thứ tự một chu trình bình thường đi qua. Dùng để duyệt trong phép kiểm.
TRANG_THAI: tuple[str, ...] = (LLM, XA_LLM, NHA_LLM, ANH, TRA_ANH, NAP_LLM, LOI_NAP)

# ── Lệnh gửi ra ngoài ─────────────────────────────────────────────────────────
#
# Máy thuần KHÔNG gọi gì; nó trả về TÊN việc phải làm. Cả ba đều **idempotent**
# theo thiết kế, vì người gọi có thể phát lại chúng nhiều lượt bước liền nhau khi
# máy B còn chưa xong (xem nhánh `NHA_LLM`).
NHA_LLM_LENH, NAP_LLM_LENH, FREE_COMFY_LENH = "nha_llm", "nap_llm", "free_comfy"

#: Trạng thái → những trạng thái nó được phép sang. "Ở lại" không phải một chuyển,
#: nên không trạng thái nào tự lặp trong bảng này.
#:
#: ⭐ Đọc bảng này bằng những gì nó KHÔNG chứa — đó là chỗ luật sống:
#:
#:   · `LLM → NHA_LLM`, `LLM → ANH`   nhả model / vẽ mà chưa drain lượt LLM;
#:   · `XA_LLM → ANH`                 vẽ trước khi máy B xác nhận model đã rời card;
#:   · `ANH → NAP_LLM`                nạp lại khi lượt vẽ còn đang chạy;
#:   · `TRA_ANH → LLM`                khai "LLM đang cư trú" mà chưa nạp gì.
#:
#: Bốn dòng đó là bốn cách giết việc đang chạy, và không cái nào biểu đạt được.
CHUYEN_HOP_LE: dict[str, frozenset[str]] = {
    LLM: frozenset({XA_LLM}),
    # Về `LLM` là đường HUỶ BỎ: job ảnh rút khỏi hàng giữa lúc drain thì không có
    # gì phải đổi nữa, và quay lại không tốn một lần nạp 16,3 s.
    XA_LLM: frozenset({NHA_LLM, LLM}),
    NHA_LLM: frozenset({ANH}),
    ANH: frozenset({TRA_ANH}),
    TRA_ANH: frozenset({NAP_LLM}),
    NAP_LLM: frozenset({LLM, LOI_NAP}),
    LOI_NAP: frozenset({NAP_LLM}),
}


@dataclass(frozen=True)
class TrangThai:
    """Toàn bộ trạng thái BỀN của nhóm — đúng bốn trường, khớp bảng `gpu_residency`.

    Mọi thứ khác mà máy cần biết là **quan sát** (`QuanSat`), tức thứ đọc lại
    được từ sự thật (lease, hàng job, máy B). Giữ trạng thái bền tối thiểu là
    cách duy nhất để một tiến trình chết giữa cửa sổ không để lại một bộ đếm sai.
    """

    ten: str = LLM
    #: Vào `ten` hiện tại từ lúc nào (giây, cùng gốc với `bay_gio`).
    tu_luc: float = 0.0
    #: Cửa sổ ảnh mở lúc nào. Chỉ có nghĩa từ `ANH` trở đi.
    cua_so_bat_dau: float = 0.0
    lan_nap_loi: int = 0


def _sang(tt: TrangThai, ten: str, bay_gio: float, **dat) -> TrangThai:
    """Cửa DUY NHẤT đổi trạng thái. Ném nếu cặp chuyển không có trong bảng.

    Vì sao ném chứ không trả về `tt`: một chuyển ngoài bảng không phải một điều
    kiện chưa thoả, nó là một **lỗi lập trình** — và lỗi loại đó ở đây có nghĩa
    là máy vừa suýt giết một lượt của khách. Im lặng ở lại sẽ biến nó thành một
    nhóm GPU treo mà không ai biết vì sao.
    """
    if ten not in CHUYEN_HOP_LE[tt.ten]:
        raise ValueError(f"chuyen bat hop le: {tt.ten!r} -> {ten!r}")
    return replace(tt, ten=ten, tu_luc=bay_gio, **dat)
